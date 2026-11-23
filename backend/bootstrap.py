import os
from pathlib import Path

from dotenv import load_dotenv

from backend.adapters.file_lock import FileLock
from backend.adapters.json_storage import JsonStorageAdapter
from backend.adapters.llm_provider import ErroProvedor, FakeGeradorLLM, GeminiFallback, GeminiGeradorLLM
from backend.application.use_cases import GerarRespostaUseCase


def diretorio_dados(padrao):
    load_dotenv()
    return Path(os.getenv("DATA_DIR") or padrao)


def criar_provedor():
    load_dotenv()
    provedor = os.getenv("LLM_PROVIDER", "fake").strip().lower()
    if provedor == "fake":
        return FakeGeradorLLM()
    if provedor == "gemini":
        principal = os.getenv("LLM_MODEL") or "gemini-4-hydrogen"
        alternativas = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.8-flash,gemini-3.6-flash")
        modelos = dict.fromkeys([principal, *(m.strip() for m in alternativas.split(",") if m.strip())])
        return GeminiFallback(
            GeminiGeradorLLM(
                os.getenv("LLM_API_KEY"), modelo,
                float(os.getenv("LLM_TIMEOUT_SECONDS", "12")), os.getenv("LLM_BASE_URL"),
            )
            for modelo in modelos
        )
    raise ErroProvedor("Provedor desconhecido. Use fake ou gemini.")


def criar_geracao(pasta_catalogos, pasta_execucoes, pasta_prompts):
    historico = JsonStorageAdapter(pasta_catalogos, pasta_execucoes)
    trava = FileLock(historico.pasta_execucoes.parent / "locks")
    return GerarRespostaUseCase(criar_provedor(), historico, pasta_prompts, trava)
