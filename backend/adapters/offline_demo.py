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


def _relato_de_pasta_compartilhada(relato):
    relato = relato.casefold()
    return "arquivo" in relato and "pasta compartilhada" in relato and any(
        termo in relato for termo in ("envio", "enviado", "mandei")
    )


def _resolucao_pasta_v1(perfil, relato):
    verificacao, sinal, detalhe = {
        "leigo": (
            "Procure o nome do arquivo na lista de arquivos enviados.",
            "O nome do arquivo aparece como enviado.",
            "Confirme o nome exato para evitar procurar outro arquivo.",
        ),
        "intermediario": (
            "Confira o status do envio e o caminho de destino do arquivo.",
            "O envio consta como concluído e o destino está identificado.",
            "Anote o caminho completo e o horário do envio.",
        ),
        "avancado": (
            "Confira, se disponível, o registro de sincronização e a conta associada ao destino.",
            "Há um evento de envio concluído vinculado à conta e à pasta.",
            "Correlacione o evento pelo horário, nome do arquivo e caminho.",
        ),
    }[perfil.nivel]
    tentativa = {
        "chat": "Informe no chat o nome do arquivo e o status que aparece.",
        "email": "Responda por e-mail com o nome, o horário e o status que encontrou.",
        "telefone": "Leia o nome do arquivo e o status durante o atendimento.",
    }[perfil.canal]
    if perfil.estilo == "didatico":
        verificacao += " Isso ajuda a separar um envio pendente de um problema de acesso."
    elif perfil.estilo == "detalhado":
        verificacao += " " + detalhe

    acao_destino = {
        "leigo": "Peça à colega para abrir a mesma pasta e procurar pelo nome exato do arquivo.",
        "intermediario": "Compare o caminho de destino com o caminho que a colega está consultando.",
        "avancado": "Confirme o destino e verifique se a colega tem permissão de leitura nessa pasta.",
    }[perfil.nivel]
    sinal_destino = "A colega está na pasta correta e consegue localizar e abrir o arquivo."
    contingencia = (
        "Se o destino for o mesmo e o arquivo continuar ausente, confirme qual conta a "
        "colega usou e peça ao responsável pela pasta para verificar o acesso."
    )
    if "colega" not in relato.casefold():
        acao_destino = "Abra a pasta de destino com a conta usada no envio e procure o nome exato do arquivo."
        sinal_destino = "O arquivo aparece na pasta de destino e pode ser aberto."
        contingencia = "Se o arquivo continuar ausente, informe o status e peça uma verificação de sincronização."
    if "já conferi a pasta de destino" in relato.casefold():
        verificacao = {
            "leigo": "Com a pasta já conferida, procure o nome do arquivo na lista de enviados.",
            "intermediario": "Com o destino já conferido, verifique o status atual da sincronização.",
            "avancado": "Com o destino já conferido, correlacione o envio com o registro da sincronização.",
        }[perfil.nivel]
        sinal = "O registro indica se a sincronização terminou ou ainda está pendente."
        acao_destino = "Confirme se a conta usada no envio tem acesso à pasta e procure o arquivo pelo nome."
        contingencia = "Se o acesso estiver correto, informe o horário e o status para investigar a sincronização."

    passos = [
        {"ordem": 1, "acao": verificacao, "sinal_esperado": sinal,
         "se_falhar": "Se o envio estiver pendente ou não houver registro, " + tentativa[0].lower() + tentativa[1:]},
        {"ordem": 2, "acao": acao_destino, "sinal_esperado": sinal_destino,
         "se_falhar": contingencia},
    ]
    return {"passos": passos}


def _resolucao_pasta_v2(perfil, relato):
    contexto = relato.casefold()
    conferiu = "já conferi a pasta de destino" in contexto
    tem_colega = "colega" in contexto
    checagem = {
        "leigo": "Veja se o envio ainda está pendente ou já terminou.",
        "intermediario": "Separe envio pendente de envio concluído pelo status no histórico.",
        "avancado": "Se houver registro de sincronização, confirme se o envio terminou ou falhou.",
    }[perfil.nivel]
    if perfil.estilo == "didatico":
        checagem += " Isso indica se vale investigar a pasta ou o próprio envio."
    elif perfil.estilo == "detalhado":
        checagem += " Use o horário do envio para identificar o registro."
    canal = {
        "chat": "no chat", "email": "por e-mail", "telefone": "durante a ligação",
    }[perfil.canal]
    if conferiu:
        acao_acesso = "Como o destino já foi conferido, verifique o acesso com a conta que precisa abrir o arquivo."
    elif tem_colega:
        acao_acesso = "Peça à colega para abrir a mesma pasta e confirmar a conta em uso."
    else:
        acao_acesso = "Abra a pasta de destino com a conta usada no envio."
    return {"passos": [
        {
            "ordem": 1, "acao": checagem,
            "sinal_esperado": "Se estiver pendente, acompanhe a sincronização. Vá ao passo 2 só se o envio estiver concluído.",
            "se_falhar": f"Se não houver status disponível ou aparecer erro, informe {canal} o horário e a mensagem exibida.",
        },
        {
            "ordem": 2, "acao": acao_acesso,
            "sinal_esperado": "Se a pasta abrir, procure o arquivo pelo nome no passo 3.",
            "se_falhar": f"Se o acesso for negado, informe {canal} qual pasta e qual conta foram usadas e peça ao responsável para conferir a permissão.",
        },
        {
            "ordem": 3, "acao": f"Tente abrir o arquivo e confirme o resultado {canal}.",
            "sinal_esperado": "Se abrir na pasta esperada, encerre o atendimento.",
            "se_falhar": "Se a pasta abre, mas o arquivo continua ausente, encaminhe nome, horário do envio e status para investigar a sincronização antes de reenviar.",
        },
    ]}


def gerar_demonstracao(perfil, relato, tipo, versao):
    passo = orientar(perfil)["passos"][0]
    v2 = versao == "v2"
    if tipo == "resolucao":
        if _relato_de_pasta_compartilhada(relato):
            if v2:
                return _resolucao_pasta_v2(perfil, relato)
            return _resolucao_pasta_v1(perfil, relato)
        if v2:
            passo["sinal_esperado"] += " Se a falha se repetir, registre a mensagem exata e a etapa em que apareceu."
            return {"passos": [passo, {
                "ordem": 2,
                "acao": "Confira se a mesma ação pode ser concluída sem repetir uma operação irreversível.",
                "sinal_esperado": "A ação pode ser concluída. Se confirmado, informe o resultado no canal de atendimento.",
                "se_falhar": "Encaminhe a etapa e o sinal observado para a equipe de suporte.",
            }]}
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
