"""Regras de negócio do cadastro de Pessoa.

Fica entre as rotas (HTTP) e o client (Pipefy): decide o que precisa ser
consultado ou validado antes de criar, mover ou apagar um card.
"""

import unicodedata
from typing import Any

from app.clients.pipefy import PipefyClient
from app.core.config import Settings


class CidadeNaoEncontradaError(Exception):
    """A cidade informada não existe na tabela de cidades do Pipefy.

    Guarda as opções válidas para a API poder mostrá-las na resposta de erro.
    """

    def __init__(self, nome: str, opcoes: list[str]) -> None:
        self.nome = nome
        self.opcoes = opcoes
        super().__init__(f"Cidade '{nome}' não encontrada.")


def normalizar(texto: str) -> str:
    """Remove acentos e maiúsculas para comparar textos: 'Eusébio' -> 'eusebio'."""
    # NFKD separa a letra do acento ("é" -> "e" + "´"); o encode em ASCII
    # descarta o acento e o casefold deixa tudo minúsculo.
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.casefold().strip()


class PessoaService:
    """Operações do cadastro de Pessoa sobre o pipe do Pipefy."""

    def __init__(self, client: PipefyClient, settings: Settings) -> None:
        # O client chega pronto (injeção de dependência): nos testes dá para
        # trocar por um client falso que não chama o Pipefy de verdade.
        self._client = client
        self._settings = settings

    async def listar_cidades(self) -> list[dict[str, Any]]:
        """Lista as cidades cadastradas na tabela ligada ao campo Cidade."""
        return await self._client.list_table_records(
            self._settings.pipefy_cidade_table_id
        )

    async def resolver_cidade(self, nome: str) -> str:
        """Traduz o nome da cidade para o ID do registro que o Pipefy exige.

        Lança `CidadeNaoEncontradaError` se a cidade não existir na tabela.
        """
        cidades = await self.listar_cidades()

        # 1º: nome idêntico (a tabela tem "Fortaleza" e "fortaleza" duplicadas).
        for cidade in cidades:
            if cidade["title"] == nome:
                return cidade["id"]

        # 2º: ignorando acentos e maiúsculas ("eusebio" encontra "Eusébio").
        for cidade in cidades:
            if normalizar(cidade["title"]) == normalizar(nome):
                return cidade["id"]

        raise CidadeNaoEncontradaError(nome, [c["title"] for c in cidades])
