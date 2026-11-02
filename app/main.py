from fastapi import FastAPI

app = FastAPI(
    title="Pipefy Integration API",
    description="API de cadastro de Pessoas integrada ao Pipefy.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Verifica se a API está no ar."""
    return {"status": "ok"}
