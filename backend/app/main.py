"""API HTTP do ResolveAI.

Esta camada só traduz HTTP <-> modelos neutros e monta as dependências. A
lógica fica em `app.core`; conectores e adaptadores ficam fora do núcleo.
"""

from __future__ import annotations

import hmac
import logging
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import LLM_PROVIDERS, Settings
from app.core.cache import AnalysisCache
from app.core.models import AnalysisResult, Ticket
from app.core.ports import Analyzer, KnowledgeBase
from app.core.service import AnalysisOutcome, run_analysis
from app.core.telemetry import AnalysisEvent, TelemetryStore

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


class AnalyzeResponse(AnalysisResult):
    # Identifica esta análise para a avaliação (👍/👎) do analista.
    analysis_id: str


class FeedbackRequest(BaseModel):
    analysis_id: str = Field(min_length=1, max_length=64)
    helpful: bool
    comment: str | None = Field(default=None, max_length=1000)


app = FastAPI(
    title="ResolveAI",
    description="Assistente de investigação de chamados de TI.",
    version="0.3.0",
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


@lru_cache
def get_telemetry() -> TelemetryStore:
    from app.telemetry.sqlite import SQLiteTelemetryStore

    return SQLiteTelemetryStore(get_settings().telemetry_db_path)


def _bearer_matches(authorization: str | None, token: str) -> bool:
    return bool(authorization) and hmac.compare_digest(
        authorization.encode("utf-8"), f"Bearer {token}".encode("utf-8")
    )


def require_token(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Exige `Authorization: Bearer <RESOLVEAI_API_TOKEN>` quando o token está definido."""
    if not settings.api_token:
        return
    if not _bearer_matches(authorization, settings.api_token):
        raise HTTPException(status_code=401, detail="Invalid or missing API token.")


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Telemetria só para o Painel da IA: exige o RESOLVEAI_ADMIN_TOKEN.

    É um token separado do usado pelo plugin para analisar chamados; sem ele,
    os endpoints /admin/* ficam desativados.
    """
    if not settings.admin_token:
        raise HTTPException(
            status_code=403,
            detail="Painel desativado: defina RESOLVEAI_ADMIN_TOKEN no backend.",
        )
    if not _bearer_matches(authorization, settings.admin_token):
        raise HTTPException(status_code=401, detail="Token de administrador inválido.")


def _record(telemetry: TelemetryStore, event: AnalysisEvent) -> None:
    # A telemetria nunca pode derrubar a análise.
    try:
        telemetry.record(event)
    except Exception:
        LOGGER.exception("Falha ao registrar a telemetria da análise.")


@app.get("/")
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "resolveai-backend"}


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    dependencies=[Depends(require_token)],
)
def analyze(
    request: TicketAnalysisRequest,
    analyzer: Annotated[Analyzer, Depends(get_analyzer)],
    knowledge_base: Annotated[KnowledgeBase | None, Depends(get_knowledge_base)],
    settings: Annotated[Settings, Depends(get_settings)],
    cache: Annotated[AnalysisCache, Depends(get_analysis_cache)],
    telemetry: Annotated[TelemetryStore, Depends(get_telemetry)],
) -> AnalyzeResponse:
    ticket = Ticket(
        id=str(request.ticket_id),
        title=request.title.strip(),
        description=request.description.strip(),
        tenant_id=None if request.tenant_id is None else str(request.tenant_id),
    )
    analysis_id = uuid.uuid4().hex
    base_event = {
        "id": analysis_id,
        "created_at": datetime.now(timezone.utc),
        "ticket_id": ticket.id,
        "tenant_id": ticket.tenant_id,
        "provider": getattr(analyzer, "provider", type(analyzer).__name__),
        "model": getattr(analyzer, "model", None),
    }
    started = time.perf_counter()

    cache_key = AnalysisCache.key(ticket, namespace=type(analyzer).__name__)
    outcome: AnalysisOutcome | None = None
    cache_hit = False
    if not request.refresh:
        outcome = cache.get(cache_key)
        cache_hit = outcome is not None

    if outcome is None:
        try:
            outcome = run_analysis(
                ticket,
                knowledge_base,
                analyzer,
                limit=settings.rag_limit,
                max_distance=settings.rag_max_distance,
            )
        except Exception as error:
            LOGGER.exception("Falha ao analisar o chamado %s.", ticket.id)
            _record(
                telemetry,
                AnalysisEvent(
                    **base_event,
                    status="error",
                    error_type=type(error).__name__,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                ),
            )
            raise HTTPException(
                status_code=502, detail="Não foi possível gerar a análise do chamado."
            ) from error
        cache.set(cache_key, outcome)

    _record(
        telemetry,
        AnalysisEvent(
            **base_event,
            status="ok",
            cache_hit=cache_hit,
            duration_ms=int((time.perf_counter() - started) * 1000),
            cases_retrieved=len(outcome.retrieved),
            cases_used=len(outcome.used),
            cases_cited=len(outcome.cited),
            best_distance=outcome.best_distance,
            confidence=outcome.result.nivel_de_confianca.percentual,
        ),
    )
    return AnalyzeResponse(**outcome.result.model_dump(), analysis_id=analysis_id)


@app.post("/feedback", status_code=204, dependencies=[Depends(require_token)])
def feedback(
    request: FeedbackRequest,
    telemetry: Annotated[TelemetryStore, Depends(get_telemetry)],
) -> None:
    comment = request.comment.strip() if request.comment else None
    if not telemetry.add_feedback(request.analysis_id, request.helpful, comment or None):
        raise HTTPException(status_code=404, detail="Análise não encontrada.")


# --- Telemetria para o Painel da IA ---------------------------------------
# O painel em si fica no GLPI (Ferramentas > Painel da IA, só Super-Admin),
# que chama estes endpoints servidor a servidor com o RESOLVEAI_ADMIN_TOKEN.


@app.get("/admin/metrics", dependencies=[Depends(require_admin)])
def admin_metrics(
    telemetry: Annotated[TelemetryStore, Depends(get_telemetry)],
    settings: Annotated[Settings, Depends(get_settings)],
    analyzer: Annotated[Analyzer, Depends(get_analyzer)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> dict:
    summary = telemetry.summary(days)
    summary["config"] = {
        "provider": getattr(analyzer, "provider", type(analyzer).__name__),
        "model": getattr(analyzer, "model", None),
        "rag_enabled": settings.rag_enabled,
        "rag_limit": settings.rag_limit,
        "rag_max_distance": settings.rag_max_distance,
        "cache_ttl_seconds": settings.analysis_cache_ttl,
    }
    return summary


@app.get("/admin/analyses", dependencies=[Depends(require_admin)])
def admin_analyses(
    telemetry: Annotated[TelemetryStore, Depends(get_telemetry)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[dict]:
    return telemetry.recent(limit)
