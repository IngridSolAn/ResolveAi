from fastapi import FastAPI
from pydantic import BaseModel


class TicketAnalysisRequest(BaseModel):
    ticket_id: int
    title: str
    description: str


app = FastAPI(
    title="ResolveAI",
    description="Assistente de investigação de chamados de TI.",
    version="0.1.0",
)


@app.get("/")
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "resolveai-backend"}


@app.post("/analyze")
def analyze_ticket(ticket: TicketAnalysisRequest) -> dict:
    evidence = ticket.description.strip() or ticket.title.strip()
    return {
        "diagnostico_e_evidencias": (
            "Análise inicial baseada nos dados fornecidos pelo chamado: "
            + evidence[:500]
            if evidence
            else "Nenhuma descrição disponível para análise."
        ),
        "nivel_de_confianca": {
            "percentual": 30,
            "justificativa": "Resultado inicial; integração com o modelo de IA ainda não foi configurada.",
        },
        "passos_sugeridos_de_teste": [
            "Reúna logs e mensagens de erro do sistema afetado.",
            "Valide se o problema é reproduzido em outro usuário ou dispositivo.",
        ],
    }
