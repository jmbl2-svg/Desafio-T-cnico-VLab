import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backend.domain.models import Execucao, PerfilCliente, Ticket
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

    def buscar_por_chave(self, chave):
        for caminho in sorted(self.pasta_execucoes.glob("*.json")):
            try:
                registro = json.loads(caminho.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(registro, dict) and registro.get("input_key") == chave and not registro.get("cache_hit"):
                return registro
        return None

    def salvar_execucao(
        self, perfil, relato, saida, tipo="resolucao", versao="v1", *,
        provedor="fake", modelo="fake-support-v1", parametros=None, template_hash=None, input_key=None, source_run_id=None,
    ):
        validar_saida(tipo, saida)
        self.pasta_execucoes.mkdir(parents=True, exist_ok=True)

        while True:
            run_id = str(secrets.randbelow(900_000_000_000) + 100_000_000_000)
            caminho = self.pasta_execucoes / f"{run_id}.json"
            registro = Execucao(
                run_id=run_id, timestamp_utc=datetime.now(timezone.utc).isoformat(),
                perfil=perfil.to_dict(), ticket=relato, saida=saida, tipo=tipo, versao=versao,
                provedor=provedor, modelo=modelo, parametros=parametros or {},
                template_hash=template_hash, input_key=input_key,
                cache_hit=source_run_id is not None, source_run_id=source_run_id,
            ).to_dict()

            temporario = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=self.pasta_execucoes,
                    prefix=".execucao-", delete=False,
                ) as arquivo:
                    temporario = Path(arquivo.name)
                    json.dump(registro, arquivo, ensure_ascii=False, indent=2)
                    arquivo.flush()
                    os.fsync(arquivo.fileno())

                # A publicação por link é atômica e preserva o destino em caso de colisão.
                os.link(temporario, caminho)
            except FileExistsError:
                continue
            finally:
                if temporario is not None:
                    temporario.unlink(missing_ok=True)

            return caminho
