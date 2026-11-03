"""Configurações da aplicação.

Os valores vêm das variáveis de ambiente ou do arquivo .env (fora do Git),
para que segredos como o token do Pipefy nunca fiquem escritos no código.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cada atributo é preenchido pela variável de ambiente de mesmo nome.

    Ex.: `pipefy_token` <- `PIPEFY_TOKEN`. Se um campo obrigatório faltar ou
    vier no tipo errado, a aplicação nem sobe (fail fast).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Obrigatórios (sem valor padrão): precisam estar no .env.
    pipefy_token: SecretStr  # SecretStr esconde o valor em prints e logs
    pipefy_pipe_id: int
    pipefy_cidade_table_id: str  # tabela ligada ao campo "Cidade" do pipe

    # Opcionais: só vão no .env se precisarem mudar.
    pipefy_api_url: str = "https://api.pipefy.com/graphql"
    pipefy_timeout: float = 10.0  # segundos esperando o Pipefy responder


@lru_cache
def get_settings() -> Settings:
    """Retorna as configurações, lendo o .env só na primeira chamada.

    Ser uma função (e não uma variável global) facilita trocar os valores
    nos testes.
    """
    # O Pylance não sabe que o Pydantic preenche os campos pelo .env.
    return Settings()  # pyright: ignore[reportCallIssue]
