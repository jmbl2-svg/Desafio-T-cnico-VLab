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
class RespostaModelo:
    saida: dict
    modelo: str


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
    input_key: str | None = None
    cache_hit: bool = False
    source_run_id: str | None = None

    def to_dict(self):
        return asdict(self)


@dataclass
class Comparacao:
    comparison_id: str
    run_ids: list[str]
    criada_em: str
    status: str = "pendente"
    avaliacao: dict | None = None

    def to_dict(self):
        return asdict(self)
