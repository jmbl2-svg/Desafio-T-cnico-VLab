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
