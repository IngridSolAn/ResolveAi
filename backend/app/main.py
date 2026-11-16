"""API HTTP do ResolveAI.

Esta camada só traduz HTTP <-> modelos neutros e monta as dependências. A
lógica fica em `app.core`; conectores e adaptadores ficam fora do núcleo.
"""

from __future__ import annotations

import hmac
import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import LLM_PROVIDERS, Settings
from app.core.cache import AnalysisCache
from app.core.models import AnalysisResult, Ticket
from app.core.ports import Analyzer, KnowledgeBase
from app.core.service import analyze_ticket

LOGGER = logging.getLogger("resolveai.api")


class TicketAnalysisRequest(BaseModel):
    ticket_id: int | str
    title: str = Field(default="", max_length=1000)
    description: str = Field(default="", max_length=50000)
    # Escopo de isolamento (no GLPI, o entities_id do chamado). Sem ele, a
    # análise é feita sem consultar o histórico.
    tenant_id: int | str | None = None
    # Ignora o cache e gera uma nova análise ("Analisar novamente").
    refresh: bool = False


app = FastAPI(
    title="ResolveAI",
    description="Assistente de investigação de chamados de TI.",
    version="0.2.0",
)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_analysis_cache() -> AnalysisCache:
    return AnalysisCache(ttl_seconds=get_settings().analysis_cache_ttl)


def build_analyzer(settings: Settings) -> Analyzer:
    """Escolhe a IA pelo RESOLVEAI_LLM: ollama (padrão), claude ou offline."""
    from app.llm.offline import OfflineAnalyzer

    provider = settings.llm_provider
    if provider not in LLM_PROVIDERS:
        raise ValueError(
            f"RESOLVEAI_LLM inválido: {provider!r}. Use: {', '.join(LLM_PROVIDERS)}."
        )

    if provider == "ollama":
        from app.llm.ollama import OllamaAnalyzer

        return OllamaAnalyzer(
            host=settings.ollama_host,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
        )

    if provider == "claude":
        if not settings.anthropic_api_key:
            LOGGER.warning(
                "RESOLVEAI_LLM=claude, mas ANTHROPIC_API_KEY não foi definida: "
                "usando o modo sem IA."
            )
            return OfflineAnalyzer()
        from app.llm.claude import ClaudeAnalyzer

        return ClaudeAnalyzer(
            model=settings.claude_model, effort=settings.claude_effort
        )

    return OfflineAnalyzer()


@lru_cache
def get_analyzer() -> Analyzer:
    return build_analyzer(get_settings())


@lru_cache
def get_knowledge_base() -> KnowledgeBase | None:
    settings = get_settings()
    if not settings.rag_enabled:
        return None
    try:
        from app.knowledge.chroma import ChromaKnowledgeBase, create_collection

        collection = create_collection(
            host=settings.chroma_host or None,
            port=settings.chroma_port,
            path=settings.chroma_path,
            name=settings.chroma_collection,
        )
    except Exception:
        LOGGER.exception("ChromaDB indisponível: análises seguirão sem histórico.")
        get_knowledge_base.cache_clear()  # tenta de novo na próxima requisição
        return None
    return ChromaKnowledgeBase(collection)


def require_token(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Exige `Authorization: Bearer <RESOLVEAI_API_TOKEN>` quando o token está definido."""
    if not settings.api_token:
        return
    expected = f"Bearer {settings.api_token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token.")


@app.get("/")
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "resolveai-backend"}


@app.post(
    "/analyze",
    response_model=AnalysisResult,
    dependencies=[Depends(require_token)],
)
def analyze(
    request: TicketAnalysisRequest,
    analyzer: Annotated[Analyzer, Depends(get_analyzer)],
    knowledge_base: Annotated[KnowledgeBase | None, Depends(get_knowledge_base)],
    settings: Annotated[Settings, Depends(get_settings)],
    cache: Annotated[AnalysisCache, Depends(get_analysis_cache)],
) -> AnalysisResult:
    ticket = Ticket(
        id=str(request.ticket_id),
        title=request.title.strip(),
        description=request.description.strip(),
        tenant_id=None if request.tenant_id is None else str(request.tenant_id),
    )
    cache_key = AnalysisCache.key(ticket, namespace=type(analyzer).__name__)
    if not request.refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    try:
        result = analyze_ticket(
            ticket,
            knowledge_base,
            analyzer,
            limit=settings.rag_limit,
            max_distance=settings.rag_max_distance,
        )
    except Exception as error:
        LOGGER.exception("Falha ao analisar o chamado %s.", ticket.id)
        raise HTTPException(
            status_code=502, detail="Não foi possível gerar a análise do chamado."
        ) from error
    cache.set(cache_key, result)
    return result
