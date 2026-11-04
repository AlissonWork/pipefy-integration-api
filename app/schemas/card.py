"""Schemas de resposta com os dados de um card do Pipefy."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Fase(BaseModel):
    """Fase (coluna) do pipe em que o card está."""

    id: str
    nome: str


class CardCriado(BaseModel):
    """Resposta do cadastro: identifica o card criado no Pipefy."""

    id: str  # usado depois para mover ou apagar o card
    titulo: str
    url: str  # link para abrir o card no Pipefy
    fase: Fase


class CardResumo(BaseModel):
    """Item da listagem: só o essencial, sem dados pessoais."""

    id: str
    titulo: str
    fase: Fase
    criado_em: datetime  # o Pydantic converte o texto ISO do Pipefy em data/hora


class CardDetalhe(BaseModel):
    """Um card completo, com os valores de todos os campos preenchidos."""

    id: str
    titulo: str
    url: str
    fase: Fase
    criado_em: datetime
    campos: dict[str, Any]  # id do campo -> valor (ex.: "cpf" -> "529...")


class MoverFase(BaseModel):
    """Corpo (opcional) do PATCH de fase.

    Sem `destino`, o card avança para a próxima fase do pipe.
    """

    # Nome ("Concluído", "fazendo") ou ID da fase de destino.
    destino: str | None = Field(default=None, examples=["Concluído"])


class CardMovido(BaseModel):
    """Resposta da mudança de fase."""

    id: str
    titulo: str
    fase_anterior: Fase
    fase_atual: Fase
    finalizado: bool  # True quando o card chegou na fase final do pipe
    mensagem: str  # explicação legível do que aconteceu
