import logging
import io
import json
import os
from contextvars import ContextVar
from hashlib import sha256
from pathlib import Path
from typing import Literal
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, model_validator

from backend.adapters.json_storage import JsonStorageAdapter
from backend.adapters.web_auth import COOKIE_NAME, SESSION_SECONDS, WebAuth
from backend.adapters.llm_provider import ErroProvedor, LLMIndisponivel
from backend.bootstrap import criar_geracao, diretorio_dados
from backend.application.use_cases import arquivos_exportacao, avaliar_comparacao, comparar_execucoes


RAIZ = Path(__file__).resolve().parents[1]
CATALOGOS = RAIZ / "database"
PROMPTS = RAIZ / "IA" / "prompts"
app = FastAPI(title="V-LAB Suporte Técnico")
USUARIO_ATIVO = ContextVar("usuario_ativo", default=None)
PUBLICOS = {"/api/saude", "/api/auth/registro", "/api/auth/login", "/api/auth/sessao"}


def autenticacao():
    pasta = diretorio_dados(RAIZ / "data")
    pasta.mkdir(parents=True, exist_ok=True)
    return WebAuth(str(pasta))


@app.middleware("http")
async def verificar_sessao(request: Request, call_next):
    caminho = request.url.path.rstrip("/")
    if not caminho.startswith("/api/"):
        return await call_next(request)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origem = request.headers.get("origin")
        origens_permitidas = {
            valor.strip().rstrip("/")
            for valor in os.getenv("VLAB_ORIGENS_PUBLICAS", "").split(",")
            if valor.strip()
        } or {str(request.base_url).rstrip("/")}
        if origem and (origem == "null" or origem not in origens_permitidas):
            return JSONResponse({"detail": "Origem da solicitação inválida."}, status_code=403)
    if caminho in PUBLICOS:
        return await call_next(request)
    token = request.cookies.get(COOKIE_NAME)
    usuario = await run_in_threadpool(autenticacao().user_for, token) if token else None
    if usuario is None:
        return JSONResponse({"detail": "Entre para continuar."}, status_code=401)
    escopo = USUARIO_ATIVO.set(usuario)
    try:
        return await call_next(request)
    finally:
        USUARIO_ATIVO.reset(escopo)


@app.exception_handler(RequestValidationError)
async def erro_entrada(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/auth/"):
        return JSONResponse({"detail": "Confira o usuário e a senha."}, status_code=422)
    return JSONResponse({"detail": "Confira os campos informados."}, status_code=422)


class Credenciais(BaseModel):
    usuario: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    senha: str = Field(min_length=10, max_length=128)


@app.post("/api/auth/registro", status_code=201)
def registrar(payload: Credenciais):
    usuario = payload.usuario.lower()
    if not autenticacao().register(usuario, payload.senha):
        raise HTTPException(409, "Esse nome de usuário já está em uso.")
    return {"usuario": usuario}


@app.post("/api/auth/login")
def entrar(payload: Credenciais, request: Request, response: Response):
    usuario = payload.usuario.lower()
    token = autenticacao().login(usuario, payload.senha)
    if token is None:
        raise HTTPException(401, "Usuário ou senha inválidos.")
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
        samesite="strict", secure=request.url.scheme == "https",
    )
    return {"usuario": usuario}


@app.get("/api/auth/sessao")
def sessao(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    return {"usuario": autenticacao().user_for(token) if token else None}


@app.post("/api/auth/logout", status_code=204)
def sair(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    autenticacao().logout(token)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME)
    return response
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
    pasta = diretorio_dados(RAIZ / "data")
    usuario = USUARIO_ATIVO.get()
    if usuario is not None:
        conta = sha256(usuario.encode("utf-8")).hexdigest()
        pasta = pasta / "contas" / conta
    return JsonStorageAdapter(CATALOGOS, pasta / "runs")


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


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def pagina_inicial():
    pagina = (RAIZ / "frontend" / "standalone.html").read_text(encoding="utf-8")
    pasta = RAIZ / "frontend" / "dist"
    if all((pasta / nome).is_file() for nome in ("comparacao.js", "comparacao.css")):
        assets = (
            '<link rel="stylesheet" href="/frontend-assets/comparacao.css">'
            '<script type="module" src="/frontend-assets/comparacao.js"></script>'
        )
        pagina = pagina.replace("<!-- frontend interativo -->", assets)
    return pagina


@app.get("/frontend-assets/{nome}", include_in_schema=False)
def servir_componente(nome: Literal["comparacao.js", "comparacao.css"]):
    caminho = RAIZ / "frontend" / "dist" / nome
    if not caminho.is_file():
        raise HTTPException(404, "Componente não compilado.")
    return FileResponse(caminho)


@app.get("/api/comparacoes/{comparison_id}/exportar")
def baixar_comparacao(comparison_id: str):
    try:
        arquivos = arquivos_exportacao(novo_historico(), comparison_id)
    except LookupError as erro:
        raise HTTPException(404, str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as pacote:
        for nome, dados in arquivos.items():
            pacote.writestr(nome, json.dumps(dados, ensure_ascii=False, indent=2))
    return Response(
        buffer.getvalue(), media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{comparison_id}.zip"'},
    )
