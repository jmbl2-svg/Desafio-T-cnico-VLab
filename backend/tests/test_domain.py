import pytest

from backend.domain.rules import chave_execucao, validar_saida


def test_chave_independe_da_ordem_dos_campos():
    assert chave_execucao({"a": 1, "b": 2}) == chave_execucao({"b": 2, "a": 1})


def test_fluxo_rejeita_ciclo():
    with pytest.raises(ValueError, match="ciclos"):
        validar_saida("fluxo", {
            "inicio": "a",
            "nos": [{"id": "a", "condicao": "Continuar?", "destinos": {"sim": "a"}}],
            "ascii_diagram": "[a] -> [a]",
        })
