"""Rotas do cadastro de Pessoa (cards no Pipefy)."""

from fastapi import APIRouter, status

from app.api.dependencies import PessoaServiceDep
from app.schemas.card import CardCriado, CardDetalhe, CardResumo
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


# Parâmetro fora da URL ({...}) e de tipo simples = query string: /pessoas?fase=Fazendo
@router.get("")
async def listar_pessoas(
    service: PessoaServiceDep,
    fase: str | None = None,  # opcional: sem ele, lista todos
) -> list[CardResumo]:
    """Lista os cards do pipe (resumo). Filtro opcional pelo nome da fase."""
    return await service.listar(fase)


# {card_id} vem da URL: GET /pessoas/123
@router.get("/{card_id}")
async def detalhar_pessoa(card_id: int, service: PessoaServiceDep) -> CardDetalhe:
    """Retorna um card completo, com todos os campos preenchidos."""
    return await service.detalhar(card_id)
