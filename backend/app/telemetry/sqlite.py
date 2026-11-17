"""`TelemetryStore` em SQLite (arquivo local, sem servidor extra)."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

from app.core.telemetry import AnalysisEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    tenant_id TEXT,
    provider TEXT NOT NULL,
    model TEXT,
    status TEXT NOT NULL,
    error_type TEXT,
    cache_hit INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    cases_retrieved INTEGER NOT NULL,
    cases_used INTEGER NOT NULL,
    cases_cited INTEGER NOT NULL,
    best_distance REAL,
    confidence INTEGER
);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses (created_at);
CREATE TABLE IF NOT EXISTS feedback (
    analysis_id TEXT PRIMARY KEY REFERENCES analyses (id),
    helpful INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL
);
"""

CONFIDENCE_BUCKETS = [(0, 19), (20, 39), (40, 59), (60, 79), (80, 100)]


def _percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def _rate(part: int, total: int) -> float | None:
    return round(part / total, 4) if total else None


class SQLiteTelemetryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def record(self, event: AnalysisEvent) -> None:
        data = event.model_dump()
        data["created_at"] = event.created_at.astimezone(timezone.utc).isoformat()
        data["cache_hit"] = int(event.cache_hit)
        columns = ", ".join(data)
        placeholders = ", ".join(f":{key}" for key in data)
        with self._lock:
            self._conn.execute(
                f"INSERT INTO analyses ({columns}) VALUES ({placeholders})", data
            )
            self._conn.commit()

    def add_feedback(
        self, analysis_id: str, helpful: bool, comment: str | None = None
    ) -> bool:
        with self._lock:
            exists = self._conn.execute(
                "SELECT 1 FROM analyses WHERE id = ? AND status = 'ok'", (analysis_id,)
            ).fetchone()
            if not exists:
                return False
            # Uma avaliação por análise; avaliar de novo substitui a anterior.
            self._conn.execute(
                "INSERT INTO feedback (analysis_id, helpful, comment, created_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT (analysis_id) DO UPDATE SET "
                "helpful = excluded.helpful, comment = excluded.comment, "
                "created_at = excluded.created_at",
                (
                    analysis_id,
                    int(helpful),
                    comment,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()
        return True

    def _rows_since(self, since: datetime) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(
                "SELECT a.*, f.helpful FROM analyses a "
                "LEFT JOIN feedback f ON f.analysis_id = a.id "
                "WHERE a.created_at >= ? ORDER BY a.created_at",
                (since.isoformat(),),
            ).fetchall()

    def summary(self, days: int) -> dict:
        now = datetime.now(timezone.utc)
        start_day = (now - timedelta(days=days - 1)).date()
        since = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)
        rows = self._rows_since(since)

        ok = [row for row in rows if row["status"] == "ok"]
        generated = [row for row in ok if not row["cache_hit"]]
        durations = [row["duration_ms"] for row in generated]
        confidences = [row["confidence"] for row in ok if row["confidence"] is not None]
        rated = [row for row in ok if row["helpful"] is not None]
        helpful = sum(1 for row in rated if row["helpful"])

        per_day: dict[str, list[sqlite3.Row]] = {
            (start_day + timedelta(days=offset)).isoformat(): [] for offset in range(days)
        }
        for row in rows:
            day = row["created_at"][:10]
            if day in per_day:
                per_day[day].append(row)

        daily = []
        for day, day_rows in per_day.items():
            day_durations = [
                row["duration_ms"]
                for row in day_rows
                if row["status"] == "ok" and not row["cache_hit"]
            ]
            daily.append(
                {
                    "date": day,
                    "analyses": len(day_rows),
                    "errors": sum(1 for row in day_rows if row["status"] == "error"),
                    "p50_ms": int(median(day_durations)) if day_durations else None,
                    "p95_ms": _percentile(day_durations, 0.95),
                }
            )

        providers: dict[str, int] = {}
        for row in ok:
            label = row["provider"] + (f" · {row['model']}" if row["model"] else "")
            providers[label] = providers.get(label, 0) + 1

        return {
            "days": days,
            "since": start_day.isoformat(),
            "totals": {
                "analyses": len(rows),
                "ok": len(ok),
                "errors": len(rows) - len(ok),
                "cache_hits": sum(1 for row in ok if row["cache_hit"]),
                "rated": len(rated),
                "helpful": helpful,
                "not_helpful": len(rated) - helpful,
            },
            "rates": {
                "error": _rate(len(rows) - len(ok), len(rows)),
                "cache_hit": _rate(sum(1 for row in ok if row["cache_hit"]), len(ok)),
                "with_history": _rate(sum(1 for row in ok if row["cases_used"]), len(ok)),
                "cited_case": _rate(sum(1 for row in ok if row["cases_cited"]), len(ok)),
                "helpful": _rate(helpful, len(rated)),
            },
            "latency_ms": {
                "p50": int(median(durations)) if durations else None,
                "p95": _percentile(durations, 0.95),
            },
            "confidence": {
                "average": round(sum(confidences) / len(confidences), 1)
                if confidences
                else None,
                "buckets": [
                    {
                        "range": f"{low}–{high}",
                        "count": sum(1 for value in confidences if low <= value <= high),
                    }
                    for low, high in CONFIDENCE_BUCKETS
                ],
            },
            "providers": [
                {"label": label, "count": count}
                for label, count in sorted(providers.items(), key=lambda item: -item[1])
            ],
            "daily": daily,
        }

    def recent(self, limit: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT a.*, f.helpful FROM analyses a "
                "LEFT JOIN feedback f ON f.analysis_id = a.id "
                "ORDER BY a.created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["cache_hit"] = bool(item["cache_hit"])
            item["helpful"] = None if item["helpful"] is None else bool(item["helpful"])
            result.append(item)
        return result
