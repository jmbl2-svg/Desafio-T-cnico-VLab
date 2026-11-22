import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from backend.domain.models import PerfilCliente, Ticket


RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_PERFIS = RAIZ / "database" / "profiles.json"
ARQUIVO_TICKETS = RAIZ / "database" / "tickets.json"
PASTA_EXECUCOES = RAIZ / "data" / "runs"


def carregar_perfis():
    with ARQUIVO_PERFIS.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    return [PerfilCliente(**item) for item in dados]


def escolher_perfil(perfis):
    print("Perfis disponíveis:")
    for perfil in perfis:
        print(f"- {perfil.id}: {perfil.nome} ({perfil.nivel})")

    perfil_id = input("Digite o ID do cliente: ").strip()

    for perfil in perfis:
        if perfil.id == perfil_id:
            return perfil

    return None


def orientar(perfil):
    verificacoes = {
        "leigo": (
            "Volte à tela onde o problema apareceu e observe o que acontece.",
            "Você consegue dizer se o problema apareceu de novo.",
            "Isso ajuda a descobrir em qual tela o problema começa.",
        ),
        "intermediario": (
            "Anote a etapa, o horário e a mensagem exibida, se houver.",
            "Você consegue indicar em qual etapa a falha ocorreu.",
            "Esses dados ajudam a identificar se o problema se repete.",
        ),
        "avancado": (
            "Correlacione o horário da falha com o registro disponível.",
            "Você identifica um evento que coincide com a ocorrência relatada.",
            "A comparação ajuda a localizar a etapa em que o processo falhou.",
        ),
    }

    retornos = {
        "chat": "Conte aqui no chat o que apareceu na tela.",
        "email": "Responda ao e-mail com a etapa e o horário observados.",
        "telefone": "Descreva em voz alta o último estado que conseguiu confirmar.",
    }

    acao, sinal, motivo = verificacoes[perfil.nivel]
    alternativa = retornos[perfil.canal]

    if perfil.estilo == "didatico":
        acao = f"{acao} Por que fazer isso? {motivo}"
    elif perfil.estilo == "detalhado":
        sinal = f"{sinal} Registre também o que aconteceu imediatamente antes."

    return {
        "passos": [
            {
                "ordem": 1,
                "acao": acao,
                "sinal_esperado": sinal,
                "se_falhar": alternativa,
            }
        ]
    }


def salvar_execucao(perfil, relato, saida):
    PASTA_EXECUCOES.mkdir(parents=True, exist_ok=True)

    while True:
        run_id = str(secrets.randbelow(900_000_000_000) + 100_000_000_000)
        caminho = PASTA_EXECUCOES / f"{run_id}.json"
        registro = {
            "run_id": run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "perfil": perfil.to_dict(),
            "ticket": relato,
            "saida": saida,
        }

        try:
            with caminho.open("x", encoding="utf-8") as arquivo:
                json.dump(registro, arquivo, ensure_ascii=False, indent=2)
        except FileExistsError:
            continue

        return caminho
def carregar_tickets():
    with ARQUIVO_TICKETS.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    return [Ticket(**item) for item in dados]


def escolher_relato(tickets):
    print("\nTickets disponíveis:")
    for ticket in tickets:
        print(f"- {ticket.id}: {ticket.titulo}")

    ticket_id = input(
        "Digite o ID do ticket ou pressione Enter para escrever um relato: "
    ).strip().lower()

    if not ticket_id:
        relato = input("Descreva o problema: ").strip()
        if not relato:
            print("Informe o problema para continuar.")
            return None
        return relato

    for ticket in tickets:
        if ticket.id == ticket_id:
            return ticket.descricao

    print("Ticket não encontrado. Use um dos IDs da lista.")
    return None

def main():
    perfil = escolher_perfil(carregar_perfis())

    if perfil is None:
        print("Perfil não encontrado. Use um dos IDs da lista.")
        return

    relato = input("Descreva o problema: ").strip()

    if not relato:
        print("Informe o problema para continuar.")
        return

    print(f"Cliente: {perfil.nome} | Canal: {perfil.canal}")
    print(f"Relato recebido: {relato}")
    saida = orientar(perfil)

    for passo in saida["passos"]:
        print(f"\nPasso {passo['ordem']}: {passo['acao']}")
        print(f"O que observar: {passo['sinal_esperado']}")
        print(f"Se não funcionar: {passo['se_falhar']}")

    caminho = salvar_execucao(perfil, relato, saida)
    print(f"\nAtendimento salvo em: {caminho}")


if __name__ == "__main__":
    main()