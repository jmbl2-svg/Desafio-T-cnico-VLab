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

    acao, sinal, motivo = verificacoes[perfil["nivel"]]
    alternativa = retornos[perfil["canal"]]

    if perfil["estilo"] == "didatico":
        acao = f"{acao} Por que fazer isso? {motivo}"
    elif perfil["estilo"] == "detalhado":
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
    saida = orientar(perfil)

    for passo in saida["passos"]:
        print(f"\nPasso {passo['ordem']}: {passo['acao']}")
        print(f"O que observar: {passo['sinal_esperado']}")
        print(f"Se não funcionar: {passo['se_falhar']}")


if __name__ == "__main__":
    main()