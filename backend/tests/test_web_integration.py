from fastapi.testclient import TestClient

from backend.api import app


def entrar(client, usuario):
    credenciais = {"usuario": usuario, "senha": "senha-ficticia-123"}
    assert client.post("/api/auth/registro", json=credenciais).status_code == 201
    assert client.post("/api/auth/login", json=credenciais).status_code == 200


def test_sessao_e_isolamento_de_execucoes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    with TestClient(app) as alice, TestClient(app) as bruno:
        assert alice.get("/api/perfis").status_code == 401
        entrar(alice, "alice")
        entrar(bruno, "bruno")
        run = alice.post("/api/execucoes", json={"perfil_id": "0001", "ticket_id": "pasta"})
        assert run.status_code == 201
        caminho = f"/api/execucoes/{run.json()['run_id']}"
        assert alice.get(caminho).status_code == 200
        assert bruno.get(caminho).status_code == 404
        assert alice.post("/api/auth/logout").status_code == 204
        assert alice.get(caminho).status_code == 401


def test_zip_requer_rubrica_e_inclui_tres_json(tmp_path, monkeypatch):
    from io import BytesIO
    from zipfile import ZipFile

    from backend.domain.rules import CRITERIOS

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    with TestClient(app) as client:
        entrar(client, "avaliador")
        run_ids = []
        for versao in ("v1", "v2"):
            resultado = client.post("/api/execucoes", json={
                "perfil_id":"0001", "ticket_id":"pasta", "versao":versao,
            })
            assert resultado.status_code == 201
            run_ids.append(resultado.json()["run_id"])
        par = client.post("/api/comparacoes", json={"run_ids":run_ids})
        assert par.status_code == 201
        url = "/api/comparacoes/" + par.json()["comparison_id"]
        assert client.get(url+"/exportar").status_code == 422
        notas = {id_: {c: {"nota":4,"justificativa":"A ação é verificável."} for c in CRITERIOS} for id_ in run_ids}
        res = client.put(url+"/avaliacao", json={
            "avaliador":"Teste", "notas":notas, "conclusao":"Comparei as ações.",
        })
        assert res.status_code == 200
        pacote = client.get(url+"/exportar")
        assert pacote.status_code == 200
        with ZipFile(BytesIO(pacote.content)) as zipfile:
            assert len(zipfile.namelist()) == 3
