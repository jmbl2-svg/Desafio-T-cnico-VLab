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


def test_trava_tem_timeout_e_libera_apos_erro(tmp_path):
    import pytest

    from backend.adapters.file_lock import FileLock

    trava = FileLock(tmp_path, timeout=0)
    chave = "a" * 64
    with pytest.raises(RuntimeError, match="interrompido"):
        with trava.adquirir(chave):
            with pytest.raises(TimeoutError):
                with trava.adquirir(chave):
                    pytest.fail("Trava adquirida duas vezes")
            raise RuntimeError("interrompido")
    with trava.adquirir(chave):
        assert (tmp_path / f"{chave}.lock").is_file()
    assert not list(tmp_path.iterdir())


def test_compara_versoes_com_os_mesmos_controles(tmp_path):
    import pytest

    from backend.adapters.json_storage import JsonStorageAdapter
    from backend.adapters.llm_provider import FakeGeradorLLM
    from backend.application.use_cases import comparar_execucoes

    raiz = Path(__file__).resolve().parents[2]
    historico = JsonStorageAdapter(raiz / "database", tmp_path / "runs")
    caso = GerarRespostaUseCase(FakeGeradorLLM(), historico, raiz / "IA" / "prompts")
    perfil = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")
    _, primeira = caso.executar(perfil, "Arquivo ausente.", versao="v1")
    _, segunda = caso.executar(perfil, "Arquivo ausente.", versao="v2")
    par = comparar_execucoes(historico, primeira.stem, segunda.stem)
    assert historico.obter_comparacao(par["comparison_id"]) == par
    with pytest.raises(ValueError, match="distintas"):
        comparar_execucoes(historico, primeira.stem, primeira.stem)


def test_rubrica_exige_justificativa():
    import pytest
    from backend.domain.rules import CRITERIOS, validar_rubrica

    ids = ["111111111111", "222222222222"]
    notas = {
        run_id: {c: {"nota": 4, "justificativa": "A resposta orienta a próxima ação."} for c in CRITERIOS}
        for run_id in ids
    }
    validar_rubrica(ids, "Avaliador", notas, "Ambas são compreensíveis.")
    notas[ids[0]]["clarity"]["justificativa"] = ""
    with pytest.raises(ValueError, match="justificativa"):
        validar_rubrica(ids, "Avaliador", notas, "Ambas são compreensíveis.")


def test_resolucao_offline_aproveita_o_caso_da_pasta_compartilhada():
    from backend.adapters.llm_provider import FakeGeradorLLM
    from backend.domain.rules import validar_saida

    gerador = FakeGeradorLLM()
    perfil = PerfilCliente("0002", "Lucas", "intermediario", "direto", "email")
    relato = "O envio foi confirmado, mas minha colega não encontra o arquivo na pasta compartilhada."
    bases = (gerador.gerar("prompt", perfil, relato, versao=versao) for versao in ("v1", "v2"))
    v1, v2 = bases
    for saida in (v1, v2):
        validar_saida("resolucao", saida)
        assert len(saida["passos"]) == 2
        assert "destino" in saida["passos"][0]["acao"]
        assert "e-mail" in saida["passos"][0]["se_falhar"]
    assert "compare o destino" in v2["passos"][0]["sinal_esperado"]
    assert v1["passos"][0]["sinal_esperado"] != v2["passos"][0]["sinal_esperado"]
    outro = gerador.gerar("prompt", perfil, "Não consigo entrar no sistema.")
    assert "destino" not in outro["passos"][0]["acao"]
