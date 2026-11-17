"""Analisador gratuito que roda um modelo aberto localmente via Ollama."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.models import AnalysisResult, SimilarCase, Ticket
from app.llm.errors import AnalysisError
from app.prompts import RESPONSE_JSON_SCHEMA, SYSTEM_PROMPT, build_user_prompt

LOGGER = logging.getLogger("resolveai.llm.ollama")

DEFAULT_MODEL = "qwen2.5:7b"
NO_HISTORY_SENTENCE = (
    "Não encontrei histórico semelhante no material recuperado do GLPI."
)

# Modelos menores seguem melhor o formato quando veem o schema no prompt, e
# tendem a usar a frase de "sem histórico" mesmo havendo casos parecidos.
OLLAMA_SYSTEM_PROMPT = (
    SYSTEM_PROMPT
    + """
COMO USAR OS CASOS RECUPERADOS
- Os casos em "casos_recuperados_rag" já foram pré-selecionados por
  similaridade. Compare cada um com o chamado atual.
- Se um caso tiver o mesmo tipo de equipamento ou serviço e um sintoma
  parecido (ex.: dispositivo perdendo conexão Wi-Fi), ele É correlacionado:
  cite o ID dele (ex.: "chamado #12") no diagnóstico, explique a semelhança e
  use a solução dele como hipótese a verificar.
- Use a frase "Não encontrei histórico semelhante no material recuperado do
  GLPI." SOMENTE quando "casos_recuperados_rag" estiver vazio ou nenhum caso
  tiver relação com o problema. Nunca use essa frase e cite um caso ao mesmo
  tempo.
- Quando houver caso correlacionado, a confiança deve refletir isso (em geral
  acima de 50), sem passar de 85 enquanto nada tiver sido verificado.
"""
    + "\nSCHEMA JSON DA RESPOSTA\n"
    + json.dumps(RESPONSE_JSON_SCHEMA, ensure_ascii=False)
    + "\n"
)


class OllamaAnalyzer:
    """`Analyzer` que chama a API local do Ollama com saída JSON estruturada."""

    provider = "ollama"

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = DEFAULT_MODEL,
        timeout: float = 300.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.client = client or httpx.Client(
            base_url=host.rstrip("/"), timeout=httpx.Timeout(timeout, connect=5.0)
        )

    def analyze(
        self, ticket: Ticket, similar_cases: Sequence[SimilarCase]
    ) -> AnalysisResult:
        user_prompt = build_user_prompt(
            ticket.model_dump(),
            [case.model_dump(exclude_none=True) for case in similar_cases],
        )
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            # O Ollama restringe a geração a este JSON schema.
            "format": RESPONSE_JSON_SCHEMA,
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = self.client.post("/api/chat", json=payload)
        except httpx.HTTPError as error:
            raise AnalysisError(
                f"Não foi possível conectar ao Ollama: {error}"
            ) from error

        if response.status_code == 404:
            raise AnalysisError(
                f"Modelo '{self.model}' não encontrado no Ollama. "
                f"Rode: ollama pull {self.model}"
            )
        if response.status_code >= 400:
            raise AnalysisError(
                f"O Ollama retornou HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            content = response.json()["message"]["content"]
            result = AnalysisResult.model_validate_json(content)
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            LOGGER.warning("Invalid Ollama response for ticket %s.", ticket.id)
            raise AnalysisError("O modelo não retornou uma análise válida.") from error
        return _drop_contradictory_no_history(result, similar_cases)


def _drop_contradictory_no_history(
    result: AnalysisResult, similar_cases: Sequence[SimilarCase]
) -> AnalysisResult:
    """Modelos pequenos às vezes citam um caso E dizem que não há histórico.

    Se o diagnóstico cita o ID de algum caso recebido, a frase de "sem
    histórico" é contraditória e é removida.
    """
    diagnosis = result.diagnostico_e_evidencias
    cites_case = any(f"#{case.id}" in diagnosis for case in similar_cases)
    if not cites_case or NO_HISTORY_SENTENCE not in diagnosis:
        return result
    cleaned = " ".join(diagnosis.replace(NO_HISTORY_SENTENCE, "").split())
    return result.model_copy(update={"diagnostico_e_evidencias": cleaned or diagnosis})
