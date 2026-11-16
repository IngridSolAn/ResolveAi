"""Conector GLPI: lê chamados solucionados e traduz para o modelo neutro.

É o único módulo que conhece as tabelas do GLPI. Use uma conta somente leitura,
de preferência apontando para uma réplica do banco.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from app.core.models import ResolvedTicket

LOGGER = logging.getLogger("resolveai.connectors.glpi")

# Status 5 = Solucionado, 6 = Fechado.
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
    """Extrai texto legível de HTML preservando quebras de parágrafo."""

    BLOCK_TAGS = {"address", "article", "br", "div", "li", "p", "section", "tr"}

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
    """Remove HTML e assinaturas de e-mail comuns de um campo de texto do GLPI."""
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


def format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"Invalid GLPI date_mod value: {value!r}")


def rows_to_tickets(rows: list[Any]) -> list[ResolvedTicket]:
    """Agrupa as linhas da consulta (uma por solução/acompanhamento) por chamado."""
    grouped: dict[int, dict[str, Any]] = {}

    for row in rows:
        ticket_id = int(row["ticket_id"])
        if row["entities_id"] is None:
            LOGGER.warning("Skipping ticket %s without an entity ID.", ticket_id)
            continue

        current = grouped.setdefault(
            ticket_id,
            {
                "source": "glpi",
                "id": str(ticket_id),
                "tenant_id": str(int(row["entities_id"])),
                "title": clean_glpi_text(row["title"]),
                "description": clean_glpi_text(row["description"]),
                "updated_at": format_datetime(row["date_mod"]),
                "solutions": [],
                "followups": [],
            },
        )

        source_text = clean_glpi_text(row["source_text"])
        if source_text:
            if row["source_type"] == "solution":
                current["solutions"].append(source_text)
            elif row["source_type"] == "followup":
                current["followups"].append(source_text)

    tickets: list[ResolvedTicket] = []
    for data in grouped.values():
        if not data["solutions"]:
            LOGGER.warning(
                "Skipping ticket %s because it has no non-empty solution.", data["id"]
            )
            continue
        tickets.append(ResolvedTicket(**data))
    return tickets


class GLPIDatabaseSource:
    """`TicketSource` que lê direto do banco (réplica somente leitura) do GLPI."""

    name = "glpi"

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def fetch_resolved_since(self, since: str) -> tuple[list[ResolvedTicket], str]:
        from sqlalchemy import text

        with self.engine.connect() as connection:
            rows = list(
                connection.execute(
                    text(TICKET_DOCUMENT_QUERY), {"since": since}
                ).mappings()
            )

        newest = max((format_datetime(row["date_mod"]) for row in rows), default=since)
        return rows_to_tickets(rows), newest
