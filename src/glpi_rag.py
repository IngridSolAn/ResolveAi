"""Historical and incremental indexing of resolved GLPI tickets in ChromaDB."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol

LOGGER = logging.getLogger("resolveai.glpi_rag")
INITIAL_WATERMARK = "1970-01-01 00:00:00"

TICKET_DOCUMENT_QUERY = """
SELECT
    t.id AS ticket_id,
    t.entities_id AS entities_id,
    t.name AS title,
    t.content AS description,
    t.status AS status,
    t.date_mod AS date_mod,
    'solution' AS source_type,
    s.content AS source_text,
    s.date_creation AS source_date
FROM glpi_tickets AS t
INNER JOIN glpi_itilsolutions AS s
    ON s.items_id = t.id
    AND s.itemtype = 'Ticket'
WHERE t.status IN (5, 6)
    AND t.date_mod >= :since

UNION ALL

SELECT
    t.id AS ticket_id,
    t.entities_id AS entities_id,
    t.name AS title,
    t.content AS description,
    t.status AS status,
    t.date_mod AS date_mod,
    'followup' AS source_type,
    f.content AS source_text,
    f.date_creation AS source_date
FROM glpi_tickets AS t
INNER JOIN glpi_itilfollowups AS f
    ON f.items_id = t.id
    AND f.itemtype = 'Ticket'
WHERE t.status IN (5, 6)
    AND t.date_mod >= :since
    AND EXISTS (
        SELECT 1
        FROM glpi_itilsolutions AS s
        WHERE s.items_id = t.id
            AND s.itemtype = 'Ticket'
    )
ORDER BY ticket_id, source_date
"""

SIGNATURE_START = re.compile(
    r"(?im)^\s*(?:"
    r"--\s*$|"
    r"atenciosamente[,!.]?\s*$|"
    r"cordialmente[,!.]?\s*$|"
    r"obrigad[oa][,!.\s]*$|"
    r"best regards[,!.]?\s*$|"
    r"kind regards[,!.]?\s*$|"
    r"regards[,!.]?\s*$|"
    r"sent from my (?:iphone|ipad|android).*$"
    r")"
)


class TextExtractor(HTMLParser):
    """Extract readable text from HTML while retaining paragraph boundaries."""

    BLOCK_TAGS = {
        "address",
        "article",
        "br",
        "div",
        "li",
        "p",
        "section",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def clean_glpi_text(value: Any) -> str:
    """Remove HTML and common email signatures from a GLPI text field."""
    if value is None:
        return ""

    parser = TextExtractor()
    parser.feed(str(value))
    parser.close()

    text = "".join(parser.parts).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    signature = SIGNATURE_START.search(text)
    if signature:
        text = text[: signature.start()].rstrip()

    return text


def _format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"Invalid GLPI date_mod value: {value!r}")


def _load_watermark(path: Path) -> str:
    if not path.exists():
        return INITIAL_WATERMARK

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        watermark = state["last_date_mod"]
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
            json.dumps({"last_date_mod": watermark}, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    except OSError as error:
        raise RuntimeError(f"Could not save RAG sync state at {path}.") from error


class VectorCollection(Protocol):
    def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, int | str]],
    ) -> None: ...


def _make_ticket_documents(rows: list[Any]) -> list[dict[str, Any]]:
    tickets: dict[int, dict[str, Any]] = {}

    for row in rows:
        ticket_id = int(row["ticket_id"])
        entities_id = row["entities_id"]
        if entities_id is None:
            LOGGER.warning("Skipping ticket %s without an entity ID.", ticket_id)
            continue

        current = tickets.setdefault(
            ticket_id,
            {
                "ticket_id": ticket_id,
                "entities_id": int(entities_id),
                "title": clean_glpi_text(row["title"]),
                "description": clean_glpi_text(row["description"]),
                "status": int(row["status"]),
                "date_mod": _format_datetime(row["date_mod"]),
                "solutions": [],
                "followups": [],
            },
        )

        source_text = clean_glpi_text(row["source_text"])
        if source_text:
            source_type = row["source_type"]
            if source_type == "solution":
                current["solutions"].append(source_text)
            elif source_type == "followup":
                current["followups"].append(source_text)

    documents: list[dict[str, Any]] = []
    for ticket in tickets.values():
        if not ticket["solutions"]:
            LOGGER.warning(
                "Skipping ticket %s because it has no non-empty solution.",
                ticket["ticket_id"],
            )
            continue

        sections = [
            f"Chamado: {ticket['title']}",
            f"Descrição: {ticket['description']}",
            "Solução: " + "\n".join(ticket["solutions"]),
        ]
        if ticket["followups"]:
            sections.append("Acompanhamentos: " + "\n".join(ticket["followups"]))
        ticket["document"] = "\n\n".join(section for section in sections if section)
        documents.append(ticket)

    return documents


def index_incremental(
    engine: Any,
    collection: VectorCollection,
    state_path: Path,
    overlap_seconds: int = 300,
    batch_size: int = 100,
) -> int:
    """Index tickets changed since the saved date_mod watermark."""
    if overlap_seconds < 0:
        raise ValueError("overlap_seconds must be zero or greater.")
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero.")

    try:
        from sqlalchemy import text
    except ImportError as error:
        raise RuntimeError(
            "SQLAlchemy is required. Install requirements-rag.txt."
        ) from error

    watermark = _load_watermark(state_path)
    since = datetime.strptime(watermark, "%Y-%m-%d %H:%M:%S") - timedelta(
        seconds=overlap_seconds
    )
    since_value = since.strftime("%Y-%m-%d %H:%M:%S")

    with engine.connect() as connection:
        rows = list(
            connection.execute(
                text(TICKET_DOCUMENT_QUERY),
                {"since": since_value},
            ).mappings()
        )

    newest_date_mod = max(
        [watermark, *[_format_datetime(row["date_mod"]) for row in rows]]
    )
    tickets = _make_ticket_documents(rows)
    if not tickets:
        LOGGER.info("No changed resolved tickets found since %s.", since_value)
        _save_watermark(state_path, newest_date_mod)
        return 0

    indexed = 0
    for start in range(0, len(tickets), batch_size):
        batch = tickets[start : start + batch_size]
        collection.upsert(
            ids=[str(ticket["ticket_id"]) for ticket in batch],
            documents=[ticket["document"] for ticket in batch],
            metadatas=[
                {
                    "ticket_id": ticket["ticket_id"],
                    "entities_id": ticket["entities_id"],
                    "status": ticket["status"],
                    "date_mod": ticket["date_mod"],
                }
                for ticket in batch
            ],
        )
        indexed += len(batch)
    _save_watermark(state_path, newest_date_mod)
    LOGGER.info("Indexed %s tickets through %s.", indexed, newest_date_mod)
    return indexed


def search_by_entity(
    collection: Any,
    query: str,
    entities_id: int,
    limit: int = 5,
) -> dict[str, Any]:
    """Search only within one GLPI entity; callers must pass the authorized entity."""
    if entities_id < 0:
        raise ValueError("entities_id must be zero or greater.")
    if limit < 1:
        raise ValueError("limit must be greater than zero.")

    return collection.query(
        query_texts=[query],
        n_results=limit,
        where={"entities_id": entities_id},
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Incrementally index closed GLPI tickets in ChromaDB."
    )
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    database_url = os.environ.get("GLPI_READONLY_DATABASE_URL")
    if not database_url:
        parser.error("Set GLPI_READONLY_DATABASE_URL to the read-only replica URL.")

    chroma_path = Path(os.environ.get("CHROMA_PATH", "data/chroma"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "glpi_tickets")
    state_path = Path(os.environ.get("RAG_STATE_PATH", "data/glpi_rag_state.json"))
    overlap_seconds = int(os.environ.get("RAG_SYNC_OVERLAP_SECONDS", "300"))

    try:
        from chromadb import PersistentClient
        from sqlalchemy import create_engine
    except ImportError as error:
        raise SystemExit(
            "RAG dependencies are missing. Install requirements-rag.txt."
        ) from error

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )
    client = PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    try:
        index_incremental(
            engine,
            collection,
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
