import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_gera_com_perfil_numerico(tmp_path):
    raiz = Path(__file__).resolve().parents[2]
    ambiente = {**os.environ, "DATA_DIR": str(tmp_path), "LLM_PROVIDER": "fake", "PYTHONIOENCODING": "utf-8"}
    resultado = subprocess.run(
        [sys.executable, "-m", "backend.cli", "gerar", "--perfil", "0005",
         "--ticket-id", "pasta", "--versao", "v2", "--sem-cache"],
        cwd=raiz, env=ambiente, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    dados = json.loads(resultado.stdout)
    registro = json.loads(Path(dados["arquivo"]).read_text(encoding="utf-8"))
    assert registro["perfil"]["nome"] == "Luiza"
    assert registro["versao"] == "v2"
    assert dados["run_id"].isdigit()


def test_api_gera_resposta_com_o_mesmo_nucleo(tmp_path, monkeypatch):
    from backend.api import GeracaoInput, criar_execucao, obter_saude

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    resposta = criar_execucao(GeracaoInput(perfil_id="0001", ticket_id="pasta"))
    assert obter_saude()["status"] == "pronta"
    assert resposta["registro"]["perfil"]["nome"] == "Maria"
    assert resposta["saida"]["passos"]


def test_api_compara_e_grava_rubrica(tmp_path, monkeypatch):
    from backend.api import (
        AvaliacaoInput, ComparacaoInput, GeracaoInput,
        atualizar_avaliacao, criar_comparacao, criar_execucao,
    )
    from backend.domain.rules import CRITERIOS

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    ids = tuple(
        criar_execucao(GeracaoInput(perfil_id="0001", ticket_id="pasta", versao=v))["run_id"]
        for v in ("v1", "v2")
    )
    par = criar_comparacao(ComparacaoInput(run_ids=ids))
    notas = {
        run_id: {c: {"nota": 4, "justificativa": "A ação está clara."} for c in CRITERIOS}
        for run_id in ids
    }
    avaliacao = AvaliacaoInput(avaliador="Teste", notas=notas, conclusao="Comparei as duas versões.")
    assert atualizar_avaliacao(par["comparison_id"], avaliacao)["status"] == "concluida"


def test_pagina_inicial_exibe_formulario():
    from backend.api import pagina_inicial

    pagina = pagina_inicial()
    assert 'id="cenario"' in pagina
    assert "/api/execucoes" in pagina
