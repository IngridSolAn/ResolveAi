"""Casos de uso do núcleo: analisar um chamado e indexar o histórico."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from app.core.models import AnalysisResult, SimilarCase, Ticket
from app.core.ports import Analyzer, KnowledgeBase, TicketSource

LOGGER = logging.getLogger("resolveai.core")
INITIAL_WATERMARK = "1970-01-01 00:00:00"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class AnalysisOutcome:
    """Resultado da análise mais o que aconteceu no RAG (para a telemetria)."""

    result: AnalysisResult
    retrieved: list[SimilarCase] = field(default_factory=list)
    used: list[SimilarCase] = field(default_factory=list)

    @property
    def best_distance(self) -> float | None:
        distances = [case.distance for case in self.retrieved if case.distance is not None]
        return min(distances) if distances else None

    @property
    def cited(self) -> list[SimilarCase]:
        """Casos enviados à IA que ela citou pelo ID no diagnóstico."""
        text = self.result.diagnostico_e_evidencias
        return [case for case in self.used if f"#{case.id}" in text]


def run_analysis(
    ticket: Ticket,
    knowledge_base: KnowledgeBase | None,
    analyzer: Analyzer,
    limit: int = 5,
    max_distance: float | None = None,
) -> AnalysisOutcome:
    """Recupera casos parecidos (RAG) e pede o diagnóstico ao analisador.

    `max_distance` descarta casos pouco parecidos antes de enviá-los à IA:
    casos irrelevantes no contexto confundem principalmente modelos menores.
    """
    retrieved: list[SimilarCase] = []
    query = f"{ticket.title}\n{ticket.description}".strip()
    if knowledge_base is not None and ticket.tenant_id and query:
        try:
            retrieved = knowledge_base.search(query, ticket.tenant_id, limit)
        except Exception:
            # Sem histórico a análise continua: o prompt já orienta o modelo a
            # declarar que não encontrou casos semelhantes.
            LOGGER.exception("Falha ao consultar a base de conhecimento.")
    used = retrieved
    if max_distance is not None:
        used = [
            case
            for case in retrieved
            if case.distance is None or case.distance <= max_distance
        ]
    return AnalysisOutcome(
        result=analyzer.analyze(ticket, used), retrieved=retrieved, used=used
    )


def analyze_ticket(
    ticket: Ticket,
    knowledge_base: KnowledgeBase | None,
    analyzer: Analyzer,
    limit: int = 5,
    max_distance: float | None = None,
) -> AnalysisResult:
    """Atalho para `run_analysis` quando só o resultado interessa."""
    return run_analysis(ticket, knowledge_base, analyzer, limit, max_distance).result


def _load_watermark(path: Path) -> str:
    if not path.exists():
        return INITIAL_WATERMARK
    try:
        watermark = json.loads(path.read_text(encoding="utf-8"))["last_date_mod"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise RuntimeError(f"Could not read RAG sync state at {path}.") from error
    if not isinstance(watermark, str) or not watermark.strip():
        raise RuntimeError(f"Invalid last_date_mod in RAG sync state at {path}.")
    return watermark


def _save_watermark(path: Path, watermark: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_text(
            json.dumps({"last_date_mod": watermark}, indent=2), encoding="utf-8"
        )
        os.replace(temporary_path, path)
    except OSError as error:
        raise RuntimeError(f"Could not save RAG sync state at {path}.") from error


def index_incremental(
    source: TicketSource,
    knowledge_base: KnowledgeBase,
    state_path: Path,
    overlap_seconds: int = 300,
    batch_size: int = 100,
) -> int:
    """Indexa os chamados solucionados alterados desde a última sincronização."""
    if overlap_seconds < 0:
        raise ValueError("overlap_seconds must be zero or greater.")
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero.")

    watermark = _load_watermark(state_path)
    since = datetime.strptime(watermark, DATETIME_FORMAT) - timedelta(
        seconds=overlap_seconds
    )
    since_value = since.strftime(DATETIME_FORMAT)

    tickets, newest_seen = source.fetch_resolved_since(since_value)
    newest = max(watermark, newest_seen)

    for start in range(0, len(tickets), batch_size):
        knowledge_base.upsert(tickets[start : start + batch_size])

    _save_watermark(state_path, newest)
    LOGGER.info(
        "Indexed %s tickets from %s through %s.", len(tickets), source.name, newest
    )
    return len(tickets)
