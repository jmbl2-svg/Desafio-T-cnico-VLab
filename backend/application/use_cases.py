from contextlib import nullcontext
from hashlib import sha256

from backend.application.ports import GeradorLLMPort, HistoricoPort, LockPort
from backend.domain.models import RespostaModelo
from backend.domain.rules import chave_execucao


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
    def __init__(self, gerador: GeradorLLMPort, historico: HistoricoPort, pasta_prompts, trava: LockPort | None = None):
        self.gerador = gerador
        self.historico = historico
        self.pasta_prompts = pasta_prompts
        self.trava = trava

    def executar(self, perfil, relato, tipo="resolucao", versao="v1", sem_cache=False):
        prompt, template_hash = _preparar_prompt(self.pasta_prompts, perfil, relato, tipo, versao)
        provedor = getattr(self.gerador, "provedor", "fake")
        modelo = getattr(self.gerador, "modelo", "fake-support-v1")
        parametros = getattr(self.gerador, "parametros", {})
        chave = chave_execucao({
            "perfil": perfil.to_dict(), "relato": relato, "tipo": tipo, "versao": versao,
            "template_hash": template_hash, "provedor": provedor,
            "modelo": getattr(self.gerador, "identidade_cache", modelo),
            "parametros": parametros,
        })
        with self.trava.adquirir(chave) if self.trava else nullcontext():
            anterior = None if sem_cache else self.historico.buscar_por_chave(chave)
            if anterior is None:
                gerado = self.gerador.gerar(prompt, perfil, relato, tipo, versao)
                if isinstance(gerado, RespostaModelo):
                    saida, modelo = gerado.saida, gerado.modelo
                else:
                    saida = gerado
                fonte = None
            else:
                saida = anterior["saida"]
                fonte = anterior["run_id"]
                modelo = anterior["modelo"]
            caminho = self.historico.salvar_execucao(
                perfil, relato, saida, tipo, versao, provedor=provedor, modelo=modelo,
                parametros=parametros, template_hash=template_hash, input_key=chave,
                source_run_id=fonte,
            )
            return saida, caminho
