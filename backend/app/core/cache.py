"""Cache em memória das análises.

A análise com IA local pode levar minutos; reabrir o mesmo chamado sem
mudanças devolve o resultado guardado. A chave inclui o conteúdo do chamado,
então qualquer edição no título ou na descrição gera uma nova análise.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict

from app.core.models import AnalysisResult, Ticket


class AnalysisCache:
    def __init__(self, ttl_seconds: float = 86400, max_items: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._items: OrderedDict[str, tuple[float, AnalysisResult]] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def key(ticket: Ticket, namespace: str = "") -> str:
        raw = json.dumps(
            [namespace, ticket.model_dump()], sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> AnalysisResult | None:
        if self.ttl_seconds <= 0:
            return None
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            stored_at, result = item
            if time.monotonic() - stored_at > self.ttl_seconds:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return result

    def set(self, key: str, result: AnalysisResult) -> None:
        if self.ttl_seconds <= 0:
            return
        with self._lock:
            self._items[key] = (time.monotonic(), result)
            self._items.move_to_end(key)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)
