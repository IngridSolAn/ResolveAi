"""Modelos neutros do núcleo do ResolveAI.

Nada aqui conhece GLPI, Zammad, Jira etc. Cada conector traduz os dados da
sua plataforma para estes modelos, e o núcleo trabalha só com eles.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Ticket(BaseModel):
    """Chamado em análise, vindo de qualquer plataforma de ITSM."""

    id: str = Field(min_length=1)
    title: str = ""
    description: str = ""
    # Escopo de isolamento dos dados (entidade no GLPI, organização no Zammad,
    # projeto no Jira...). A busca de casos parecidos nunca sai deste escopo;
    # sem ele, a análise é feita sem histórico.
    tenant_id: str | None = None


class ResolvedTicket(BaseModel):
    """Chamado já solucionado, usado como conhecimento para o RAG."""

    source: str = Field(min_length=1)  # ex.: "glpi"
    id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    title: str = ""
    description: str = ""
    solutions: list[str] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)
    updated_at: str  # "AAAA-MM-DD HH:MM:SS" em UTC

    def to_document(self) -> str:
        sections = [
            f"Chamado: {self.title}",
            f"Descrição: {self.description}",
            "Solução: " + "\n".join(self.solutions),
        ]
        if self.followups:
            sections.append("Acompanhamentos: " + "\n".join(self.followups))
        return "\n\n".join(sections)


class SimilarCase(BaseModel):
    """Caso recuperado da base de conhecimento."""

    id: str
    source: str
    content: str
    distance: float | None = None


class ConfidenceLevel(BaseModel):
    percentual: int = Field(ge=0, le=100)
    justificativa: str = Field(min_length=1)


class AnalysisResult(BaseModel):
    """Contrato de resposta do /analyze, consumido pelo plugin do GLPI."""

    diagnostico_e_evidencias: str = Field(min_length=1)
    nivel_de_confianca: ConfidenceLevel
    passos_sugeridos_de_teste: list[str]
