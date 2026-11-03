"""Ponto de entrada da API."""

from typing import Any

from fastapi import FastAPI

from app.clients.pipefy import PipefyClient
from app.core.config import get_settings

app = FastAPI(
    title="Pipefy Integration API",
    description="API de cadastro de Pessoas integrada ao Pipefy.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Verifica se a API está no ar."""
    return {"status": "ok"}


@app.get("/pipe", tags=["Pipe"])
async def get_pipe() -> dict[str, Any]:
    """Retorna a estrutura do pipe: fases e campos do cadastro de Pessoa."""
    settings = get_settings()
    client = PipefyClient(settings)
    return await client.get_pipe(settings.pipefy_pipe_id)
