"""Indexa no ChromaDB os chamados solucionados do GLPI.

Uso (dentro de backend/):  python -m app.index
Execute periodicamente (cron, agendador); cada execução é incremental.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from app.config import Settings
from app.connectors.glpi import GLPIDatabaseSource
from app.core.service import index_incremental
from app.knowledge.chroma import ChromaKnowledgeBase, create_collection


def _load_dotenv() -> None:
    """Fora do Docker, lê o .env da raiz do projeto (se existir)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def main() -> None:
    _load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    database_url = os.environ.get("GLPI_READONLY_DATABASE_URL")
    if not database_url:
        parser.error("Set GLPI_READONLY_DATABASE_URL to the read-only replica URL.")

    settings = Settings()
    state_path = Path(os.environ.get("RAG_STATE_PATH", "data/glpi_rag_state.json"))
    overlap_seconds = int(os.environ.get("RAG_SYNC_OVERLAP_SECONDS", "300"))

    from sqlalchemy import create_engine

    engine = create_engine(
        database_url, pool_pre_ping=True, connect_args={"connect_timeout": 10}
    )
    knowledge_base = ChromaKnowledgeBase(
        create_collection(
            host=settings.chroma_host or None,
            port=settings.chroma_port,
            path=settings.chroma_path,
            name=settings.chroma_collection,
        )
    )
    try:
        index_incremental(
            GLPIDatabaseSource(engine),
            knowledge_base,
            state_path,
            overlap_seconds=overlap_seconds,
            batch_size=args.batch_size,
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()
