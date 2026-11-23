from backend.application.ports import GeradorLLMPort, HistoricoPort


def montar_prompt(pasta_prompts, perfil, relato, tipo="resolucao"):
    pasta = pasta_prompts / "v1"
    base = (pasta / "base.txt").read_text(encoding="utf-8")
    estrategia = (pasta / f"{tipo}.txt").read_text(encoding="utf-8")
    contexto = base.format(
        nome=perfil.nome,
        perfil_id=perfil.id,
        nivel=perfil.nivel,
        estilo=perfil.estilo,
        canal=perfil.canal,
        relato=relato,
    )
    return f"{contexto}\n{estrategia}"


class GerarRespostaUseCase:
    def __init__(self, gerador: GeradorLLMPort, historico: HistoricoPort, pasta_prompts):
        self.gerador = gerador
        self.historico = historico
        self.pasta_prompts = pasta_prompts

    def executar(self, perfil, relato, tipo="resolucao"):
        prompt = montar_prompt(self.pasta_prompts, perfil, relato, tipo)
        saida = self.gerador.gerar(prompt, perfil, relato, tipo)
        caminho = self.historico.salvar_execucao(perfil, relato, saida, tipo)
        return saida, caminho
