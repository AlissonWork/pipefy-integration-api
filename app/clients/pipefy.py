"""Client da API GraphQL do Pipefy."""

from typing import Any

import httpx

from app.core.config import Settings


class PipefyError(Exception):
    """Erro retornado pela API do Pipefy."""


class PipefyClient:
    """Concentra toda a comunicação com o Pipefy."""

    def __init__(self, settings: Settings) -> None:
        self._url = settings.pipefy_api_url
        self._timeout = settings.pipefy_timeout
        self._headers = {
            "Authorization": f"Bearer {settings.pipefy_token.get_secret_value()}",
        }

    async def execute(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Envia uma query ou mutation e retorna o campo "data" da resposta."""
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
