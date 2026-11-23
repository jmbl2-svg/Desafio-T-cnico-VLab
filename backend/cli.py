from pathlib import Path

from backend.adapters.json_storage import JsonStorageAdapter


RAIZ = Path(__file__).resolve().parent.parent
PASTA_CATALOGOS = RAIZ / "database"
PASTA_PROMPTS = RAIZ / "IA" / "prompts"
PASTA_EXECUCOES = RAIZ / "data" / "runs"


def criar_armazenamento():
    return JsonStorageAdapter(PASTA_CATALOGOS, PASTA_EXECUCOES)


def carregar_perfis():
    return criar_armazenamento().listar_perfis()


def carregar_tickets():
    return criar_armazenamento().listar_tickets()


def escolher_perfil(perfis):
    print("Perfis disponíveis:")
    for perfil in perfis:
        print(f"- {perfil.id}: {perfil.nome} ({perfil.nivel})")

    perfil_id = input("Digite o ID do cliente: ").strip()

    for perfil in perfis:
        if perfil.id == perfil_id:
            return perfil

    return None


def escolher_relato(tickets):
    print("\nTickets disponíveis:")
    for ticket in tickets:
        print(f"- {ticket.id}: {ticket.titulo}")

    codigo = input("ID do ticket (Enter para escrever um relato): ").strip().lower()
    if not codigo:
        relato = input("Descreva o problema: ").strip()
        if relato:
            return relato
        print("Informe o problema para continuar.")
        return None

    for ticket in tickets:
        if ticket.id == codigo:
            return ticket.descricao

    print("Ticket não encontrado. Use um dos IDs da lista.")
    return None


def montar_prompt(perfil, relato):
    pasta = PASTA_PROMPTS / "v1"
    base = (pasta / "base.txt").read_text(encoding="utf-8")
    estrategia = (pasta / "resolucao.txt").read_text(encoding="utf-8")
    contexto = base.format(
        nome=perfil.nome,
        perfil_id=perfil.id,
        nivel=perfil.nivel,
        estilo=perfil.estilo,
        canal=perfil.canal,
        relato=relato,
    )
    return f"{contexto}\n{estrategia}"


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
    return criar_armazenamento().salvar_execucao(perfil, relato, saida)


def main():
    perfil = escolher_perfil(carregar_perfis())

    if perfil is None:
        print("Perfil não encontrado. Use um dos IDs da lista.")
        return

    relato = escolher_relato(carregar_tickets())
    if relato is None:
        return

    prompt = montar_prompt(perfil, relato)
    print("\nPrompt de resolução (demonstração offline):")
    print(prompt)

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