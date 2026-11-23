import pytest

from backend.adapters.json_storage import JsonStorageAdapter
from backend.domain.models import PerfilCliente
from backend.domain.rules import validar_resolucao


def test_aceita_resolucao_com_passo_completo():
    saida = {
        "passos": [
            {
                "ordem": 1,
                "acao": "Confira a lista de arquivos enviados.",
                "sinal_esperado": "O nome do arquivo aparece na lista.",
                "se_falhar": "Informe o status exibido no chat.",
            }
        ]
    }

    validar_resolucao(saida)


def test_rejeita_passo_com_campo_vazio():
    saida = {
        "passos": [
            {
                "ordem": 1,
                "acao": "Confira a lista de arquivos enviados.",
                "sinal_esperado": "   ",
                "se_falhar": "Informe o status exibido no chat.",
            }
        ]
    }

    with pytest.raises(ValueError, match="sinal_esperado"):
        validar_resolucao(saida)


def test_impede_gravacao_de_resolucao_sem_passos(tmp_path):
    pasta_execucoes = tmp_path / "runs"
    armazenamento = JsonStorageAdapter(tmp_path, pasta_execucoes)
    perfil = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")

    with pytest.raises(ValueError, match="pelo menos um passo"):
        armazenamento.salvar_execucao(perfil, "Arquivo não aparece.", {"passos": []})

    assert not pasta_execucoes.exists()


def test_gera_e_valida_diagnostico():
    from backend.adapters.llm_provider import FakeGeradorLLM
    from backend.domain.rules import validar_saida

    perfil = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")
    saida = FakeGeradorLLM().gerar("prompt", perfil, "Falha relatada.", "diagnostico")
    validar_saida("diagnostico", saida)
