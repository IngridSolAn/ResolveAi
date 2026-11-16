import json
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.connectors.glpi import GLPIDatabaseSource, clean_glpi_text, rows_to_tickets
from app.core.service import index_incremental
from app.knowledge.chroma import ChromaKnowledgeBase


def make_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "ticket_id": 41,
        "entities_id": 7,
        "title": "Erro no acesso",
        "description": "<p>Usuário não entra.</p>",
        "status": 6,
        "date_mod": datetime(2026, 1, 2, 3, 4, 5),
        "source_type": "solution",
        "source_text": "<p>Senha redefinida.</p>",
        "source_date": datetime(2026, 1, 2, 3, 0, 0),
    }
    return {**row, **overrides}


def test_clean_glpi_text_removes_html_and_email_signature() -> None:
    text = clean_glpi_text(
        "<p>Falha de rede&nbsp;na filial.</p>"
        "<p>Atenciosamente,<br>Equipe de suporte</p>"
    )

    assert text == "Falha de rede na filial."


def test_rows_to_tickets_maps_entity_to_tenant_and_combines_text() -> None:
    followup = make_row(source_type="followup", source_text="Usuário confirmou.")

    tickets = rows_to_tickets([make_row(), followup])

    assert len(tickets) == 1
    ticket = tickets[0]
    assert (ticket.source, ticket.id, ticket.tenant_id) == ("glpi", "41", "7")
    assert ticket.description == "Usuário não entra."
    assert "Senha redefinida." in ticket.to_document()
    assert "Usuário confirmou." in ticket.to_document()


def test_rows_to_tickets_skips_tickets_without_entity_or_solution() -> None:
    no_entity = make_row(ticket_id=1, entities_id=None)
    empty_solution = make_row(ticket_id=2, source_text="<p> </p>")

    assert rows_to_tickets([no_entity, empty_solution]) == []


class FakeCollection:
    def __init__(self) -> None:
        self.query_args: dict[str, Any] = {}
        self.upserts: list[dict[str, Any]] = []

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_args = kwargs
        return {
            "ids": [["glpi:41"]],
            "documents": [["Chamado: Erro no acesso"]],
            "metadatas": [[{"source": "glpi", "ticket_id": "41", "tenant_id": "7"}]],
            "distances": [[0.12]],
        }

    def upsert(self, **kwargs: Any) -> None:
        self.upserts.append(kwargs)


def test_search_always_filters_by_tenant() -> None:
    collection = FakeCollection()

    cases = ChromaKnowledgeBase(collection).search("erro de acesso", "7", limit=3)

    assert collection.query_args["where"] == {"tenant_id": "7"}
    assert collection.query_args["n_results"] == 3
    assert cases[0].id == "41"
    assert cases[0].distance == 0.12


def test_search_rejects_missing_tenant() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        ChromaKnowledgeBase(FakeCollection()).search("erro", "")


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def __iter__(self):
        return iter(self.rows)


class FakeConnection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.parameters: dict[str, str] | None = None

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str, parameters: dict[str, str]) -> FakeResult:
        assert "glpi_itilsolutions" in query
        assert "glpi_itilfollowups" in query
        self.parameters = parameters
        return FakeResult(self.rows)


class FakeEngine:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def connect(self) -> FakeConnection:
        return self.connection


@pytest.fixture
def fake_sqlalchemy(monkeypatch: pytest.MonkeyPatch) -> None:
    sqlalchemy = ModuleType("sqlalchemy")
    sqlalchemy.text = lambda query: query
    monkeypatch.setitem(sys.modules, "sqlalchemy", sqlalchemy)


@pytest.mark.usefixtures("fake_sqlalchemy")
def test_index_incremental_uses_watermark_and_persists_tenant_metadata(
    tmp_path: Path,
) -> None:
    connection = FakeConnection([make_row()])
    collection = FakeCollection()
    state_path = tmp_path / "nested" / "state.json"

    count = index_incremental(
        GLPIDatabaseSource(FakeEngine(connection)),
        ChromaKnowledgeBase(collection),
        state_path,
        overlap_seconds=0,
    )

    assert count == 1
    assert connection.parameters == {"since": "1970-01-01 00:00:00"}
    assert collection.upserts[0]["ids"] == ["glpi:41"]
    assert collection.upserts[0]["metadatas"][0]["tenant_id"] == "7"
    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "last_date_mod": "2026-01-02 03:04:05"
    }


@pytest.mark.usefixtures("fake_sqlalchemy")
def test_index_incremental_advances_watermark_even_when_tickets_are_skipped(
    tmp_path: Path,
) -> None:
    connection = FakeConnection([make_row(entities_id=None)])
    collection = FakeCollection()
    state_path = tmp_path / "state.json"

    count = index_incremental(
        GLPIDatabaseSource(FakeEngine(connection)),
        ChromaKnowledgeBase(collection),
        state_path,
        overlap_seconds=0,
    )

    assert count == 0
    assert collection.upserts == []
    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "last_date_mod": "2026-01-02 03:04:05"
    }
