"""Schemas do cadastro de Pessoa."""

import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Sexo(StrEnum):
    MASCULINO = "Masculino"
    FEMININO = "Feminino"
    PREFERE_NAO_RESPONDER = "Prefere não responder"


class Hobby(StrEnum):
    TEATRO = "Teatro"
    MUSICA = "Música"
    CINEMA = "Cinema"
    ESPORTES = "Esportes"
    LEITURA = "Leitura"
    VIAGEM = "Viagem"
    ARTES = "Artes"


def cpf_valido(digitos: str) -> bool:
    """Confere os dois dígitos verificadores do CPF."""
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d) * (tamanho + 1 - i) for i, d in enumerate(digitos[:tamanho]))
        if (soma * 10 % 11) % 10 != int(digitos[tamanho]):
            return False
    return True


class PessoaCreate(BaseModel):
    """Dados para cadastrar uma Pessoa (vira um card no Pipefy)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str = Field(min_length=2, max_length=120, examples=["Maria Silva"])
    cidade: str = Field(min_length=2, examples=["Fortaleza"])
    cpf: str | None = Field(default=None, examples=["529.982.247-25"])
    data_de_nascimento: date | None = Field(default=None, examples=["1995-08-20"])
    telefone: str | None = Field(default=None, min_length=8, max_length=20)
    sexo: Sexo | None = None
    hobbies: list[Hobby] = Field(default_factory=list)

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, valor: str | None) -> str | None:
        """Aceita com ou sem máscara e devolve sempre no formato 000.000.000-00."""
        if valor is None:
            return None
        digitos = re.sub(r"\D", "", valor)
        if not cpf_valido(digitos):
            raise ValueError("CPF inválido")
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"

    @field_validator("data_de_nascimento")
    @classmethod
    def validar_nascimento(cls, valor: date | None) -> date | None:
        if valor and valor > date.today():
            raise ValueError("a data de nascimento não pode estar no futuro")
        return valor
