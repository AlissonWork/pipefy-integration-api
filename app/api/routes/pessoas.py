"""Rotas do cadastro de Pessoa (cards no Pipefy)."""

from fastapi import APIRouter, status

from app.api.dependencies import PessoaServiceDep
from app.schemas.card import CardCriado
from app.schemas.pessoa import PessoaCreate

# Todas as rotas deste arquivo começam com /pessoas.
router = APIRouter(prefix="/pessoas", tags=["Pessoas"])


# prefix "/pessoas" + "" = POST /pessoas. 201 = "recurso criado".
@router.post("", status_code=status.HTTP_201_CREATED)
async def criar_pessoa(
    pessoa: PessoaCreate,  # o corpo JSON, já validado pelo schema (senão: 422)
    service: PessoaServiceDep,  # injetado pelo FastAPI
) -> CardCriado:  # o formato da resposta, validado e documentado no Swagger
    """Cadastra uma Pessoa criando um card na primeira fase do pipe."""
    return await service.criar(pessoa)


# {card_id} na URL vira o parâmetro card_id; int faz o FastAPI rejeitar "abc" (422).
# 204 = "deu certo e não há conteúdo para devolver".
@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_pessoa(card_id: int, service: PessoaServiceDep) -> None:
    """Apaga o card da Pessoa. Só aceita cards do pipe de Pessoas."""
    await service.deletar(card_id)
