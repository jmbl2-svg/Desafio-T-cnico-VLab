from typing import Protocol


class GeradorLLMPort(Protocol):
    def gerar(self, prompt, perfil, relato, tipo="resolucao", versao="v1"):
        """Recebe o prompt e devolve uma resposta estruturada."""
        ...


class HistoricoPort(Protocol):
    def salvar_execucao(self, perfil, relato, saida, tipo="resolucao", versao="v1", **metadados):
        """Grava uma execução concluída e devolve seu caminho."""
        ...
