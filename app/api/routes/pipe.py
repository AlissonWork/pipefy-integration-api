"""Rotas de consulta à estrutura do pipe no Pipefy."""

from typing import Any

from fastapi import APIRouter

from app.api.dependencies import PessoaServiceDep, PipefyClientDep, SettingsDep

# Um "mini-app" com as rotas deste assunto; o main.py pluga ele no app.
# "tags" agrupa as rotas na mesma seção do Swagger.
router = APIRouter(tags=["Pipe"])


# O FastAPI injeta o client e as settings prontos (Depends), sem montar à mão.
@router.get("/pipe")
async def get_pipe(client: PipefyClientDep, settings: SettingsDep) -> dict[str, Any]:
    """Retorna a estrutura do pipe: fases e campos do cadastro de Pessoa."""
    return await client.get_pipe(settings.pipefy_pipe_id)


@router.get("/cidades")
async def listar_cidades(service: PessoaServiceDep) -> list[dict[str, Any]]:
    """Lista as cidades aceitas no cadastro de Pessoa."""
    return await service.listar_cidades()
