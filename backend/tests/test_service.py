from collections.abc import Sequence

from app.core.models import AnalysisResult, SimilarCase, Ticket
from app.core.service import analyze_ticket
from app.llm.offline import OfflineAnalyzer


class StaticKnowledgeBase:
    def upsert(self, tickets: object) -> None: ...

    def search(self, query: str, tenant_id: str, limit: int) -> list[SimilarCase]:
        return [
            SimilarCase(id="1", source="glpi", content="Wi-Fi", distance=0.31),
            SimilarCase(id="6", source="glpi", content="Sinal", distance=0.44),
            SimilarCase(id="3", source="glpi", content="ERP", distance=0.56),
        ]


class CaptureAnalyzer(OfflineAnalyzer):
    def __init__(self) -> None:
        self.cases: list[SimilarCase] = []

    def analyze(
        self, ticket: Ticket, similar_cases: Sequence[SimilarCase]
    ) -> AnalysisResult:
        self.cases = list(similar_cases)
        return super().analyze(ticket, similar_cases)


def test_max_distance_drops_unrelated_cases() -> None:
    analyzer = CaptureAnalyzer()
    ticket = Ticket(id="7", title="Coletor cai do Wi-Fi", tenant_id="0")

    analyze_ticket(ticket, StaticKnowledgeBase(), analyzer, max_distance=0.5)

    assert [case.id for case in analyzer.cases] == ["1", "6"]


def test_without_max_distance_keeps_all_cases() -> None:
    analyzer = CaptureAnalyzer()
    ticket = Ticket(id="7", title="Coletor cai do Wi-Fi", tenant_id="0")

    analyze_ticket(ticket, StaticKnowledgeBase(), analyzer)

    assert len(analyzer.cases) == 3
