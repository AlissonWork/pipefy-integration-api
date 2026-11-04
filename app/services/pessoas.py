"""Regras de negócio do cadastro de Pessoa.

Fica entre as rotas (HTTP) e o client (Pipefy): decide o que precisa ser
consultado ou validado antes de criar, mover ou apagar um card.
"""

import json
import unicodedata
from datetime import datetime
from typing import Any

from app.clients.pipefy import PipefyClient, PipefyError
from app.core.config import Settings
from app.schemas.card import CardCriado, CardDetalhe, CardMovido, CardResumo, Fase
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


class FaseNaoEncontradaError(Exception):
    """A fase de destino informada não existe no pipe."""

    def __init__(self, destino: str, opcoes: list[str]) -> None:
        self.destino = destino
        self.opcoes = opcoes  # nomes das fases válidas, para a resposta de erro
        super().__init__(f"Fase '{destino}' não encontrada.")


class MovimentacaoInvalidaError(Exception):
    """O card não pode ir para a fase pedida (ex.: já está na fase final)."""


def normalizar(texto: str) -> str:
    """Remove acentos e maiúsculas para comparar textos: 'Eusébio' -> 'eusebio'."""
    # NFKD separa a letra do acento ("é" -> "e" + "´"); o encode em ASCII
    # descarta o acento e o casefold deixa tudo minúsculo.
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.casefold().strip()


def converter_valor(valor: str | None) -> Any:
    """Checklist e connector chegam como texto JSON ('["Leitura"]'): vira lista."""
    if valor and valor.startswith("["):
        try:
            return json.loads(valor)  # '["Leitura"]' -> ["Leitura"]
        except json.JSONDecodeError:
            pass  # era só um texto começando com "[": devolve como veio
    return valor


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

    async def listar(self, fase: str | None = None) -> list[CardResumo]:
        """Lista os cards do pipe, do mais novo para o mais antigo.

        Se `fase` vier preenchida, filtra pelo nome da fase (sem acento/maiúscula).
        """
        cards = await self._client.list_cards(self._settings.pipefy_pipe_id)

        # Traduz cada card do Pipefy para o nosso formato resumido.
        resumos = [
            CardResumo(
                id=card["id"],
                titulo=card["title"],
                fase=Fase(
                    id=card["current_phase"]["id"], nome=card["current_phase"]["name"]
                ),
                criado_em=card["created_at"],
            )
            for card in cards
        ]

        # Filtro opcional: "concluido" encontra "Concluído".
        if fase:
            resumos = [
                r for r in resumos if normalizar(r.fase.nome) == normalizar(fase)
            ]

        # Mais novos primeiro: facilita achar o card que acabou de ser criado.
        return sorted(resumos, key=lambda r: r.criado_em, reverse=True)

    async def detalhar(self, card_id: int) -> CardDetalhe:
        """Retorna um card completo. Lança `CardNaoEncontradoError` se não for nosso."""
        card = await self._buscar_card(card_id)  # reaproveita a checagem do passo 5
        return CardDetalhe(
            id=card["id"],
            titulo=card["title"],
            url=card["url"],
            fase=Fase(
                id=card["current_phase"]["id"], nome=card["current_phase"]["name"]
            ),
            criado_em=card["created_at"],
            # Lista de {field, value} do Pipefy -> dicionário {"cpf": "...", ...}
            campos={
                c["field"]["id"]: converter_valor(c["value"]) for c in card["fields"]
            },
        )

    async def mover_fase(self, card_id: int, destino: str | None = None) -> CardMovido:
        """Move o card para a fase `destino` ou, sem destino, para a próxima fase.

        Lança `CardNaoEncontradoError`, `FaseNaoEncontradaError` ou
        `MovimentacaoInvalidaError` (card já está na fase final ou no destino).
        """
        card = await self._buscar_card(card_id)  # 404 se não for do nosso pipe
        atual = card["current_phase"]

        # As fases vêm do próprio pipe, na ordem do quadro (nada fixo no código).
        pipe = await self._client.get_pipe(self._settings.pipefy_pipe_id)
        fases = pipe["phases"]

        # Sem destino: próxima fase. Com destino: procura pelo nome ou ID.
        if destino is None:
            nova = self._proxima_fase(fases, atual)
        else:
            nova = self._encontrar_fase(fases, destino)

        if nova["id"] == atual["id"]:
            raise MovimentacaoInvalidaError(
                f"O card já está na fase '{atual['name']}'."
            )

        movido = await self._client.move_card(card_id, nova["id"])
        fase_atual = movido["current_phase"]
        finalizado = fase_atual["done"]  # done = fase final do pipe

        return CardMovido(
            id=card["id"],
            titulo=card["title"],
            fase_anterior=Fase(id=atual["id"], nome=atual["name"]),
            fase_atual=Fase(id=fase_atual["id"], nome=fase_atual["name"]),
            finalizado=finalizado,
            # Mensagem diferente quando chega no fim, como o desafio pede.
            mensagem=(
                f"O card chegou na fase final ({fase_atual['name']})."
                if finalizado
                else f"Card movido para a fase '{fase_atual['name']}'."
            ),
        )

    @staticmethod
    def _proxima_fase(
        fases: list[dict[str, Any]], atual: dict[str, Any]
    ) -> dict[str, Any]:
        """Retorna a fase seguinte à atual na ordem do pipe."""
        if atual["done"]:
            raise MovimentacaoInvalidaError(
                f"O card já está na fase final ('{atual['name']}')."
            )
        ids = [fase["id"] for fase in fases]
        posicao = ids.index(atual["id"])  # onde o card está na fila de fases
        if posicao + 1 >= len(fases):
            raise MovimentacaoInvalidaError("Não existe fase depois da atual.")
        return fases[posicao + 1]

    @staticmethod
    def _encontrar_fase(fases: list[dict[str, Any]], destino: str) -> dict[str, Any]:
        """Acha a fase pelo ID ou pelo nome (sem acento/maiúscula)."""
        for fase in fases:
            if fase["id"] == destino or normalizar(fase["name"]) == normalizar(destino):
                return fase
        raise FaseNaoEncontradaError(destino, [fase["name"] for fase in fases])

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
