from types import SimpleNamespace
from typing import Any

import pytest

from app.core.models import AnalysisResult, ConfidenceLevel, SimilarCase, Ticket
from app.llm.claude import AnalysisError, ClaudeAnalyzer
from app.prompts import SYSTEM_PROMPT

RESULT = AnalysisResult(
    diagnostico_e_evidencias="Senha expirada, como no chamado #41.",
    nivel_de_confianca=ConfidenceLevel(percentual=70, justificativa="Caso similar."),
    passos_sugeridos_de_teste=["1. Verificar a data de expiração da senha."],
)


class FakeMessages:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return self.response


def make_client(stop_reason: str = "end_turn", parsed: Any = RESULT):
    messages = FakeMessages(
        SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed)
    )
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def test_analyze_sends_ticket_and_cases_with_structured_output() -> None:
    client, messages = make_client()
    analyzer = ClaudeAnalyzer(client=client)

    result = analyzer.analyze(
        Ticket(id="101", title="Sem acesso", tenant_id="7"),
        [SimilarCase(id="41", source="glpi", content="Senha redefinida.")],
    )

    assert result == RESULT
    assert messages.kwargs["model"] == "claude-opus-5-5"
    assert messages.kwargs["system"] == SYSTEM_PROMPT
    assert messages.kwargs["output_format"] is AnalysisResult
    assert messages.kwargs["output_config"] == {"effort": "medium"}
    assert messages.kwargs["fallbacks"] == "default"
    user_content = messages.kwargs["messages"][0]["content"]
    assert '"Sem acesso"' in user_content
    assert '"Senha redefinida."' in user_content


@pytest.mark.parametrize(
    ("stop_reason", "parsed"),
    [("refusal", None), ("max_tokens", None), ("end_turn", None)],
)
def test_analyze_raises_when_no_usable_result(stop_reason: str, parsed: Any) -> None:
    client, _ = make_client(stop_reason=stop_reason, parsed=parsed)

    with pytest.raises(AnalysisError):
        ClaudeAnalyzer(client=client).analyze(Ticket(id="1"), [])
