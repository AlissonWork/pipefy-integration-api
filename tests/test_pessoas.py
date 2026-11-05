"""Testes das rotas de Pessoa, com o Pipefy falso do conftest."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import PIPE_ID, ClienteFalso

# Corpo válido reaproveitado pelos testes de cadastro.
PESSOA = {
    "nome": "Maria Silva",
    "cidade": "Fortaleza",
    "cpf": "52998224725",
    "data_de_nascimento": "1995-08-20",
    "sexo": "Feminino",
    "hobbies": ["Leitura"],
}


@pytest.fixture
def card_id(client: TestClient) -> str:
    """Cria um card pela API e devolve o ID (ponto de partida dos testes)."""
    return client.post("/pessoas", json=PESSOA).json()["id"]


class TestCriarPessoa:
    """POST /pessoas"""

    def test_retorna_201_na_primeira_fase(
        self, client: TestClient, pipefy: ClienteFalso
    ) -> None:
        resposta = client.post("/pessoas", json=PESSOA)

        assert resposta.status_code == 201
        assert resposta.json()["fase"]["nome"] == "Caixa de entrada"
        assert pipefy.campos_enviados["cpf"] == "529.982.247-25"  # salvo com máscara

    # Roda o mesmo teste uma vez para cada par (cidade enviada, ID esperado).
    @pytest.mark.parametrize(
        ("cidade", "id_esperado"),
        [
            ("eusebio", "20"),  # sem acento e minúscula
            ("fortaleza", "10"),  # duplicada na tabela: usa o registro original
        ],
    )
    def test_encontra_cidade_sem_acento_e_maiuscula(
        self, client: TestClient, pipefy: ClienteFalso, cidade: str, id_esperado: str
    ) -> None:
        resposta = client.post("/pessoas", json={**PESSOA, "cidade": cidade})

        assert resposta.status_code == 201
        assert pipefy.campos_enviados["cidade"] == [id_esperado]

    def test_cidade_inexistente_retorna_422_com_opcoes(
        self, client: TestClient, pipefy: ClienteFalso
    ) -> None:
        resposta = client.post("/pessoas", json={**PESSOA, "cidade": "Recife"})

        assert resposta.status_code == 422
        assert "Fortaleza" in resposta.json()["cidades_validas"]
        assert pipefy.cards == {}  # nenhum card foi criado

    def test_cpf_invalido_retorna_422_sem_chamar_o_pipefy(
        self, client: TestClient, pipefy: ClienteFalso
    ) -> None:
        resposta = client.post("/pessoas", json={**PESSOA, "cpf": "111.111.111-11"})

        assert resposta.status_code == 422
        assert pipefy.cards == {}


class TestMoverFase:
    """PATCH /pessoas/{id}/fase"""

    def test_avanca_para_a_proxima_fase(self, client: TestClient, card_id: str) -> None:
        resposta = client.patch(f"/pessoas/{card_id}/fase")

        assert resposta.status_code == 200
        assert resposta.json()["fase_atual"]["nome"] == "Fazendo"
        assert resposta.json()["finalizado"] is False

    def test_avisa_quando_chega_na_fase_final(
        self, client: TestClient, card_id: str
    ) -> None:
        client.patch(f"/pessoas/{card_id}/fase")  # Caixa de entrada -> Fazendo
        resposta = client.patch(f"/pessoas/{card_id}/fase")  # Fazendo -> Concluído

        corpo = resposta.json()
        assert corpo["fase_atual"]["nome"] == "Concluído"
        assert corpo["finalizado"] is True
        assert "fase final" in corpo["mensagem"]

    def test_avancar_na_fase_final_retorna_409(
        self, client: TestClient, card_id: str
    ) -> None:
        client.patch(f"/pessoas/{card_id}/fase", json={"destino": "Concluído"})

        resposta = client.patch(f"/pessoas/{card_id}/fase")

        assert resposta.status_code == 409

    def test_move_para_destino_pelo_nome(
        self, client: TestClient, card_id: str
    ) -> None:
        resposta = client.patch(
            f"/pessoas/{card_id}/fase", json={"destino": "concluido"}
        )

        assert resposta.status_code == 200
        assert resposta.json()["finalizado"] is True

    def test_destino_inexistente_retorna_422_com_opcoes(
        self, client: TestClient, card_id: str
    ) -> None:
        resposta = client.patch(f"/pessoas/{card_id}/fase", json={"destino": "xyz"})

        assert resposta.status_code == 422
        assert resposta.json()["fases_validas"] == [
            "Caixa de entrada",
            "Fazendo",
            "Concluído",
        ]


class TestApagarPessoa:
    """DELETE /pessoas/{id}"""

    def test_apaga_o_card(
        self, client: TestClient, pipefy: ClienteFalso, card_id: str
    ) -> None:
        resposta = client.delete(f"/pessoas/{card_id}")

        assert resposta.status_code == 204
        assert card_id not in pipefy.cards

    def test_card_inexistente_retorna_404(self, client: TestClient) -> None:
        resposta = client.delete("/pessoas/999")

        assert resposta.status_code == 404

    def test_nao_apaga_card_de_outro_pipe(
        self, client: TestClient, pipefy: ClienteFalso, card_id: str
    ) -> None:
        pipefy.cards[card_id]["pipe"]["id"] = str(PIPE_ID + 1)  # finge outro pipe

        resposta = client.delete(f"/pessoas/{card_id}")

        assert resposta.status_code == 404
        assert card_id in pipefy.cards  # o card continua lá
