"""Configuração lida das variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


LLM_PROVIDERS = ("ollama", "claude", "offline")


@dataclass(frozen=True)
class Settings:
    # Qual IA gera o diagnóstico: "ollama" (gratuita, local), "claude" (paga,
    # API da Anthropic) ou "offline" (sem IA, só lista casos parecidos).
    llm_provider: str = field(
        default_factory=lambda: _env("RESOLVEAI_LLM", "ollama").lower()
    )

    ollama_host: str = field(
        default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: _env("OLLAMA_MODEL", "qwen2.5:7b")
    )
    ollama_timeout: float = field(
        default_factory=lambda: float(_env("OLLAMA_TIMEOUT_SECONDS", "300"))
    )

    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    claude_model: str = field(
        default_factory=lambda: _env("CLAUDE_MODEL", "claude-opus-5-5")
    )
    claude_effort: str = field(
        default_factory=lambda: _env("CLAUDE_EFFORT", "medium")
    )
    api_token: str = field(default_factory=lambda: _env("RESOLVEAI_API_TOKEN"))
    # Token do painel de administradores (separado do token do plugin). Sem
    # ele, o painel fica desativado.
    admin_token: str = field(default_factory=lambda: _env("RESOLVEAI_ADMIN_TOKEN"))
    telemetry_db_path: str = field(
        default_factory=lambda: _env("TELEMETRY_DB_PATH", "data/telemetry.db")
    )
    rag_enabled: bool = field(
        default_factory=lambda: _env("RESOLVEAI_RAG_ENABLED", "true").lower()
        in {"1", "true", "yes"}
    )
    # Por quanto tempo (segundos) uma análise é reaproveitada; 0 desativa.
    analysis_cache_ttl: float = field(
        default_factory=lambda: float(_env("ANALYSIS_CACHE_TTL_SECONDS", "86400"))
    )
    rag_limit: int = field(default_factory=lambda: int(_env("RAG_LIMIT", "5")))
    # Distância de cosseno máxima (0 = idêntico, 2 = oposto) para um caso ser
    # enviado à IA. Vazio desativa o filtro.
    rag_max_distance: float | None = field(
        default_factory=lambda: (
            float(_env("RAG_MAX_DISTANCE", "0.5"))
            if _env("RAG_MAX_DISTANCE", "0.5")
            else None
        )
    )
    chroma_host: str = field(default_factory=lambda: _env("CHROMADB_HOST"))
    chroma_port: int = field(
        default_factory=lambda: int(_env("CHROMADB_PORT", "8000"))
    )
    chroma_path: str = field(
        default_factory=lambda: _env("CHROMA_PATH", "data/chroma")
    )
    chroma_collection: str = field(
        default_factory=lambda: _env("CHROMA_COLLECTION", "resolveai_tickets")
    )
