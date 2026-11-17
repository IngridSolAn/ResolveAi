"""Telemetria do comportamento da IA (para o painel de administradores).

Registra metadados de cada análise e a avaliação dos analistas. Por
privacidade, NÃO guarda título, descrição nem o texto gerado pela IA: só IDs,
números e o resultado da avaliação.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field


class AnalysisEvent(BaseModel):
    id: str
    created_at: datetime
    source: str = "glpi"
    ticket_id: str
    tenant_id: str | None = None
    provider: str  # ollama | claude | offline
    model: str | None = None
    status: str  # ok | error
    error_type: str | None = None
    cache_hit: bool = False
    duration_ms: int = Field(ge=0)
    cases_retrieved: int = 0
    cases_used: int = 0
    cases_cited: int = 0
    best_distance: float | None = None
    confidence: int | None = None


class TelemetryStore(Protocol):
    def record(self, event: AnalysisEvent) -> None: ...

    def add_feedback(
        self, analysis_id: str, helpful: bool, comment: str | None = None
    ) -> bool:
        """Grava a avaliação; retorna False se a análise não existe."""
        ...

    def summary(self, days: int) -> dict: ...

    def recent(self, limit: int) -> list[dict]: ...
