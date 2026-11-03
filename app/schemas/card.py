"""Schemas de resposta com os dados de um card do Pipefy."""

from pydantic import BaseModel


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
