import json
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.core.models import SimilarCase, Ticket
from app.llm.claude import ClaudeAnalyzer
from app.llm.errors import AnalysisError
from app.llm.offline import OfflineAnalyzer
from app.llm.ollama import OllamaAnalyzer
from app.main import build_analyzer
from app.prompts import RESPONSE_JSON_SCHEMA

VALID_CONTENT = json.dumps(
    {
        "diagnostico_e_evidencias": "Senha expirada, como no chamado #41.",
        "nivel_de_confianca": {"percentual": 65, "justificativa": "Caso similar."},
        "passos_sugeridos_de_teste": ["1. Verificar a expiração da senha."],
    },
    ensure_ascii=False,
)


def make_analyzer(status: int = 200, body: Any = None) -> tuple[OllamaAnalyzer, list]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if body is None:
            payload = {"message": {"role": "assistant", "content": VALID_CONTENT}}
        else:
            payload = body
        return httpx.Response(status, json=payload)

    client = httpx.Client(
        base_url="http://ollama:11434", transport=httpx.MockTransport(handler)
    )
    return OllamaAnalyzer(model="qwen2.5:7b", client=client), requests


def test_analyze_sends_schema_and_parses_result() -> None:
    analyzer, requests = make_analyzer()

    result = analyzer.analyze(
        Ticket(id="101", title="Sem acesso", tenant_id="7"),
        [SimilarCase(id="41", source="glpi", content="Senha redefinida.")],
    )

    assert result.nivel_de_confianca.percentual == 65
    sent = json.loads(requests[0].content)
    assert requests[0].url.path == "/api/chat"
    assert sent["model"] == "qwen2.5:7b"
    assert sent["stream"] is False
    assert sent["format"] == RESPONSE_JSON_SCHEMA
    assert "Senha redefinida." in sent["messages"][1]["content"]


def test_analyze_explains_missing_model() -> None:
    analyzer, _ = make_analyzer(status=404, body={"error": "model not found"})

    with pytest.raises(AnalysisError, match="ollama pull qwen2.5:7b"):
        analyzer.analyze(Ticket(id="1"), [])


def test_analyze_rejects_output_outside_contract() -> None:
    invalid = {"message": {"content": json.dumps({"diagnostico_e_evidencias": "x"})}}
    analyzer, _ = make_analyzer(body=invalid)

    with pytest.raises(AnalysisError):
        analyzer.analyze(Ticket(id="1"), [])


def test_analyze_reports_connection_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = httpx.Client(base_url="http://x", transport=httpx.MockTransport(handler))

    with pytest.raises(AnalysisError, match="conectar ao Ollama"):
        OllamaAnalyzer(client=client).analyze(Ticket(id="1"), [])


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (Settings(llm_provider="ollama"), OllamaAnalyzer),
        (Settings(llm_provider="offline"), OfflineAnalyzer),
        (Settings(llm_provider="claude", anthropic_api_key=""), OfflineAnalyzer),
        (Settings(llm_provider="claude", anthropic_api_key="sk-test"), ClaudeAnalyzer),
    ],
)
def test_build_analyzer_selects_provider(settings: Settings, expected: type) -> None:
    pytest.importorskip("anthropic")

    assert isinstance(build_analyzer(settings), expected)


def test_build_analyzer_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="RESOLVEAI_LLM"):
        build_analyzer(Settings(llm_provider="gpt"))


def test_ollama_is_the_default_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESOLVEAI_LLM", raising=False)

    assert Settings().llm_provider == "ollama"


def test_removes_no_history_sentence_when_a_case_is_cited() -> None:
    content = json.dumps(
        {
            "diagnostico_e_evidencias": (
                "O caso #41 é parecido. "
                "Não encontrei histórico semelhante no material recuperado do GLPI."
            ),
            "nivel_de_confianca": {"percentual": 60, "justificativa": "Similar."},
            "passos_sugeridos_de_teste": ["1. Verificar."],
        },
        ensure_ascii=False,
    )
    analyzer, _ = make_analyzer(body={"message": {"content": content}})

    result = analyzer.analyze(
        Ticket(id="1"), [SimilarCase(id="41", source="glpi", content="x")]
    )

    assert result.diagnostico_e_evidencias == "O caso #41 é parecido."
