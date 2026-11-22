import json
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_PERFIS = RAIZ / "database" / "profiles.json"


def carregar_perfis():
    with ARQUIVO_PERFIS.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def escolher_perfil(perfis):
    print("Perfis disponíveis:")
    for perfil in perfis:
        print(f"- {perfil['id']}: {perfil['nome']} ({perfil['nivel']})")

    perfil_id = input("Digite o ID do cliente: ").strip().lower()

    for perfil in perfis:
        if perfil["id"] == perfil_id:
            return perfil

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

    print(f"Cliente: {perfil['nome']} | Canal: {perfil['canal']}")
    print(f"Relato recebido: {relato}")
    print("Orientação inicial: confira se o arquivo aparece na lista de enviados.")


if __name__ == "__main__":
    main()