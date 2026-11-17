from datetime import datetime, timedelta, timezone

from app.core.telemetry import AnalysisEvent
from app.telemetry.sqlite import SQLiteTelemetryStore


def event(id: str, **overrides) -> AnalysisEvent:
    data = {
        "id": id,
        "created_at": datetime.now(timezone.utc),
        "ticket_id": "7",
        "provider": "ollama",
        "model": "qwen2.5:7b",
        "status": "ok",
        "duration_ms": 1000,
        "confidence": 65,
        "cases_used": 1,
    }
    return AnalysisEvent(**{**data, **overrides})


def test_summary_aggregates_rates_latency_and_buckets() -> None:
    store = SQLiteTelemetryStore(":memory:")
    store.record(event("a", duration_ms=1000, confidence=65, cases_cited=1))
    store.record(event("b", duration_ms=3000, confidence=30, cases_used=0))
    store.record(event("c", cache_hit=True, duration_ms=5))
    store.record(event("d", status="error", error_type="AnalysisError", confidence=None))
    store.add_feedback("a", True)
    store.add_feedback("b", False)

    summary = store.summary(7)

    assert summary["totals"]["analyses"] == 4
    assert summary["totals"]["errors"] == 1
    assert summary["rates"]["error"] == 0.25
    assert summary["rates"]["helpful"] == 0.5
    assert summary["rates"]["cache_hit"] == round(1 / 3, 4)
    # Latência ignora respostas do cache e erros.
    assert summary["latency_ms"]["p50"] == 2000
    buckets = {b["range"]: b["count"] for b in summary["confidence"]["buckets"]}
    assert buckets["60–79"] == 2 and buckets["20–39"] == 1
    assert len(summary["daily"]) == 7
    assert summary["daily"][-1]["analyses"] == 4


def test_summary_excludes_events_outside_the_window() -> None:
    store = SQLiteTelemetryStore(":memory:")
    old = datetime.now(timezone.utc) - timedelta(days=40)
    store.record(event("old", created_at=old))
    store.record(event("new"))

    assert store.summary(30)["totals"]["analyses"] == 1


def test_feedback_only_for_successful_analyses_and_can_change() -> None:
    store = SQLiteTelemetryStore(":memory:")
    store.record(event("ok"))
    store.record(event("err", status="error"))

    assert store.add_feedback("err", True) is False
    assert store.add_feedback("ok", False) is True
    assert store.add_feedback("ok", True) is True
    assert store.summary(1)["totals"]["helpful"] == 1
    assert store.recent(5)[0]["helpful"] in (True, None)
