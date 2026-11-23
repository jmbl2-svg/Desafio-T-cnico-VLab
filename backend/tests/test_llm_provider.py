import httpx

from backend.adapters import llm_provider


def test_gemini_envia_chave_no_cabecalho_e_registra_modelo(monkeypatch):
    def responder(pedido):
        assert pedido.headers["x-goog-api-key"] == "teste"
        assert "teste" not in str(pedido.url)
        return httpx.Response(200, json={
            "modelVersion": "gemini-efetivo",
            "candidates": [{"content": {"parts": [{"text": '{"passos": []}'}]}}],
        })

    client = httpx.Client(transport=httpx.MockTransport(responder))
    monkeypatch.setattr(llm_provider.httpx, "Client", lambda **kwargs: client)
    provider = llm_provider.GeminiGeradorLLM("teste")
    resposta = provider.gerar("prompt", None, "relato")
    assert resposta.modelo == "gemini-efetivo"
    assert resposta.saida == {"passos": []}
