from fastapi import FastAPI

app = FastAPI(
    title="ResolveAI",
    description="Assistente de investigação de chamados de TI.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
