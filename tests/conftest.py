"""Peças compartilhadas pelos testes (fixtures do pytest).

Troca o Pipefy por um client falso em memória e as configurações por valores
fixos: os testes rodam sem internet, sem token e sem criar cards de verdade.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.dependencies import get_pipefy_client
from app.clients.pipefy import PipefyError
from app.core.config import Settings, get_settings
from app.main import app

PIPE_ID = 303843596

# Fases como o Pipefy devolve: na ordem do quadro, com "done" na fase final.
FASES = [
    {"id": "1", "name": "Caixa de entrada", "done": False},
    {"id": "2", "name": "Fazendo", "done": False},
    {"id": "3", "name": "Concluído", "done": True},
]

# Imita a tabela real, inclusive a duplicata "fortaleza" (ID maior).
CIDADES = [
    {"id": "10", "title": "Fortaleza"},
    {"id": "20", "title": "Eusébio"},
    {"id": "30", "title": "fortaleza"},
]


class ClienteFalso:
    """Imita o PipefyClient guardando os cards num dicionário em memória."""

    def __init__(self) -> None:
        self.cards: dict[str, dict[str, Any]] = {}  # id do card -> card
        self.campos_enviados: dict[str, Any] = {}  # campos do último card criado
        self._ultimo_id = 1000

    async def get_pipe(self, pipe_id: int) -> dict[str, Any]:
        return {"id": str(pipe_id), "name": "Pipe de teste", "phases": FASES}

    async def list_table_records(self, table_id: str) -> list[dict[str, Any]]:
        return CIDADES

    async def create_card(
        self, pipe_id: int, title: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        self._ultimo_id += 1  # gera um ID novo a cada card
        card_id = str(self._ultimo_id)
        self.campos_enviados = fields  # guardado para os testes conferirem
        self.cards[card_id] = {
            "id": card_id,
            "title": title,
            "url": f"https://app.pipefy.com/pipes/{pipe_id}#cards/{card_id}",
            "created_at": "2026-11-05T10:00:00Z",
            "pipe": {"id": str(pipe_id)},
            "current_phase": FASES[0],  # todo card nasce na primeira fase
            "fields": [],
        }
        return self.cards[card_id]

    async def get_card(self, card_id: int) -> dict[str, Any]:
        # Igual ao Pipefy real: ID inexistente responde "Acesso negado".
        if str(card_id) not in self.cards:
            raise PipefyError("Acesso negado")
        return self.cards[str(card_id)]

    async def list_cards(self, pipe_id: int) -> list[dict[str, Any]]:
        return list(self.cards.values())

    async def move_card(self, card_id: int, phase_id: str) -> dict[str, Any]:
        card = self.cards[str(card_id)]
        card["current_phase"] = next(f for f in FASES if f["id"] == phase_id)
        return card

    async def delete_card(self, card_id: int) -> None:
        del self.cards[str(card_id)]


@pytest.fixture
def pipefy() -> ClienteFalso:
    """Um Pipefy falso novo (vazio) para cada teste."""
    return ClienteFalso()


@pytest.fixture
def client(pipefy: ClienteFalso) -> Iterator[TestClient]:
    """Cliente HTTP da API com o Pipefy e as configurações trocados."""
    # "Quando uma rota pedir o client ou as settings, entregue estes aqui."
    app.dependency_overrides[get_pipefy_client] = lambda: pipefy
    app.dependency_overrides[get_settings] = lambda: Settings(
        pipefy_token=SecretStr("token-falso"),
        pipefy_pipe_id=PIPE_ID,
        pipefy_cidade_table_id="tabela-falsa",
    )
    yield TestClient(app)  # o teste roda aqui
    app.dependency_overrides.clear()  # depois do teste, desfaz as trocas
