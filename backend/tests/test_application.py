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
        def buscar_por_chave(self, chave):
            return None

        def salvar_execucao(self, perfil, relato, saida, tipo="resolucao", versao="v1", **metadados):
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


def test_cache_reutiliza_apenas_entradas_equivalentes(tmp_path):
    import json

    from backend.adapters.json_storage import JsonStorageAdapter
    from backend.adapters.llm_provider import FakeGeradorLLM

    raiz = Path(__file__).resolve().parents[2]
    historico = JsonStorageAdapter(raiz / "database", tmp_path)
    caso = GerarRespostaUseCase(FakeGeradorLLM(), historico, raiz / "IA" / "prompts")
    perfil = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")
    _, origem = caso.executar(perfil, "Arquivo ausente.")
    _, repeticao = caso.executar(perfil, "Arquivo ausente.")
    _, forcada = caso.executar(perfil, "Arquivo ausente.", sem_cache=True)
    _, nova_versao = caso.executar(perfil, "Arquivo ausente.", versao="v2")
    cached = json.loads(repeticao.read_text(encoding="utf-8"))
    assert cached["cache_hit"]
    assert cached["source_run_id"] == origem.stem
    for caminho in (origem, forcada, nova_versao):
        assert not json.loads(caminho.read_text(encoding="utf-8"))["cache_hit"]


def test_gravacao_preserva_execucao_em_caso_de_colisao(tmp_path, monkeypatch):
    from backend.adapters import json_storage
    from backend.adapters.offline_demo import orientar

    numeros = iter([1, 1, 2])
    monkeypatch.setattr(json_storage.secrets, "randbelow", lambda _: next(numeros))
    armazenamento = json_storage.JsonStorageAdapter(tmp_path, tmp_path / "runs")
    perfil = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")
    saida = orientar(perfil)
    primeiro = armazenamento.salvar_execucao(perfil, "Primeiro.", saida)
    segundo = armazenamento.salvar_execucao(perfil, "Segundo.", saida)
    assert segundo != primeiro
    assert "Primeiro." in primeiro.read_text(encoding="utf-8")
    assert set(primeiro.parent.iterdir()) == {primeiro, segundo}
