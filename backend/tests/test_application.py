from pathlib import Path

from backend.application.use_cases import GerarRespostaUseCase
from backend.domain.models import PerfilCliente


def test_caso_de_uso_envia_prompt_ao_gerador_e_grava():
    class Gerador:
        def gerar(self, prompt, perfil, relato, tipo="resolucao"):
            assert perfil.id == "0001"
            assert relato in prompt
            return {"passos": []}

    class Historico:
        def salvar_execucao(self, perfil, relato, saida, tipo="resolucao"):
            assert saida == {"passos": []}
            return Path("teste.json")

    pasta = Path(__file__).resolve().parents[2] / "IA" / "prompts"
    caso = GerarRespostaUseCase(Gerador(), Historico(), pasta)
    perfil = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")
    assert caso.executar(perfil, "Arquivo ausente.") == ({"passos": []}, Path("teste.json"))
