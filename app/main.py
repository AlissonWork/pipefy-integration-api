"""Ponto de entrada da API: cria a aplicação FastAPI e registra as rotas."""

from typing import Any

from fastapi import FastAPI

from app.clients.pipefy import PipefyClient
from app.core.config import get_settings
from app.services.pessoas import PessoaService

# Título, descrição e versão aparecem na documentação automática (/docs).
app = FastAPI(
    title="Pipefy Integration API",
    description="API de cadastro de Pessoas integrada ao Pipefy.",
    version="0.1.0",
)


# O decorator registra a função como a rota "GET /health" do app.
@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Verifica se a API está no ar."""
    return {"status": "ok"}


@app.get("/pipe", tags=["Pipe"])
async def get_pipe() -> dict[str, Any]:
    """Retorna a estrutura do pipe: fases e campos do cadastro de Pessoa."""
    settings = get_settings()
    client = PipefyClient(settings)
    # `await` pausa a rota até o Pipefy responder; enquanto isso a API
    # continua livre para atender outras requisições.
    return await client.get_pipe(settings.pipefy_pipe_id)


@app.get("/cidades", tags=["Cidades"])
async def listar_cidades() -> list[dict[str, Any]]:
    """Lista as cidades aceitas no cadastro de Pessoa."""
    settings = get_settings()
    service = PessoaService(PipefyClient(settings), settings)
    return await service.listar_cidades()
