from backend.adapters.file_lock import FileLock
from backend.adapters.json_storage import JsonStorageAdapter
from backend.adapters.llm_provider import FakeGeradorLLM
from backend.application.use_cases import GerarRespostaUseCase


def criar_geracao(pasta_catalogos, pasta_execucoes, pasta_prompts):
    historico = JsonStorageAdapter(pasta_catalogos, pasta_execucoes)
    trava = FileLock(historico.pasta_execucoes.parent / "locks")
    return GerarRespostaUseCase(FakeGeradorLLM(), historico, pasta_prompts, trava)
