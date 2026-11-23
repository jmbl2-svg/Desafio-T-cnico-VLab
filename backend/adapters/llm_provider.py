"""Provedor determinístico para a demonstração offline."""

from backend.adapters.offline_demo import gerar_demonstracao
from backend.adapters.offline_demo import orientar as orientar


class FakeGeradorLLM:
    def gerar(self, prompt, perfil, relato, tipo="resolucao", versao="v1"):
        return gerar_demonstracao(perfil, relato, tipo, versao)
