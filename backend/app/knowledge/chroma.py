"""Base de conhecimento vetorial no ChromaDB."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.models import ResolvedTicket, SimilarCase


class ChromaKnowledgeBase:
    """`KnowledgeBase` sobre uma coleção do ChromaDB.

    Os IDs incluem a plataforma de origem ("glpi:123"), então chamados de
    plataformas diferentes podem conviver na mesma coleção sem colidir.
    """

    def __init__(self, collection: Any) -> None:
        self.collection = collection

    def upsert(self, tickets: Sequence[ResolvedTicket]) -> None:
        if not tickets:
            return
        self.collection.upsert(
            ids=[f"{ticket.source}:{ticket.id}" for ticket in tickets],
            documents=[ticket.to_document() for ticket in tickets],
            metadatas=[
                {
                    "source": ticket.source,
                    "ticket_id": ticket.id,
                    "tenant_id": ticket.tenant_id,
                    "updated_at": ticket.updated_at,
                }
                for ticket in tickets
            ],
        )

    def search(self, query: str, tenant_id: str, limit: int = 5) -> list[SimilarCase]:
        if not tenant_id:
            raise ValueError("tenant_id is required.")
        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        result = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where={"tenant_id": tenant_id},
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[None] * len(ids)])[0]

        return [
            SimilarCase(
                id=str((metadata or {}).get("ticket_id", doc_id)),
                source=str((metadata or {}).get("source", "")),
                content=document or "",
                distance=distance,
            )
            for doc_id, document, metadata, distance in zip(
                ids, documents, metadatas, distances
            )
        ]


def create_collection(
    *,
    host: str | None = None,
    port: int = 8000,
    path: str = "data/chroma",
    name: str = "resolveai_tickets",
) -> Any:
    """Conecta ao Chroma remoto (`host`) ou usa um diretório local (`path`)."""
    import chromadb

    if host:
        client = chromadb.HttpClient(host=host, port=port)
    else:
        client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
