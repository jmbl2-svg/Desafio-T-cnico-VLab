import os
import time
from contextlib import contextmanager
from pathlib import Path


class FileLock:
    def __init__(self, pasta, timeout=45):
        self.pasta = Path(pasta)
        self.timeout = timeout

    @contextmanager
    def adquirir(self, chave):
        if len(chave) != 64 or any(c not in "0123456789abcdef" for c in chave):
            raise ValueError("Chave de trava inválida.")
        self.pasta.mkdir(parents=True, exist_ok=True)
        caminho = self.pasta / f"{chave}.lock"
        limite = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError as erro:
                if time.monotonic() >= limite:
                    raise TimeoutError("Uma geração equivalente ainda está em andamento.") from erro
                time.sleep(0.05)
        try:
            os.close(fd)
            yield
        finally:
            caminho.unlink(missing_ok=True)
