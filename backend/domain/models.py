from dataclasses import asdict, dataclass


@dataclass
class PerfilCliente:
    id: str
    nome: str
    nivel: str
    estilo: str
    canal: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Ticket:
    id: str
    titulo: str
    descricao: str

@dataclass
class Execucao:
    run_id: str
    timestamp_utc: str
    perfil: dict
    ticket: str
    saida: dict
    tipo: str
    versao: str
    provedor: str
    modelo: str
    parametros: dict
    template_hash: str | None

    def to_dict(self):
        return asdict(self)
