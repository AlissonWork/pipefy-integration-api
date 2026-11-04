"""Client da API GraphQL do Pipefy.

O Pipefy tem um único endereço (/graphql) que recebe sempre um POST com a
consulta no corpo. Este módulo concentra essa comunicação: o resto da
aplicação não precisa saber de HTTP, token ou formato GraphQL.
"""

from typing import Any

import httpx

from app.core.config import Settings


class PipefyError(Exception):
    """Erro devolvido pelo Pipefy na chave "errors" da resposta."""


class PipefyClient:
    """Concentra toda a comunicação com o Pipefy.

    O `execute` cuida do "como" (HTTP, token, erros); os demais métodos
    cuidam do "o quê" perguntar e reaproveitam o `execute`.
    """

    def __init__(self, settings: Settings) -> None:
        self._url = settings.pipefy_api_url
        self._timeout = settings.pipefy_timeout
        # Único ponto em que o token sai do SecretStr: no cabeçalho da requisição.
        self._headers = {
            "Authorization": f"Bearer {settings.pipefy_token.get_secret_value()}",
        }

    async def execute(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Envia uma query ou mutation e retorna o campo "data" da resposta.

        Lança `httpx.HTTPStatusError` para status de erro (ex.: 401, token
        inválido) e `PipefyError` quando o Pipefy devolve "errors".
        """
        # O `async with` fecha a conexão no fim, mesmo se der erro no meio.
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self._url,
                json={"query": query, "variables": variables or {}},
                headers=self._headers,
            )

        response.raise_for_status()
        body = response.json()

        # O GraphQL responde 200 mesmo com erro: a falha vem na chave "errors".
        if body.get("errors"):
            raise PipefyError(body["errors"][0]["message"])

        return body["data"]

    async def get_pipe(self, pipe_id: int) -> dict[str, Any]:
        """Busca o nome, as fases e os campos do formulário inicial do pipe."""
        # Variáveis ($pipeId) em vez de colar o ID no texto: evita injection
        # e o Pipefy valida o tipo.
        query = """
        query ($pipeId: ID!) {
          pipe(id: $pipeId) {
            id
            name
            phases { id name done }
            start_form_fields { id label type required options }
          }
        }
        """
        data = await self.execute(query, {"pipeId": pipe_id})
        return data["pipe"]

    async def list_table_records(self, table_id: str) -> list[dict[str, Any]]:
        """Lista os registros (id e título) de uma tabela do Pipefy."""
        # A lista vem "embrulhada" em edges/node (padrão de paginação do
        # GraphQL); `first: 100` pede até 100 registros.
        query = """
        query ($tableId: ID!) {
          table_records(table_id: $tableId, first: 100) {
            edges { node { id title } }
          }
        }
        """
        data = await self.execute(query, {"tableId": table_id})
        # Desembrulha: [{"node": {...}}, ...] -> [{...}, ...]
        return [edge["node"] for edge in data["table_records"]["edges"]]

    async def create_card(
        self, pipe_id: int, title: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Cria um card no pipe. `fields` mapeia o id do campo ao seu valor."""
        mutation = """
        mutation ($input: CreateCardInput!) {
          createCard(input: $input) {
            card { id title url current_phase { id name } }
          }
        }
        """
        # O Pipefy espera os campos como uma lista de pares field_id/field_value.
        variables = {
            "input": {
                "pipe_id": pipe_id,
                "title": title,
                "fields_attributes": [
                    {"field_id": campo, "field_value": valor}
                    for campo, valor in fields.items()
                ],
            }
        }
        data = await self.execute(mutation, variables)
        return data["createCard"]["card"]

    async def get_card(self, card_id: int) -> dict[str, Any]:
        """Busca um card com pipe, fase atual e valores dos campos."""
        # O pipe serve para conferir se o card é nosso; a fase e os campos
        # alimentam a consulta e o passo 6 (avançar fase).
        query = """
        query ($cardId: ID!) {
          card(id: $cardId) {
            id
            title
            url
            created_at
            pipe { id }
            current_phase { id name done }
            fields { field { id } value }
          }
        }
        """
        data = await self.execute(query, {"cardId": card_id})
        return data["card"]

    async def delete_card(self, card_id: int) -> None:
        """Apaga um card definitivamente."""
        # Mutation de escrita; se falhar, o execute() já lança o erro.
        mutation = """
        mutation ($cardId: ID!) {
          deleteCard(input: { id: $cardId }) { success }
        }
        """
        await self.execute(mutation, {"cardId": card_id})

    async def list_cards(self, pipe_id: int) -> list[dict[str, Any]]:
        """Lista todos os cards do pipe (id, título, fase e data de criação)."""
        query = """
        query ($pipeId: ID!, $after: String) {
          allCards(pipeId: $pipeId, first: 50, after: $after) {
            pageInfo { hasNextPage endCursor }
            edges { node { id title created_at current_phase { id name } } }
          }
        }
        """
        cards: list[dict[str, Any]] = []
        after = None  # cursor: "continue a partir daqui"; None = do começo

        # O Pipefy devolve no máximo 50 por vez: pedimos página por página.
        while True:
            data = await self.execute(query, {"pipeId": pipe_id, "after": after})
            pagina = data["allCards"]
            cards += [edge["node"] for edge in pagina["edges"]]  # junta esta página
            if not pagina["pageInfo"]["hasNextPage"]:
                return cards  # acabou: devolve tudo que juntou
            after = pagina["pageInfo"]["endCursor"]  # marcador para a próxima
