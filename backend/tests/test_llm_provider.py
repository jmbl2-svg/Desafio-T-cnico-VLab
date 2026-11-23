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


def test_fallback_pos_timeout_e_resposta_invalida():
    from backend.adapters.offline_demo import orientar
    from backend.domain.models import PerfilCliente, RespostaModelo

    perfil = PerfilCliente("0001", "Maria", "leigo", "didatico", "chat")
    chamadas = []

    class Modelo:
        parametros = {}

        def __init__(self, modelo, resposta):
            self.modelo = modelo
            self.resposta = resposta

        def gerar(self, *_):
            chamadas.append(self.modelo)
            if isinstance(self.resposta, Exception):
                raise self.resposta
            return RespostaModelo(self.resposta, self.modelo)

    cadeia = llm_provider.GeminiFallback([
        Modelo("primario", llm_provider.ErroProvedor("Tempo limite excedido.")),
        Modelo("secundario", {"passos": []}),
        Modelo("terciario", orientar(perfil)),
    ])
    resposta = cadeia.gerar("prompt", perfil, "relato")
    assert resposta.modelo == "terciario"
    assert chamadas == ["primario", "secundario", "terciario"]
