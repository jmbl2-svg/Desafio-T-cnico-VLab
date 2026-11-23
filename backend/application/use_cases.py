import json
import secrets
from pathlib import Path
from contextlib import nullcontext
from datetime import datetime, timezone
from hashlib import sha256

from backend.application.ports import GeradorLLMPort, HistoricoPort, LockPort
from backend.domain.models import Comparacao, RespostaModelo
from backend.domain.rules import chave_execucao, validar_par, validar_rubrica


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


def comparar_execucoes(historico, primeira_id, segunda_id):
    primeira = historico.obter_execucao(primeira_id)
    segunda = historico.obter_execucao(segunda_id)
    if primeira is None or segunda is None:
        raise LookupError("Uma das execuções não foi encontrada.")
    validar_par(primeira, segunda)
    comparacao = Comparacao(
        comparison_id=f"comp_{secrets.token_hex(12)}",
        run_ids=[primeira_id, segunda_id],
        criada_em=datetime.now(timezone.utc).isoformat(),
    ).to_dict()
    historico.salvar_comparacao(comparacao)
    return comparacao


def avaliar_comparacao(historico, comparison_id, avaliador, notas, conclusao):
    comparacao = historico.obter_comparacao(comparison_id)
    if comparacao is None:
        raise LookupError("Comparação não encontrada.")
    validar_rubrica(comparacao["run_ids"], avaliador, notas, conclusao)
    comparacao["avaliacao"] = {
        "avaliador": avaliador.strip(), "notas": notas, "conclusao": conclusao.strip(),
    }
    comparacao["status"] = "concluida"
    historico.salvar_comparacao(comparacao)
    return comparacao


def arquivos_exportacao(historico, comparison_id):
    comparacao = historico.obter_comparacao(comparison_id)
    if comparacao is None:
        raise LookupError("Comparação não encontrada.")
    if comparacao["status"] != "concluida":
        raise ValueError("Conclua a rubrica antes de exportar.")
    arquivos = {f"comparisons/{comparison_id}.json": comparacao}
    for run_id in comparacao["run_ids"]:
        registro = historico.obter_execucao(run_id)
        if registro is None:
            raise LookupError("Uma execução vinculada não foi encontrada.")
        arquivos[f"runs/{run_id}.json"] = registro
    return arquivos


def exportar_comparacao(historico, comparison_id, destino):
    arquivos = arquivos_exportacao(historico, comparison_id)
    for nome, dados in arquivos.items():
        caminho = Path(destino) / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return len(arquivos)
