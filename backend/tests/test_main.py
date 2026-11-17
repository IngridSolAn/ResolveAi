from collections.abc import Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.models import AnalysisResult, ConfidenceLevel, SimilarCase, Ticket
from app.core.cache import AnalysisCache
from app.main import (
    app,
    get_analysis_cache,
    get_analyzer,
    get_knowledge_base,
    get_settings,
    get_telemetry,
)
from app.telemetry.sqlite import SQLiteTelemetryStore

client = TestClient(app)


class RecordingAnalyzer:
    def __init__(self) -> None:
        self.calls: list[tuple[Ticket, list[SimilarCase]]] = []

    def analyze(
        self, ticket: Ticket, similar_cases: Sequence[SimilarCase]
    ) -> AnalysisResult:
        self.calls.append((ticket, list(similar_cases)))
        return AnalysisResult(
            diagnostico_e_evidencias="Diagnóstico de teste.",
            nivel_de_confianca=ConfidenceLevel(percentual=55, justificativa="Teste."),
            passos_sugeridos_de_teste=["1. Verificar o log."],
        )


class FakeKnowledgeBase:
    def __init__(self) -> None:
        self.searches: list[dict[str, Any]] = []

    def upsert(self, tickets: Any) -> None:
        raise AssertionError("not used")

    def search(self, query: str, tenant_id: str, limit: int) -> list[SimilarCase]:
        self.searches.append({"query": query, "tenant_id": tenant_id, "limit": limit})
        return [SimilarCase(id="41", source="glpi", content="Senha redefinida.")]


@pytest.fixture
def analyzer() -> RecordingAnalyzer:
    return RecordingAnalyzer()


@pytest.fixture
def knowledge_base() -> FakeKnowledgeBase:
    return FakeKnowledgeBase()


@pytest.fixture(autouse=True)
def overrides(analyzer: RecordingAnalyzer, knowledge_base: FakeKnowledgeBase):
    app.dependency_overrides[get_analyzer] = lambda: analyzer
    app.dependency_overrides[get_knowledge_base] = lambda: knowledge_base
    app.dependency_overrides[get_settings] = lambda: Settings(api_token="")
    cache = AnalysisCache()
    app.dependency_overrides[get_analysis_cache] = lambda: cache
    store = SQLiteTelemetryStore(":memory:")
    app.dependency_overrides[get_telemetry] = lambda: store
    yield
    app.dependency_overrides.clear()


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "resolveai-backend"}


def test_analyze_uses_rag_within_ticket_tenant(
    analyzer: RecordingAnalyzer, knowledge_base: FakeKnowledgeBase
) -> None:
    response = client.post(
        "/analyze",
        json={
            "ticket_id": 101,
            "title": "Sem acesso",
            "description": "Usuário não entra no sistema.",
            "tenant_id": 7,
        },
    )

    assert response.status_code == 200
    assert response.json()["nivel_de_confianca"]["percentual"] == 55
    assert knowledge_base.searches[0]["tenant_id"] == "7"
    ticket, cases = analyzer.calls[0]
    assert ticket.id == "101"
    assert [case.id for case in cases] == ["41"]


def test_analyze_without_tenant_skips_rag(
    analyzer: RecordingAnalyzer, knowledge_base: FakeKnowledgeBase
) -> None:
    response = client.post(
        "/analyze", json={"ticket_id": 5, "title": "Impressora", "description": ""}
    )

    assert response.status_code == 200
    assert knowledge_base.searches == []
    assert analyzer.calls[0][1] == []


def test_analyze_requires_token_when_configured() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(api_token="segredo")
    body = {"ticket_id": 1, "title": "x"}

    assert client.post("/analyze", json=body).status_code == 401
    ok = client.post(
        "/analyze", json=body, headers={"Authorization": "Bearer segredo"}
    )
    assert ok.status_code == 200


def test_analyze_returns_502_when_analyzer_fails() -> None:
    class BrokenAnalyzer:
        def analyze(self, ticket: Ticket, similar_cases: Any) -> AnalysisResult:
            raise RuntimeError("boom")

    app.dependency_overrides[get_analyzer] = lambda: BrokenAnalyzer()

    response = client.post("/analyze", json={"ticket_id": 1, "title": "x"})

    assert response.status_code == 502


def test_analyze_reuses_cached_result_until_refresh(
    analyzer: RecordingAnalyzer,
) -> None:
    body = {"ticket_id": 9, "title": "Wi-Fi", "description": "cai", "tenant_id": 1}

    assert client.post("/analyze", json=body).status_code == 200
    assert client.post("/analyze", json=body).status_code == 200
    assert len(analyzer.calls) == 1

    client.post("/analyze", json={**body, "refresh": True})
    assert len(analyzer.calls) == 2

    client.post("/analyze", json={**body, "description": "cai sempre"})
    assert len(analyzer.calls) == 3


def _telemetry() -> SQLiteTelemetryStore:
    return app.dependency_overrides[get_telemetry]()


def test_analyze_returns_analysis_id_and_records_telemetry() -> None:
    body = {"ticket_id": 7, "title": "Wi-Fi", "description": "cai", "tenant_id": 0}

    first = client.post("/analyze", json=body).json()
    second = client.post("/analyze", json=body).json()

    assert first["analysis_id"] != second["analysis_id"]
    rows = _telemetry().recent(10)
    assert [row["cache_hit"] for row in rows] == [True, False]
    assert rows[1]["cases_used"] == 1
    assert rows[1]["confidence"] == 55
    assert rows[1]["provider"] == "RecordingAnalyzer"


def test_analyze_error_is_recorded() -> None:
    class BrokenAnalyzer:
        def analyze(self, ticket: Ticket, similar_cases: Any) -> AnalysisResult:
            raise RuntimeError("boom")

    app.dependency_overrides[get_analyzer] = lambda: BrokenAnalyzer()

    client.post("/analyze", json={"ticket_id": 1, "title": "x"})

    row = _telemetry().recent(1)[0]
    assert (row["status"], row["error_type"]) == ("error", "RuntimeError")


def test_feedback_is_stored_and_counted() -> None:
    analysis = client.post("/analyze", json={"ticket_id": 3, "title": "VPN"}).json()

    response = client.post(
        "/feedback", json={"analysis_id": analysis["analysis_id"], "helpful": True}
    )

    assert response.status_code == 204
    assert _telemetry().summary(7)["totals"]["helpful"] == 1
    missing = client.post("/feedback", json={"analysis_id": "nope", "helpful": False})
    assert missing.status_code == 404


def test_admin_endpoints_are_disabled_without_admin_token() -> None:
    assert client.get("/admin/metrics").status_code == 403


def test_admin_endpoints_require_the_admin_token_not_the_api_token() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_token="plugin", admin_token="admin"
    )
    client.post(
        "/analyze",
        json={"ticket_id": 1, "title": "x"},
        headers={"Authorization": "Bearer plugin"},
    )

    assert client.get("/admin/metrics").status_code == 401
    plugin = client.get("/admin/metrics", headers={"Authorization": "Bearer plugin"})
    assert plugin.status_code == 401

    admin = client.get("/admin/metrics", headers={"Authorization": "Bearer admin"})
    assert admin.status_code == 200
    assert admin.json()["totals"]["analyses"] == 1
    recent = client.get("/admin/analyses", headers={"Authorization": "Bearer admin"})
    assert recent.json()[0]["ticket_id"] == "1"
