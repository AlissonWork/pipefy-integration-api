"""Ponto de entrada da API: cria a aplicação e junta rotas e tratamento de erros."""

from fastapi import FastAPI

from app.api.errors import registrar_handlers
from app.api.routes import pessoas, pipe

# Título, descrição e versão aparecem na documentação automática (/docs).
app = FastAPI(
    title="Pipefy Integration API",
    description="API de cadastro de Pessoas integrada ao Pipefy.",
    version="0.1.0",
)

# Pluga no app as rotas de cada arquivo (cada router é um assunto).
app.include_router(pessoas.router)
app.include_router(pipe.router)

# Liga a tradução de erros em respostas HTTP (422, 502, 503).
registrar_handlers(app)


# Rota simples registrada direto no app: responde se a API está no ar.
@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Verifica se a API está no ar."""
    return {"status": "ok"}
