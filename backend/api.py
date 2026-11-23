import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from backend.adapters.json_storage import JsonStorageAdapter
from backend.adapters.llm_provider import ErroProvedor, LLMIndisponivel
from backend.bootstrap import criar_geracao, diretorio_dados
from backend.application.use_cases import avaliar_comparacao, comparar_execucoes


RAIZ = Path(__file__).resolve().parents[1]
CATALOGOS = RAIZ / "database"
PROMPTS = RAIZ / "IA" / "prompts"
app = FastAPI(title="V-LAB Suporte Técnico")
logger_gemini = logging.getLogger("vlab.gemini")
logger_gemini.setLevel(logging.INFO)
if not logger_gemini.hasHandlers():
    handler_gemini = logging.StreamHandler()
    handler_gemini.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger_gemini.addHandler(handler_gemini)


class GeracaoInput(BaseModel):
    perfil_id: str = Field(pattern=r"^[0-9]{4}$")
    ticket_id: str | None = Field(default=None, max_length=64)
    ticket: str | None = Field(default=None, max_length=12000)
    tipo: Literal["resolucao", "diagnostico", "perguntas", "fluxo"] = "resolucao"
    versao: Literal["v1", "v2"] = "v1"
    sem_cache: bool = False

    @model_validator(mode="after")
    def conferir_ticket(self):
        if bool(self.ticket_id) == bool(self.ticket and self.ticket.strip()):
            raise ValueError("Informe um ticket do catálogo ou um relato livre.")
        return self


def novo_historico():
    return JsonStorageAdapter(CATALOGOS, diretorio_dados(RAIZ / "data") / "runs")


@app.get("/api/saude")
def obter_saude():
    return {"status": "pronta"}


@app.get("/api/perfis")
def listar_perfis():
    return [perfil.to_dict() for perfil in novo_historico().listar_perfis()]


@app.get("/api/tickets")
def listar_tickets():
    return novo_historico().listar_tickets()


@app.post("/api/execucoes", status_code=201)
def criar_execucao(payload: GeracaoInput):
    historico = novo_historico()
    perfil = next((p for p in historico.listar_perfis() if p.id == payload.perfil_id), None)
    if perfil is None:
        raise HTTPException(404, "Perfil não encontrado.")
    relato = (payload.ticket or "").strip()
    if payload.ticket_id:
        ticket = next((t for t in historico.listar_tickets() if t.id == payload.ticket_id), None)
        if ticket is None:
            raise HTTPException(404, "Ticket não encontrado.")
        relato = ticket.descricao
    try:
        geracao = criar_geracao(CATALOGOS, historico.pasta_execucoes, PROMPTS)
        saida, caminho = geracao.executar(
            perfil, relato, payload.tipo, payload.versao, sem_cache=payload.sem_cache,
        )
    except (LLMIndisponivel, TimeoutError) as erro:
        raise HTTPException(503, str(erro)) from erro
    except ErroProvedor as erro:
        raise HTTPException(502, str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
    return {"run_id": caminho.stem, "saida": saida, "registro": historico.obter_execucao(caminho.stem)}


@app.get("/api/execucoes/{run_id}")
def obter_execucao(run_id: str):
    try:
        execucao = novo_historico().obter_execucao(run_id)
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
    if execucao is None:
        raise HTTPException(404, "Execução não encontrada.")
    return execucao


class ComparacaoInput(BaseModel):
    run_ids: tuple[str, str]


class NotaInput(BaseModel):
    nota: int = Field(ge=1, le=5, strict=True)
    justificativa: str = Field(min_length=1, max_length=5000)


class AvaliacaoInput(BaseModel):
    avaliador: str = Field(min_length=1, max_length=120)
    notas: dict[str, dict[str, NotaInput]]
    conclusao: str = Field(min_length=1, max_length=12000)


@app.post("/api/comparacoes", status_code=201)
def criar_comparacao(payload: ComparacaoInput):
    try:
        return comparar_execucoes(novo_historico(), *payload.run_ids)
    except LookupError as erro:
        raise HTTPException(404, str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro


@app.get("/api/comparacoes/{comparison_id}")
def obter_comparacao(comparison_id: str):
    try:
        comparacao = novo_historico().obter_comparacao(comparison_id)
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
    if comparacao is None:
        raise HTTPException(404, "Comparação não encontrada.")
    return comparacao


@app.put("/api/comparacoes/{comparison_id}/avaliacao")
def atualizar_avaliacao(comparison_id: str, payload: AvaliacaoInput):
    dados = payload.model_dump()
    try:
        return avaliar_comparacao(novo_historico(), comparison_id, **dados)
    except LookupError as erro:
        raise HTTPException(404, str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
