"""Provedor determinístico para a demonstração offline."""

import json
import logging
import time
import httpx

from backend.adapters.offline_demo import gerar_demonstracao
from backend.adapters.offline_demo import orientar as orientar
from backend.domain.models import RespostaModelo
from backend.domain.rules import validar_saida


class FakeGeradorLLM:
    provedor = "fake"
    modelo = "fake-support-v2"
    identidade_cache = "fake-support-v2-decisoes-r4"

    def gerar(self, prompt, perfil, relato, tipo="resolucao", versao="v1"):
        return gerar_demonstracao(perfil, relato, tipo, versao)


class ErroProvedor(RuntimeError):
    """Falha de configuração, transporte ou resposta do modelo."""


class GeminiGeradorLLM:
    provedor = "gemini"
    parametros = {"temperature": 0.2, "maxOutputTokens": 2048}

    def __init__(self, chave, modelo="gemini-4-hydrogen", timeout=12, base_url=None):
        if not chave:
            raise ErroProvedor("Configure LLM_API_KEY para usar o Gemini.")
        self.chave = chave
        self.modelo = modelo
        self.timeout = timeout
        self.base_url = (base_url or "https://generativelanguage.googleapis.com").rstrip("/")

    def gerar(self, prompt, perfil, relato, tipo="resolucao", versao="v1"):
        endpoint = f"{self.base_url}/v1beta/models/{self.modelo}:generateContent"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resposta = client.post(
                    endpoint,
                    headers={"x-goog-api-key": self.chave},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            **self.parametros, "responseMimeType": "application/json",
                        },
                    },
                )
            if not resposta.is_success:
                raise ErroProvedor(f"Gemini retornou HTTP {resposta.status_code}.")
            corpo = resposta.json()
            candidato = corpo["candidates"][0]
            partes = candidato["content"]["parts"]
            texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
            saida = json.loads(texto)
            if not isinstance(saida, dict):
                raise ValueError("A resposta deve ser um objeto JSON.")
            return RespostaModelo(saida, corpo.get("modelVersion") or self.modelo)
        except httpx.TimeoutException as erro:
            raise ErroProvedor("Tempo limite do Gemini excedido.") from erro
        except httpx.RequestError as erro:
            raise ErroProvedor("Falha de rede na comunicação com Gemini.") from erro
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as erro:
            raise ErroProvedor("Gemini devolveu uma resposta inválida.") from erro


class LLMIndisponivel(ErroProvedor):
    """A cadeia de geração não produziu uma resposta válida."""


class GeminiFallback:
    provedor = "gemini"

    def __init__(self, geradores):
        self.geradores = tuple(geradores)
        if not self.geradores:
            raise ErroProvedor("Configure ao menos um modelo Gemini.")
        self.modelo = self.geradores[0].modelo
        self.parametros = self.geradores[0].parametros
        self.identidade_cache = ",".join(g.modelo for g in self.geradores)

    def gerar(self, prompt, perfil, relato, tipo="resolucao", versao="v1"):
        logger = logging.getLogger("vlab.gemini")
        for gerador in self.geradores:
            inicio = time.monotonic()
            logger.info("Gemini: tentativa com %s", gerador.modelo)
            try:
                resposta = gerador.gerar(prompt, perfil, relato, tipo, versao)
                validar_saida(tipo, resposta.saida)
            except ErroProvedor as erro:
                logger.warning("Gemini: %s falhou: %s", gerador.modelo, erro)
            except ValueError:
                logger.warning("Gemini: %s retornou saída fora do contrato.", gerador.modelo)
            else:
                logger.info("Gemini: %s respondeu em %.2fs", resposta.modelo, time.monotonic()-inicio)
                return resposta
        raise LLMIndisponivel("O serviço está temporariamente indisponível. Tente novamente mais tarde.")


class OpenAIGeradorLLM:
    provedor = "openai"
    parametros = {"temperature": 0.2, "max_tokens": 2048}

    def __init__(self, chave, modelo="gpt-4o-mini", timeout=12, base_url=None):
        if not chave:
            raise ErroProvedor("Configure LLM_API_KEY para usar OpenAI.")
        self.chave = chave
        self.modelo = modelo
        self.timeout = timeout
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def gerar(self, prompt, perfil, relato, tipo="resolucao", versao="v1"):
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resposta = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.chave}"},
                    json={
                        "model": self.modelo,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        **self.parametros,
                    },
                )
            if not resposta.is_success:
                raise ErroProvedor(f"OpenAI retornou HTTP {resposta.status_code}.")
            corpo = resposta.json()
            saida = json.loads(corpo["choices"][0]["message"]["content"])
            if not isinstance(saida, dict):
                raise ValueError("A resposta deve ser um objeto JSON.")
            return RespostaModelo(saida, corpo.get("model") or self.modelo)
        except httpx.TimeoutException as erro:
            raise ErroProvedor("Tempo limite de OpenAI excedido.") from erro
        except httpx.RequestError as erro:
            raise ErroProvedor("Falha de rede na comunicação com OpenAI.") from erro
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as erro:
            raise ErroProvedor("OpenAI devolveu uma resposta inválida.") from erro
