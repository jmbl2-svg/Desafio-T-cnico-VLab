import json

from backend import cli


def perfil_por_id(perfil_id):
    return next(
        perfil
        for perfil in cli.carregar_perfis()
        if perfil.id == perfil_id
    )


def test_orientacao_muda_conforme_o_estilo():
    maria = perfil_por_id("0001")
    luiza = perfil_por_id("0005")

    passo_maria = cli.orientar(maria)["passos"][0]
    passo_luiza = cli.orientar(luiza)["passos"][0]

    assert passo_maria["ordem"] == passo_luiza["ordem"] == 1
    assert "Por que fazer isso?" in passo_maria["acao"]
    assert "imediatamente antes" in passo_luiza["sinal_esperado"]
    assert passo_maria["se_falhar"] == passo_luiza["se_falhar"]


def test_salva_execucao_com_codigo_numerico(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "PASTA_EXECUCOES", tmp_path / "runs")
    perfil = perfil_por_id("0005")
    relato = "Minha colega não encontra o arquivo."
    saida = cli.orientar(perfil)

    caminho = cli.salvar_execucao(perfil, relato, saida)
    registro = json.loads(caminho.read_text(encoding="utf-8"))

    assert len(caminho.stem) == 12
    assert caminho.stem.isdigit()
    assert registro["run_id"] == caminho.stem
    assert registro["perfil"]["id"] == "0005"
    assert registro["ticket"] == relato
    assert registro["saida"] == saida