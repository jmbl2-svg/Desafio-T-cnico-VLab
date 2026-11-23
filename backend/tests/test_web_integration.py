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
