# Imagem da API: Python 3.14 "slim" (só o essencial, imagem menor).
FROM python:3.14-slim

# Não gera arquivos .pyc e mostra os logs na hora (sem buffer).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala as dependências antes de copiar o código: enquanto o
# requirements.txt não mudar, o Docker reaproveita esta camada do cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Roda com um usuário comum, sem privilégios de administrador.
RUN useradd --create-home api
USER api

EXPOSE 8000

# 0.0.0.0 = aceita conexões de fora do contêiner (do seu computador).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
