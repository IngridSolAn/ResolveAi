"""Analisador sem IA (RESOLVEAI_LLM=offline, ou Claude sem chave configurada).

Permite subir o ambiente (GLPI + plugin + backend) e testar a integração antes
de configurar o modelo. Lista os casos recuperados, sem interpretá-los.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.models import AnalysisResult, ConfidenceLevel, SimilarCase, Ticket

NO_HISTORY = "Não encontrei histórico semelhante no material recuperado do GLPI."


class OfflineAnalyzer:
    def analyze(
        self, ticket: Ticket, similar_cases: Sequence[SimilarCase]
    ) -> AnalysisResult:
        if similar_cases:
            ids = ", ".join(f"#{case.id}" for case in similar_cases)
            diagnosis = (
                "Modo sem IA: chamados solucionados possivelmente relacionados "
                f"(busca semântica, sem verificação): {ids}."
            )
        else:
            diagnosis = NO_HISTORY

        return AnalysisResult(
            diagnostico_e_evidencias=diagnosis,
            nivel_de_confianca=ConfidenceLevel(
                percentual=0,
                justificativa=(
                    "Modo sem IA (RESOLVEAI_LLM=offline ou chave da IA ausente); "
                    "nenhuma análise foi gerada."
                ),
            ),
            passos_sugeridos_de_teste=[
                "Reúna logs e mensagens de erro do sistema afetado.",
                "Valide se o problema é reproduzido em outro usuário ou dispositivo.",
            ],
        )
