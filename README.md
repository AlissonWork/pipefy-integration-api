# Pipefy Integration API

API em Python que integra um **cadastro de Pessoas** ao [Pipefy](https://www.pipefy.com/).
Cada Pessoa cadastrada vira um **card** no pipe *Desafio - Vaga Profectum 2026*, e a API
permite criar, consultar, mover entre fases e apagar esses cards.


## Sumário

- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Como rodar](#como-rodar)
- [Endpoints](#endpoints)
- [Exemplos de uso](#exemplos-de-uso)
- [Tratamento de erros](#tratamento-de-erros)
- [Arquitetura](#arquitetura)
- [Decisões técnicas](#decisões-técnicas)
- [Demonstração](#demonstração)
- [Próximos passos](#próximos-passos)

## Funcionalidades

Os três requisitos do desafio:

| Requisito | Endpoint |
|---|---|
| Criar um card com os campos da Pessoa | `POST /pessoas` |
| Excluir um card pelo ID | `DELETE /pessoas/{id}` |
| Avançar ou mudar a fase do card, avisando quando chega na fase final | `PATCH /pessoas/{id}/fase` |

Além deles, a API oferece rotas de apoio: listar e detalhar cards, consultar a
estrutura do pipe e listar as cidades aceitas no cadastro.

## Tecnologias

| Ferramenta | Uso |
|---|---|
| **Python 3.14** | linguagem |
| **FastAPI** | framework web, validação e documentação automática (Swagger) |
| **Pydantic v2** | schemas de entrada e saída, validações |
| **pydantic-settings** | configuração via variáveis de ambiente (`.env`) |
| **httpx** | cliente HTTP assíncrono para a API GraphQL do Pipefy |
| **Uvicorn** | servidor ASGI |
| **Ruff** | lint e formatação |

## Como rodar

### 1. Pré-requisitos

- Python 3.14 (versão em que o projeto foi desenvolvido e testado)
- Um token de acesso à API do Pipefy com permissão no pipe

### 2. Clonar e instalar

```bash
git clone https://github.com/AlissonWork/pipefy-integration-api.git
cd pipefy-integration-api

python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash)
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements-dev.txt
```

> `requirements-dev.txt` instala as dependências da aplicação e o Ruff.
> Para só rodar a API, `requirements.txt` basta.

### 3. Configurar o `.env`

```bash
cp .env.example .env
```

Abra o `.env` e preencha o token:

| Variável | Obrigatória | Descrição |
|---|---|---|
| `PIPEFY_TOKEN` | sim | token de acesso à API do Pipefy (Bearer) |
| `PIPEFY_PIPE_ID` | sim | ID do pipe de Pessoas (`303843596`) |
| `PIPEFY_CIDADE_TABLE_ID` | sim | ID da tabela de cidades ligada ao campo Cidade (`yJ1z4HYx`) |
| `PIPEFY_API_URL` | não | endereço da API GraphQL (padrão: `https://api.pipefy.com/graphql`) |
| `PIPEFY_TIMEOUT` | não | segundos de espera pela resposta do Pipefy (padrão: `10`) |

O `.env` está no `.gitignore`: o token nunca vai para o repositório.
Se uma variável obrigatória faltar, o pydantic-settings acusa qual é na primeira
requisição.

### 4. Subir a API

```bash
uvicorn app.main:app --reload
```

| Endereço | O que é |
|---|---|
| http://127.0.0.1:8000/docs | documentação interativa (Swagger), dá para testar tudo por ali |
| http://127.0.0.1:8000/redoc | documentação em formato de leitura |
| http://127.0.0.1:8000/health | verificação rápida de que a API está no ar |

### 5. Qualidade de código

```bash
ruff format .   # formata
ruff check .    # aponta problemas (imports, variáveis não usadas, etc.)
```

## Endpoints

### Pessoas

| Método | Rota | Descrição | Sucesso |
|---|---|---|---|
| `POST` | `/pessoas` | cadastra uma Pessoa (cria o card na primeira fase) | `201` |
| `GET` | `/pessoas` | lista os cards, do mais novo para o mais antigo; filtro opcional `?fase=` | `200` |
| `GET` | `/pessoas/{id}` | detalha um card com todos os campos | `200` |
| `PATCH` | `/pessoas/{id}/fase` | avança o card ou move para a fase `destino` | `200` |
| `DELETE` | `/pessoas/{id}` | apaga o card | `204` |

### Pipe

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/pipe` | estrutura do pipe: fases e campos do formulário |
| `GET` | `/cidades` | cidades aceitas no campo Cidade |
| `GET` | `/health` | status da API |

### Campos da Pessoa (`POST /pessoas`)

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome` | texto | sim | 2 a 120 caracteres; vira o título do card |
| `cidade` | texto | sim | precisa existir na tabela de cidades (aceita sem acento e em minúsculas) |
| `cpf` | texto | não | dígitos verificadores validados; aceita com ou sem máscara e é salvo como `000.000.000-00` |
| `data_de_nascimento` | data (`AAAA-MM-DD`) | não | não pode estar no futuro |
| `telefone` | texto | não | 8 a 20 caracteres |
| `sexo` | opção | não | `Masculino`, `Feminino` ou `Prefere não responder` |
| `hobbies` | lista de opções | não | `Teatro`, `Música`, `Cinema`, `Esportes`, `Leitura`, `Viagem`, `Artes` |

A **data de envio** (campo `data` do formulário) é preenchida automaticamente pela API.

### Fases do pipe

```
Caixa de entrada  →  Fazendo  →  Concluído (fase final)
```

O `PATCH /pessoas/{id}/fase` funciona de dois jeitos:

- **sem corpo**: avança o card para a **próxima** fase;
- **com `{"destino": "..."}`**: move para a fase indicada, pelo **nome** (sem diferenciar
  acento ou maiúsculas, ex.: `"concluido"`) ou pelo **ID** da fase.

Quando o card chega na fase final, a resposta traz `"finalizado": true` e uma mensagem
avisando.

## Exemplos de uso

### Cadastrar uma Pessoa

```bash
curl -X POST http://127.0.0.1:8000/pessoas \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Maria Silva",
    "cidade": "Fortaleza",
    "cpf": "52998224725",
    "data_de_nascimento": "1995-08-20",
    "telefone": "85999999999",
    "sexo": "Feminino",
    "hobbies": ["Leitura", "Cinema"]
  }'
```

Resposta (`201 Created`):

```json
{
  "id": "1474000000",
  "titulo": "Maria Silva",
  "url": "https://app.pipefy.com/pipes/303843596#cards/1474000000",
  "fase": { "id": "323403002", "nome": "Caixa de entrada" }
}
```

### Avançar a fase

```bash
curl -X PATCH http://127.0.0.1:8000/pessoas/1474000000/fase
```

Ao chegar na fase final (`200 OK`):

```json
{
  "id": "1474000000",
  "titulo": "Maria Silva",
  "fase_anterior": { "id": "323403003", "nome": "Fazendo" },
  "fase_atual": { "id": "323403004", "nome": "Concluído" },
  "finalizado": true,
  "mensagem": "O card chegou na fase final (Concluído)."
}
```

### Mover para uma fase específica

```bash
curl -X PATCH http://127.0.0.1:8000/pessoas/1474000000/fase \
  -H "Content-Type: application/json" \
  -d '{"destino": "caixa de entrada"}'
```

### Listar e detalhar

```bash
curl "http://127.0.0.1:8000/pessoas?fase=concluido"
curl http://127.0.0.1:8000/pessoas/1474000000
```

### Apagar

```bash
curl -X DELETE http://127.0.0.1:8000/pessoas/1474000000   # 204 No Content
```

## Tratamento de erros

Cada erro tem um status HTTP que indica **de quem é o problema** e uma mensagem
que ajuda a corrigir:

| Status | Quando | Exemplo de resposta |
|---|---|---|
| `422` | dados inválidos (CPF, data futura, opção inexistente, JSON mal formado) | detalhe do campo com problema, gerado pelo Pydantic |
| `422` | cidade não cadastrada | `{"detail": "Cidade 'Recife' não encontrada.", "cidades_validas": [...]}` |
| `422` | fase de destino inexistente | `{"detail": "Fase 'xyz' não encontrada.", "fases_validas": [...]}` |
| `404` | card inexistente **ou de outro pipe** | `{"detail": "Card 123 não encontrado no pipe de Pessoas."}` |
| `409` | card já está na fase final, ou já está na fase de destino | `{"detail": "O card já está na fase final ('Concluído')."}` |
| `502` | o Pipefy recusou a operação ou respondeu com erro (ex.: token inválido) | `{"detail": "O Pipefy respondeu com erro HTTP 401."}` |
| `503` | o Pipefy não respondeu (fora do ar, sem internet ou timeout) | `{"detail": "Não foi possível se comunicar com o Pipefy."}` |

## Arquitetura

O projeto é dividido em camadas, cada uma com uma responsabilidade:

```
Requisição HTTP
     │
     ▼
┌─────────────┐   valida a entrada (schemas) e define o status HTTP
│   Rotas     │   app/api/routes/
└─────┬───────┘
      ▼
┌─────────────┐   regras de negócio: resolver a cidade, escolher a próxima
│   Service   │   fase, conferir se o card é do pipe
└─────┬───────┘   app/services/pessoas.py
      ▼
┌─────────────┐   comunicação com o Pipefy: GraphQL, token, erros HTTP
│   Client    │   app/clients/pipefy.py
└─────┬───────┘
      ▼
   Pipefy (API GraphQL)
```

```
app/
├── main.py                 # cria o app e registra rotas e tratamento de erros
├── core/
│   └── config.py           # configurações lidas do .env (Settings)
├── api/
│   ├── dependencies.py     # injeção de dependência (Settings → Client → Service)
│   ├── errors.py           # exceções da aplicação → respostas HTTP
│   └── routes/
│       ├── pessoas.py      # POST, GET, PATCH e DELETE de /pessoas
│       └── pipe.py         # /pipe e /cidades
├── schemas/
│   ├── pessoa.py           # entrada do cadastro e validações (CPF, data, opções)
│   └── card.py             # formatos de resposta
├── services/
│   └── pessoas.py          # regras de negócio
└── clients/
    └── pipefy.py           # client da API GraphQL do Pipefy
```

**Por que separar assim?**

- **As rotas não sabem que o Pipefy existe**: elas só recebem e devolvem dados.
- **O service não sabe de HTTP nem de GraphQL**: só aplica as regras.
- **O client é o único que fala com o Pipefy**: trocar de API ou de biblioteca HTTP
  mexe em um arquivo só.
- **As peças são injetadas** (`Depends`): o service recebe o client pronto, o que
  permite trocá-lo por um client falso em testes, sem chamar o Pipefy de verdade.

## Decisões técnicas

**Proteção do pipe compartilhado.** O token pertence a uma conta que pode ter outros
pipes, e um ID de card de qualquer um deles seria aceito pelo Pipefy. Antes de detalhar, mover ou apagar, a API busca o card e confere se ele pertence ao
pipe configurado. Se não pertencer, responde `404` sem tocar no card.

**Fases lidas do próprio pipe.** A ordem das fases e qual é a final vêm do Pipefy
(campo `done`), não de valores fixos no código. Se uma fase for criada ou renomeada,
a API continua funcionando.

**Cidade pelo nome, não pelo ID.** O campo Cidade é um *connector* para uma tabela,
e o Pipefy exige o ID do registro. A API recebe o nome, busca na tabela e converte.
A comparação ignora acentos e maiúsculas (`"eusebio"` encontra `"Eusébio"`). A tabela
tem um registro duplicado (`Fortaleza` e `fortaleza`), então a API usa o mais antigo.
Quando a cidade não existe, o erro lista as opções válidas.

**Validação na entrada.** Os dados são validados antes de qualquer chamada ao Pipefy:
CPF com dígitos verificadores (e rejeitando sequências como `111.111.111-11`), data
de nascimento no passado e opções de sexo e hobbies restritas às do formulário. Dados
inválidos nunca chegam ao Pipefy.

**Erros com o status certo.** O GraphQL do Pipefy responde `200` mesmo quando há erro
(a falha vem na chave `errors`). O client detecta isso e o converte em exceção, e um
único módulo (`errors.py`) traduz cada exceção no status adequado. Assim, quem usa a API
sabe se o problema foi nos dados enviados (`4xx`) ou no Pipefy (`5xx`).

**Segurança do token.** O token fica só no `.env`, fora do Git, e é guardado como
`SecretStr`, que não aparece em logs nem em mensagens de erro. As consultas GraphQL usam
**variáveis** em vez de concatenar valores no texto, o que evita *injection*.

**Mínimo de dados pessoais.** A listagem (`GET /pessoas`) devolve só ID, título, fase
e data, sem CPF ou telefone. Os dados completos só aparecem no detalhe de um card
específico (princípio da minimização da LGPD).

**Paginação.** O Pipefy devolve no máximo 50 cards por consulta. A listagem pede página
por página até juntar todos.

## Demonstração

A pasta [`bruno/`](bruno/) tem uma coleção do [Bruno](https://www.usebruno.com/) com o
fluxo completo, já em ordem: cadastrar, consultar, avançar até a fase final, os
principais erros e a exclusão.

1. No Bruno: **Open Collection** → selecione a pasta `bruno/`.
2. Com a API rodando, execute as requisições em ordem (ou use **Run** na coleção).

O endereço da API (`http://127.0.0.1:8000`) já vem definido na coleção. Se a API rodar
em outro endereço, ajuste o ambiente **Local** e selecione-o no canto superior direito.

O ID do card criado é guardado automaticamente e reaproveitado nas requisições seguintes.
Cada requisição confere o status esperado.
