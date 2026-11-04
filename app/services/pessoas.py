"""Regras de negócio do cadastro de Pessoa.

Fica entre as rotas (HTTP) e o client (Pipefy): decide o que precisa ser
consultado ou validado antes de criar, mover ou apagar um card.
"""

import unicodedata
from datetime import datetime
from typing import Any

from app.clients.pipefy import PipefyClient, PipefyError
from app.core.config import Settings
from app.schemas.card import CardCriado, Fase
from app.schemas.pessoa import PessoaCreate


class CidadeNaoEncontradaError(Exception):
    """A cidade informada não existe na tabela de cidades do Pipefy.

    Guarda as opções válidas para a API poder mostrá-las na resposta de erro.
    """

    def __init__(self, nome: str, opcoes: list[str]) -> None:
        self.nome = nome
        self.opcoes = opcoes
        super().__init__(f"Cidade '{nome}' não encontrada.")


class CardNaoEncontradoError(Exception):
    """O card não existe ou não pertence ao pipe de Pessoas."""

    def __init__(self, card_id: int) -> None:
        self.card_id = card_id  # guardado para quem tratar o erro, se precisar
        super().__init__(f"Card {card_id} não encontrado no pipe de Pessoas.")


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

        # Compara sem acentos e maiúsculas: "eusebio" encontra "Eusébio".
        iguais = [c for c in cidades if normalizar(c["title"]) == normalizar(nome)]
        if not iguais:
            raise CidadeNaoEncontradaError(nome, [c["title"] for c in cidades])

        # A tabela tem duplicatas ("Fortaleza" e "fortaleza"): usamos o registro
        # mais antigo (menor ID), que é o original.
        original = min(iguais, key=lambda cidade: int(cidade["id"]))
        return original["id"]

    async def criar(self, pessoa: PessoaCreate) -> CardCriado:
        """Cadastra a Pessoa criando um card na primeira fase do pipe.

        Lança `CidadeNaoEncontradaError` se a cidade não existir.
        """
        cidade_id = await self.resolver_cidade(pessoa.cidade)
        campos = self._montar_campos(pessoa, cidade_id)

        card = await self._client.create_card(
            self._settings.pipefy_pipe_id, pessoa.nome, campos
        )

        # Traduz a resposta do Pipefy (inglês) para o nosso formato.
        return CardCriado(
            id=card["id"],
            titulo=card["title"],
            url=card["url"],
            fase=Fase(
                id=card["current_phase"]["id"], nome=card["current_phase"]["name"]
            ),
        )

    async def deletar(self, card_id: int) -> None:
        """Apaga o card da Pessoa, se ele for do nosso pipe.

        Lança `CardNaoEncontradoError` se o card não existir ou for de outro pipe.
        """
        await self._buscar_card(card_id)  # garante que o card é do nosso pipe
        await self._client.delete_card(card_id)  # só então apaga

    async def _buscar_card(self, card_id: int) -> dict[str, Any]:
        """Busca o card e confere se ele pertence ao pipe de Pessoas."""
        try:
            card = await self._client.get_card(card_id)
        except PipefyError as exc:
            # Para IDs inexistentes o Pipefy responde "Acesso negado".
            raise CardNaoEncontradoError(card_id) from exc

        # O pipe é compartilhado: nunca mexemos em cards de outro pipe.
        if card is None or card["pipe"]["id"] != str(self._settings.pipefy_pipe_id):
            raise CardNaoEncontradoError(card_id)
        return card

    @staticmethod
    def _montar_campos(pessoa: PessoaCreate, cidade_id: str) -> dict[str, Any]:
        """Converte a Pessoa nos campos do formulário do Pipefy (id -> valor)."""
        campos: dict[str, Any] = {
            "nome": pessoa.nome,
            "cidade": [cidade_id],  # connector: lista de IDs de registros
            "data": datetime.now().isoformat(timespec="seconds"),  # data de envio
        }

        # Campos opcionais só são enviados quando preenchidos.
        if pessoa.cpf:
            campos["cpf"] = pessoa.cpf
        if pessoa.data_de_nascimento:
            campos["data_de_nascimento"] = pessoa.data_de_nascimento.isoformat()
        if pessoa.telefone:
            campos["telefone"] = pessoa.telefone
        if pessoa.sexo:
            campos["sexo"] = pessoa.sexo.value
        if pessoa.hobbies:
            campos["hobbies"] = [hobby.value for hobby in pessoa.hobbies]

        return campos
