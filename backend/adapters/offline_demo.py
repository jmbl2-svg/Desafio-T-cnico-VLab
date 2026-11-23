from pathlib import Path
import json


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

PASTA_FIXTURES = Path(__file__).resolve().parents[2] / "IA" / "fixtures"


def gerar_demonstracao(perfil, relato, tipo, versao):
    passo = orientar(perfil)["passos"][0]
    v2 = versao == "v2"
    if tipo == "resolucao":
        if v2:
            passo["sinal_esperado"] += " Se o sinal aparecer, confirme o resultado pelo canal de atendimento."
        return {"passos": [passo]}

    caminho = PASTA_FIXTURES / f"{tipo}_fixture.json"
    saida = json.loads(caminho.read_text(encoding="utf-8"))
    if tipo == "diagnostico":
        saida["evidencias"] = [relato]
        saida["dados_faltantes"] = [passo["acao"]]
        if v2:
            saida["conclusao_provavel"] = "O relato sustenta uma investigação, mas a causa ainda não foi confirmada."
    elif tipo == "perguntas":
        item = saida["itens"][0]
        item["pergunta"] = {
            "leigo": "O que você vê na tela quando o problema acontece?",
            "intermediario": "Em qual etapa e horário a falha ocorreu?",
            "avancado": "Qual registro coincide com a etapa e o horário da falha?",
        }[perfil.nivel]
        item["decisao_afetada"] = passo["acao"]
        if v2:
            item["decisao_afetada"] += " Se esse dado faltar: " + passo["se_falhar"]
    else:
        if v2:
            saida["nos"][0]["condicao"] = passo["sinal_esperado"]
        saida["nos"][1]["acao_terminal"] = passo["acao"]
        saida["nos"][2]["acao_terminal"] = passo["se_falhar"]
        condicao = saida["nos"][0]["condicao"]
        saida["ascii_diagram"] = f"[{condicao}] -> Sim: {passo['acao']} | Não: {passo['se_falhar']}"
    return saida
