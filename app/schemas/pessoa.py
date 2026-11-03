"""Schemas (modelos de dados) do cadastro de Pessoa.

Validam o formato do que chega na API antes de qualquer chamada ao Pipefy.
Regras que dependem de consultar o Pipefy (ex.: a cidade existe?) ficam
no service.
"""

import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Opções fixas do pipe: qualquer valor fora delas é rejeitado com erro 422.
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
    """Confere os dois dígitos verificadores de um CPF (só números)."""
    # Todos os dígitos iguais (111.111.111-11) passam na conta, mas são inválidos.
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False

    # 1º verificador: 9 primeiros dígitos com pesos de 10 a 2.
    # 2º verificador: 10 primeiros dígitos com pesos de 11 a 2.
    for tamanho in (9, 10):
        soma = sum(int(d) * (tamanho + 1 - i) for i, d in enumerate(digitos[:tamanho]))
        if (soma * 10 % 11) % 10 != int(digitos[tamanho]):
            return False
    return True


class PessoaCreate(BaseModel):
    """Dados para cadastrar uma Pessoa (vira um card no Pipefy).

    Campos sem valor padrão (nome, cidade) são obrigatórios.
    """

    # Remove espaços do começo e do fim de todo texto: "  Maria " -> "Maria".
    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str = Field(min_length=2, max_length=120, examples=["Maria Silva"])
    cidade: str = Field(min_length=2, examples=["Fortaleza"])
    cpf: str | None = Field(default=None, examples=["529.982.247-25"])
    data_de_nascimento: date | None = Field(default=None, examples=["1995-08-20"])
    telefone: str | None = Field(default=None, min_length=8, max_length=20)
    sexo: Sexo | None = None
    # default_factory cria uma lista nova a cada objeto (nunca use `= []`).
    hobbies: list[Hobby] = Field(default_factory=list)

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, valor: str | None) -> str | None:
        """Aceita com ou sem máscara e devolve sempre no formato 000.000.000-00."""
        if valor is None:
            return None
        digitos = re.sub(r"\D", "", valor)  # \D = tudo que não é dígito
        if not cpf_valido(digitos):
            raise ValueError("CPF inválido")
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"

    @field_validator("data_de_nascimento")
    @classmethod
    def validar_nascimento(cls, valor: date | None) -> date | None:
        """Impede datas de nascimento no futuro."""
        if valor and valor > date.today():
            raise ValueError("a data de nascimento não pode estar no futuro")
        return valor
