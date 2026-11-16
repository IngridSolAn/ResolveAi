"""Interfaces (portas) que conectores e adaptadores precisam implementar.

Para integrar uma nova plataforma (Zammad, osTicket, Jira Service Management,
Freshservice, ServiceNow...), basta implementar `TicketSource` traduzindo os
dados dela para `ResolvedTicket`. O restante do núcleo não muda.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.core.models import AnalysisResult, ResolvedTicket, SimilarCase, Ticket


class TicketSource(Protocol):
    """Origem de chamados solucionados de uma plataforma de ITSM."""

    name: str

    def fetch_resolved_since(self, since: str) -> tuple[list[ResolvedTicket], str]:
        """Retorna os chamados solucionados alterados desde `since` e a maior
        data de alteração vista (mesmo de chamados descartados), no formato
        "AAAA-MM-DD HH:MM:SS"."""
        ...


class KnowledgeBase(Protocol):
    """Base de conhecimento vetorial usada pelo RAG."""

    def upsert(self, tickets: Sequence[ResolvedTicket]) -> None: ...

    def search(self, query: str, tenant_id: str, limit: int) -> list[SimilarCase]:
        """Busca casos parecidos somente dentro de `tenant_id`."""
        ...


class Analyzer(Protocol):
    """Gera o diagnóstico a partir do chamado e dos casos recuperados."""

    def analyze(
        self, ticket: Ticket, similar_cases: Sequence[SimilarCase]
    ) -> AnalysisResult: ...
