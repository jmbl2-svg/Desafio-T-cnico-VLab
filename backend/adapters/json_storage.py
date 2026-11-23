import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from backend.domain.models import PerfilCliente, Ticket
from backend.domain.rules import validar_saida


class JsonStorageAdapter:
    def __init__(self, pasta_catalogos, pasta_execucoes):
        self.pasta_catalogos = Path(pasta_catalogos)
        self.pasta_execucoes = Path(pasta_execucoes)

    def listar_perfis(self):
        caminho = self.pasta_catalogos / "profiles.json"
        with caminho.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        return [PerfilCliente(**item) for item in dados]

    def listar_tickets(self):
        caminho = self.pasta_catalogos / "tickets.json"
        with caminho.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        return [Ticket(**item) for item in dados]

    def salvar_execucao(self, perfil, relato, saida, tipo="resolucao", versao="v1"):
        validar_saida(tipo, saida)
        self.pasta_execucoes.mkdir(parents=True, exist_ok=True)

        while True:
            run_id = str(secrets.randbelow(900_000_000_000) + 100_000_000_000)
            caminho = self.pasta_execucoes / f"{run_id}.json"
            registro = {
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "perfil": perfil.to_dict(),
                "ticket": relato,
                "tipo": tipo,
                "versao": versao,
                "saida": saida,
            }
            try:
                with caminho.open("x", encoding="utf-8") as arquivo:
                    json.dump(registro, arquivo, ensure_ascii=False, indent=2)
            except FileExistsError:
                continue

            return caminho
