"""Configurações da aplicação, lidas do ambiente e do arquivo .env."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cada atributo é preenchido pela variável de ambiente de mesmo nome."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    pipefy_token: SecretStr  # esconde o valor em prints e logs
    pipefy_pipe_id: int
    pipefy_api_url: str = "https://api.pipefy.com/graphql"
    pipefy_timeout: float = 10.0  # segundos


@lru_cache
def get_settings() -> Settings:
    """Retorna as configurações, carregadas uma única vez."""
    return Settings()  # pyright: ignore[reportCallIssue]
