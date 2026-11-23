import json
from pathlib import Path

from backend.adapters.json_storage import JsonStorageAdapter
from backend.adapters.llm_provider import orientar as orientar
from backend.application.use_cases import montar_prompt as renderizar_prompt
from backend.bootstrap import criar_geracao


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


def montar_prompt(perfil, relato, tipo="resolucao"):
    return renderizar_prompt(PASTA_PROMPTS, perfil, relato, tipo)


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

    tipo = input("Tipo (resolucao, diagnostico, perguntas, fluxo) [resolucao]: ").strip().lower() or "resolucao"
    if tipo not in ("resolucao", "diagnostico", "perguntas", "fluxo"):
        print("Tipo de conteúdo inválido.")
        return

    prompt = montar_prompt(perfil, relato, tipo)
    print("\nPrompt (demonstração offline):")
    print(prompt)

    print(f"Cliente: {perfil.nome} | Canal: {perfil.canal}")
    print(f"Relato recebido: {relato}")
    geracao = criar_geracao(PASTA_CATALOGOS, PASTA_EXECUCOES, PASTA_PROMPTS)
    saida, caminho = geracao.executar(perfil, relato, tipo)

    if tipo == "resolucao":
        for passo in saida["passos"]:
            print(f"\nPasso {passo['ordem']}: {passo['acao']}")
            print(f"O que observar: {passo['sinal_esperado']}")
            print(f"Se não funcionar: {passo['se_falhar']}")
    else:
        print(json.dumps(saida, ensure_ascii=False, indent=2))

    print(f"\nAtendimento salvo em: {caminho}")


if __name__ == "__main__":
    main()