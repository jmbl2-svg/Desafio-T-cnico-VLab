import argparse
import json
import logging
import sys
from pathlib import Path

from backend.adapters.json_storage import JsonStorageAdapter
from backend.adapters.llm_provider import ErroProvedor, orientar as orientar
from backend.application.use_cases import avaliar_comparacao, comparar_execucoes, exportar_comparacao
from backend.domain.rules import CRITERIOS
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


def _interativo(sem_cache):
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
        saida, caminho = geracao.executar(perfil, relato, tipo, versao, sem_cache=sem_cache)
    except (ErroProvedor, TimeoutError, ValueError) as erro:
        print(f"Falha na geração: {erro}", file=sys.stderr)
        return 1
    print(f"Provedor: {geracao.gerador.provedor}")

    if tipo == "resolucao":
        for passo in saida["passos"]:
            print(f"\nPasso {passo['ordem']}: {passo['acao']}")
            print(f"O que observar: {passo['sinal_esperado']}")
            print(f"Se não funcionar: {passo['se_falhar']}")
    else:
        print(json.dumps(saida, ensure_ascii=False, indent=2))

    print(f"\nAtendimento salvo em: {caminho}")
    return 0



def _argumentos_cenario(parser, tipo=True):
    parser.add_argument("--perfil", required=True, help="Código do perfil, por exemplo 0001")
    entrada = parser.add_mutually_exclusive_group(required=True)
    entrada.add_argument("--ticket-id", help="Código do ticket cadastrado")
    entrada.add_argument("--ticket", help="Relato livre")
    if tipo:
        parser.add_argument("--tipo", choices=("resolucao", "diagnostico", "perguntas", "fluxo"), default="resolucao")
    parser.add_argument("--sem-cache", action="store_true", default=argparse.SUPPRESS)


def _cenario(args, historico):
    perfil = next((p for p in historico.listar_perfis() if p.id == args.perfil), None)
    if perfil is None:
        raise LookupError("Perfil não encontrado.")
    relato = (args.ticket or "").strip()
    if args.ticket_id:
        ticket = next((t for t in historico.listar_tickets() if t.id == args.ticket_id), None)
        if ticket is None:
            raise LookupError("Ticket não encontrado.")
        relato = ticket.descricao
    if not relato:
        raise ValueError("Informe o relato do ticket.")
    return perfil, relato


def _avaliar(historico, comparison_id):
    par = historico.obter_comparacao(comparison_id)
    if par is None:
        raise LookupError("Comparação não encontrada.")
    avaliador = input("Seu nome: ")
    notas = {}
    for run_id in par["run_ids"]:
        registro = historico.obter_execucao(run_id)
        if registro is None:
            raise LookupError("Uma execução vinculada não foi encontrada.")
        print(f"Execução {run_id} ({registro['versao']})")
        print(json.dumps(registro["saida"], ensure_ascii=False, indent=2))
        notas[run_id] = {}
        for criterio in CRITERIOS:
            nota = int(input(f"{criterio}: nota de 1 a 5: "))
            justificativa = input("Justificativa: ")
            notas[run_id][criterio] = {"nota": nota, "justificativa": justificativa}
    conclusao = input("Conclusão comparativa: ")
    return avaliar_comparacao(historico, comparison_id, avaliador, notas, conclusao)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Assistente de suporte técnico")
    parser.add_argument("--sem-cache", action="store_true", help="Força geração nova")
    sub = parser.add_subparsers(dest="comando")
    sub.add_parser("perfis", help="Lista os perfis cadastrados")
    gerar = sub.add_parser("gerar", help="Gera uma resposta")
    _argumentos_cenario(gerar)
    gerar.add_argument("--versao", choices=("v1", "v2"), default="v1")
    comparar = sub.add_parser("comparar", help="Cria um par controlado entre v1 e v2")
    comparar.add_argument("primeira", nargs="?", help="Código da primeira execução existente")
    comparar.add_argument("segunda", nargs="?", help="Código da segunda execução existente")
    comparar.add_argument("--perfil")
    entrada = comparar.add_mutually_exclusive_group()
    entrada.add_argument("--ticket-id")
    entrada.add_argument("--ticket")
    comparar.add_argument("--tipo", choices=("resolucao", "diagnostico", "perguntas", "fluxo"), default="resolucao")
    comparar.add_argument("--versoes", nargs=2, choices=("v1", "v2"), default=("v1", "v2"))
    comparar.add_argument("--sem-cache", action="store_true", default=argparse.SUPPRESS)
    avaliar = sub.add_parser("avaliar", help="Aplica a rubrica da comparação")
    avaliar.add_argument("--comparacao", required=True)
    exportar = sub.add_parser("exportar", help="Exporta os registros da comparação")
    exportar.add_argument("--comparacao", required=True)
    exportar.add_argument("--destino", default="samples")

    args = parser.parse_args()
    if args.comando is None:
        return _interativo(args.sem_cache)
    historico = criar_armazenamento()
    try:
        if args.comando == "perfis":
            for perfil in historico.listar_perfis():
                print(f"{perfil.id} {perfil.nome} ({perfil.nivel}, {perfil.estilo}, {perfil.canal})")
        elif args.comando == "gerar":
            perfil, relato = _cenario(args, historico)
            geracao = criar_geracao(PASTA_CATALOGOS, PASTA_EXECUCOES, PASTA_PROMPTS)
            saida, caminho = geracao.executar(perfil, relato, args.tipo, args.versao, sem_cache=args.sem_cache)
            print(json.dumps({"saida": saida, "arquivo": str(caminho), "run_id": caminho.stem}, ensure_ascii=False, indent=2))
        elif args.comando == "comparar":
            if args.primeira or args.segunda:
                if not (args.primeira and args.segunda) or args.perfil or args.ticket_id or args.ticket:
                    raise ValueError("Informe dois códigos ou defina um cenário para geração.")
                ids = (args.primeira, args.segunda)
            else:
                if not args.perfil or not (args.ticket_id or args.ticket):
                    raise ValueError("Informe --perfil e um ticket para comparar.")
                if set(args.versoes) != {"v1", "v2"}:
                    raise ValueError("Escolha as duas versões distintas, v1 e v2.")
                perfil, relato = _cenario(args, historico)
                geracao = criar_geracao(PASTA_CATALOGOS, PASTA_EXECUCOES, PASTA_PROMPTS)
                ids = tuple(
                    geracao.executar(perfil, relato, args.tipo, v, sem_cache=args.sem_cache)[1].stem
                    for v in args.versoes
                )
            print(comparar_execucoes(historico, *ids)["comparison_id"])
        elif args.comando == "avaliar":
            _avaliar(historico, args.comparacao)
            print("Avaliação registrada.")
        elif args.comando == "exportar":
            total = exportar_comparacao(historico, args.comparacao, args.destino)
            print(f"{total} arquivos exportados.")
    except (ErroProvedor, LookupError, ValueError, TimeoutError) as erro:
        parser.exit(1, f"{erro}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
