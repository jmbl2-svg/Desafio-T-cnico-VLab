import argparse
import json
import logging
from pathlib import Path

from backend.adapters.json_storage import JsonStorageAdapter
from backend.adapters.llm_provider import ErroProvedor, orientar as orientar
from backend.application.use_cases import comparar_execucoes
from backend.application.use_cases import montar_prompt as renderizar_prompt
from backend.bootstrap import criar_geracao, diretorio_dados


RAIZ = Path(__file__).resolve().parent.parent
PASTA_CATALOGOS = RAIZ / "database"
PASTA_PROMPTS = RAIZ / "IA" / "prompts"
PASTA_EXECUCOES = diretorio_dados(RAIZ / "data") / "runs"


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


def montar_prompt(perfil, relato, tipo="resolucao", versao="v1"):
    return renderizar_prompt(PASTA_PROMPTS, perfil, relato, tipo, versao)


def salvar_execucao(perfil, relato, saida):
    return criar_armazenamento().salvar_execucao(perfil, relato, saida)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Assistente de suporte técnico")
    parser.add_argument("--sem-cache", action="store_true", help="Forçar geração nova")
    sub = parser.add_subparsers(dest="comando")
    comparar = sub.add_parser("comparar", help="Cria uma comparação entre dois atendimentos")
    comparar.add_argument("primeira")
    comparar.add_argument("segunda")
    args = parser.parse_args()
    if args.comando == "comparar":
        try:
            par = comparar_execucoes(criar_armazenamento(), args.primeira, args.segunda)
        except (LookupError, ValueError) as erro:
            parser.exit(1, f"{erro}\n")
        print(par["comparison_id"])
        return
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

    versao = input("Versão (v1, v2) [v1]: ").strip().lower() or "v1"
    if versao not in ("v1", "v2"):
        print("Versão inválida. Use v1 ou v2.")
        return

    print(f"Cliente: {perfil.nome} | Canal: {perfil.canal}")
    print(f"Relato recebido: {relato}")
    try:
        geracao = criar_geracao(PASTA_CATALOGOS, PASTA_EXECUCOES, PASTA_PROMPTS)
        saida, caminho = geracao.executar(perfil, relato, tipo, versao, sem_cache=args.sem_cache)
    except (ErroProvedor, TimeoutError, ValueError) as erro:
        print(f"Falha na geração: {erro}")
        return
    print(f"Provedor: {geracao.gerador.provedor}")

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