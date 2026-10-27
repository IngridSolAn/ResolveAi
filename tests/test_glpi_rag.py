import json
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from src.glpi_rag import (
    _make_ticket_documents,
    clean_glpi_text,
    index_incremental,
    search_by_entity,
)


def test_clean_glpi_text_removes_html_and_email_signature() -> None:
    text = clean_glpi_text(
        "<p>Falha de rede&nbsp;na filial.</p>"
        "<p>Atenciosamente,<br>Equipe de suporte</p>"
    )

    assert text == "Falha de rede na filial."


def test_make_ticket_documents_keeps_entity_and_combines_related_text() -> None:
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
    followup = {**row, "source_type": "followup", "source_text": "Usuário confirmou."}

    documents = _make_ticket_documents([row, followup])

    assert len(documents) == 1
    assert documents[0]["ticket_id"] == 41
    assert documents[0]["entities_id"] == 7
    assert "Senha redefinida." in documents[0]["document"]
    assert "Usuário confirmou." in documents[0]["document"]


class FakeCollection:
    def __init__(self) -> None:
        self.query_args: dict[str, Any] = {}

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_args = kwargs
        return {"ids": [["41"]]}


def test_search_by_entity_always_filters_by_entity() -> None:
    collection = FakeCollection()

    search_by_entity(collection, "erro de acesso", entities_id=7, limit=3)

    assert collection.query_args["where"] == {"entities_id": 7}
    assert collection.query_args["n_results"] == 3


@pytest.mark.parametrize("entities_id", [-1])
def test_search_by_entity_rejects_invalid_entity(entities_id: int) -> None:
    with pytest.raises(ValueError, match="entities_id"):
        search_by_entity(FakeCollection(), "erro", entities_id)


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


class FakeIndexCollection(FakeCollection):
    def __init__(self) -> None:
        super().__init__()
        self.upserts: list[dict[str, Any]] = []

    def upsert(self, **kwargs: Any) -> None:
        self.upserts.append(kwargs)


def test_index_incremental_uses_watermark_and_persists_entity_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row: dict[str, Any] = {
        "ticket_id": 41,
        "entities_id": 7,
        "title": "Erro no acesso",
        "description": "Usuário não entra.",
        "status": 6,
        "date_mod": datetime(2026, 1, 2, 3, 4, 5),
        "source_type": "solution",
        "source_text": "Senha redefinida.",
        "source_date": datetime(2026, 1, 2, 3, 0, 0),
    }
    connection = FakeConnection([row])
    collection = FakeIndexCollection()
    sqlalchemy = ModuleType("sqlalchemy")
    sqlalchemy.text = lambda query: query
    monkeypatch.setitem(sys.modules, "sqlalchemy", sqlalchemy)
    state_path = tmp_path / "nested" / "state.json"

    count = index_incremental(
        FakeEngine(connection), collection, state_path, overlap_seconds=0
    )

    assert count == 1
    assert connection.parameters == {"since": "1970-01-01 00:00:00"}
    assert collection.upserts[0]["ids"] == ["41"]
    assert collection.upserts[0]["metadatas"][0]["entities_id"] == 7
    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "last_date_mod": "2026-01-02 03:04:05"
    }
