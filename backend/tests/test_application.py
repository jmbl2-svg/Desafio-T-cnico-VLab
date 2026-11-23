from pathlib import Path

from backend.application.use_cases import GerarRespostaUseCase
from backend.domain.models import PerfilCliente


def test_caso_de_uso_envia_prompt_ao_gerador_e_grava():
    class Gerador:
        def gerar(self, prompt, perfil, relato, tipo="resolucao", versao="v1"):
            assert perfil.id == "0001"
            assert relato in prompt
            return {"passos": []}

    class Historico:
        def salvar_execucao(self, perfil, relato, saida, tipo="resolucao", versao="v1"):
            assert saida == {"passos": []}
            return Path("teste.json")

    pasta = Path(__file__).resolve().parents[2] / "IA" / "prompts"
    caso = GerarRespostaUseCase(Gerador(), Historico(), pasta)
    perfil = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")
    assert caso.executar(perfil, "Arquivo ausente.") == ({"passos": []}, Path("teste.json"))


def test_simulacao_muda_por_tipo_versao_e_nivel():
    from backend.adapters.llm_provider import FakeGeradorLLM
    from backend.domain.rules import validar_saida

    gerador = FakeGeradorLLM()
    maria = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")
    marcos = PerfilCliente("0004", "Marcos", "avancado", "didatico", "email")
    for tipo in ("resolucao", "diagnostico", "perguntas", "fluxo"):
        args = ("prompt", maria, "Arquivo ausente.", tipo)
        v1 = gerador.gerar(*args, "v1")
        v2 = gerador.gerar(*args, "v2")
        avancado = gerador.gerar("prompt", marcos, "Arquivo ausente.", tipo, "v2")
        assert v1 != v2
        assert v2 != avancado
        for resposta in (v1, v2, avancado):
            validar_saida(tipo, resposta)
