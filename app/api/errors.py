"""Tradução das exceções da aplicação em respostas HTTP.

Assim as rotas e o service só lançam erros; quem decide o status e a
mensagem devolvida ao cliente é este módulo, num lugar só.
"""

import httpx
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.clients.pipefy import PipefyError
from app.services.pessoas import (
    CardNaoEncontradoError,
    CidadeNaoEncontradaError,
    FaseNaoEncontradaError,
    MovimentacaoInvalidaError,
)


def registrar_handlers(app: FastAPI) -> None:
    """Registra no app o tratamento de cada tipo de erro."""

    # "Quando alguma rota lançar CidadeNaoEncontradaError, chame esta função."
    # 422: o erro é de quem chamou a API (mandou uma cidade que não existe).
    @app.exception_handler(CidadeNaoEncontradaError)
    async def cidade_nao_encontrada(
        _: Request,
        exc: CidadeNaoEncontradaError,  # "_" = parâmetro não usado
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            # Devolve a mensagem e as opções válidas, para o cliente corrigir.
            content={"detail": str(exc), "cidades_validas": exc.opcoes},
        )

    # 404: o card não existe (ou é de outro pipe, que não podemos mexer).
    @app.exception_handler(CardNaoEncontradoError)
    async def card_nao_encontrado(
        _: Request, exc: CardNaoEncontradoError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

        # 422: a fase de destino não existe; devolve as fases válidas.

    @app.exception_handler(FaseNaoEncontradaError)
    async def fase_nao_encontrada(
        _: Request, exc: FaseNaoEncontradaError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(exc), "fases_validas": exc.opcoes},
        )

    # 409 Conflict: o pedido é válido, mas conflita com o estado atual do card
    # (ex.: avançar um card que já está na fase final).
    @app.exception_handler(MovimentacaoInvalidaError)
    async def movimentacao_invalida(
        _: Request, exc: MovimentacaoInvalidaError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    # 502: o Pipefy devolveu "errors"; a falha é do sistema de trás, não do cliente.
    @app.exception_handler(PipefyError)
    async def erro_do_pipefy(_: Request, exc: PipefyError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": f"O Pipefy recusou a operação: {exc}"},
        )

    # 502: o Pipefy respondeu com status de erro (ex.: 401 de token inválido).
    @app.exception_handler(httpx.HTTPStatusError)
    async def pipefy_status_de_erro(
        _: Request, exc: httpx.HTTPStatusError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "detail": f"O Pipefy respondeu com erro HTTP {exc.response.status_code}."
            },
        )

    # 503: nem chegou resposta (Pipefy fora do ar, sem internet ou timeout).
    @app.exception_handler(httpx.RequestError)
    async def pipefy_indisponivel(_: Request, exc: httpx.RequestError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Não foi possível se comunicar com o Pipefy."},
        )
