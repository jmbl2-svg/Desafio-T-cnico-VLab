import ast
from pathlib import Path


def test_dominio_independe_de_infraestrutura():
    pasta = Path(__file__).resolve().parents[1] / "domain"
    proibidos = ("backend.adapters", "backend.application", "fastapi", "httpx")
    for caminho in pasta.glob("*.py"):
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                modulos = [alias.name for alias in no.names]
            elif isinstance(no, ast.ImportFrom):
                modulos = [no.module or ""]
            else:
                continue
            assert not any(modulo.startswith(proibidos) for modulo in modulos)
