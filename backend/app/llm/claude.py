"""Analisador que usa o Claude (API da Anthropic) para gerar o diagnóstico."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from app.core.models import AnalysisResult, SimilarCase, Ticket
from app.llm.errors import AnalysisError
from app.prompts import SYSTEM_PROMPT, build_user_prompt

LOGGER = logging.getLogger("resolveai.llm.claude")

DEFAULT_MODEL = "claude-opus-5-5"


class ClaudeAnalyzer:
    """`Analyzer` que chama o Claude com saída estruturada (JSON validado)."""

    def __init__(
        self,
        client: Any | None = None,
        model: str = DEFAULT_MODEL,
        effort: str = "medium",
        max_tokens: int = 16000,
    ) -> None:
        if client is None:
            import anthropic

            # Lê ANTHROPIC_API_KEY do ambiente.
            client = anthropic.Anthropic(timeout=120.0)
        self.client = client
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens

    def analyze(
        self, ticket: Ticket, similar_cases: Sequence[SimilarCase]
    ) -> AnalysisResult:
        user_prompt = build_user_prompt(
            ticket.model_dump(),
            [case.model_dump(exclude_none=True) for case in similar_cases],
        )
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            output_format=AnalysisResult,
            output_config={"effort": self.effort},
            # Se a requisição for recusada pelos classificadores de segurança,
            # a API tenta de novo em outro modelo dentro da mesma chamada.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

        if response.stop_reason == "refusal":
            LOGGER.warning("Claude refused the analysis of ticket %s.", ticket.id)
            raise AnalysisError("O modelo recusou a análise deste chamado.")
        if response.stop_reason == "max_tokens":
            raise AnalysisError("A resposta do modelo foi cortada (max_tokens).")

        result = response.parsed_output
        if result is None:
            raise AnalysisError("O modelo não retornou uma análise válida.")
        return result
