from hashlib import sha256

from backend.application.ports import GeradorLLMPort, HistoricoPort


def _preparar_prompt(pasta_prompts, perfil, relato, tipo="resolucao", versao="v1"):
    if versao not in ("v1", "v2"):
        raise ValueError("Versão do prompt inválida.")
    if tipo not in ("resolucao", "diagnostico", "perguntas", "fluxo"):
        raise ValueError("Tipo de conteúdo inválido.")
    pasta = pasta_prompts / versao
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
    template_hash = sha256(f"{base}\n{estrategia}".encode("utf-8")).hexdigest()
    return f"{contexto}\n{estrategia}", template_hash


def montar_prompt(pasta_prompts, perfil, relato, tipo="resolucao", versao="v1"):
    prompt, _ = _preparar_prompt(pasta_prompts, perfil, relato, tipo, versao)
    return prompt


class GerarRespostaUseCase:
    def __init__(self, gerador: GeradorLLMPort, historico: HistoricoPort, pasta_prompts):
        self.gerador = gerador
        self.historico = historico
        self.pasta_prompts = pasta_prompts

    def executar(self, perfil, relato, tipo="resolucao", versao="v1"):
        prompt, template_hash = _preparar_prompt(self.pasta_prompts, perfil, relato, tipo, versao)
        saida = self.gerador.gerar(prompt, perfil, relato, tipo, versao)
        caminho = self.historico.salvar_execucao(
            perfil, relato, saida, tipo, versao,
            provedor=getattr(self.gerador, "provedor", "fake"),
            modelo=getattr(self.gerador, "modelo", "fake-support-v1"),
            parametros=getattr(self.gerador, "parametros", {}),
            template_hash=template_hash,
        )
        return saida, caminho
