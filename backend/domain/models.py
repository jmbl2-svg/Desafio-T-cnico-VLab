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