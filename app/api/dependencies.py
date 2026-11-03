"""Dependências que o FastAPI injeta nas rotas (via Depends).

Cada rota declara do que precisa (ex.: o PessoaService) e o FastAPI monta
o objeto a cada requisição. Nos testes, dá para trocar qualquer peça.
"""

from typing import Annotated

from fastapi import Depends

from app.clients.pipefy import PipefyClient
from app.core.config import Settings, get_settings
from app.services.pessoas import PessoaService

SettingsDep = Annotated[Settings, Depends(get_settings)]


# Receita do client: precisa das Settings, que o FastAPI injeta sozinho.
def get_pipefy_client(settings: SettingsDep) -> PipefyClient:
    return PipefyClient(settings)


PipefyClientDep = Annotated[PipefyClient, Depends(get_pipefy_client)]


# Receita do service: depende do client, que depende das Settings.
def get_pessoa_service(client: PipefyClientDep, settings: SettingsDep) -> PessoaService:
    return PessoaService(client, settings)


PessoaServiceDep = Annotated[PessoaService, Depends(get_pessoa_service)]
