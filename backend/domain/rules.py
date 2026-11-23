import hashlib
import json


def chave_execucao(controles):
    texto = json.dumps(controles, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def validar_saida(tipo, saida):
    if not isinstance(saida, dict):
        raise ValueError("A saída precisa ser um objeto.")
    if tipo == "resolucao":
        validar_resolucao(saida)
    elif tipo == "diagnostico":
        validar_diagnostico(saida)
    elif tipo == "perguntas":
        validar_perguntas(saida)
    elif tipo == "fluxo":
        validar_fluxo(saida)
    else:
        raise ValueError(f"Tipo de conteúdo desconhecido: {tipo}")


def validar_resolucao(saida):
    if not isinstance(saida, dict):
        raise ValueError("A resolução precisa ser um objeto.")

    passos = saida.get("passos")
    if not isinstance(passos, list) or not passos:
        raise ValueError("A resolução precisa ter pelo menos um passo.")

    for numero, passo in enumerate(passos, start=1):
        if not isinstance(passo, dict):
            raise ValueError(f"O passo {numero} precisa ser um objeto.")

        ordem = passo.get("ordem")
        if type(ordem) is not int or ordem < 1:
            raise ValueError(f"O passo {numero} precisa ter uma ordem inteira positiva.")

        for campo in ("acao", "sinal_esperado", "se_falhar"):
            valor = passo.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"O passo {numero} precisa preencher '{campo}'.")


def validar_diagnostico(saida):
    for campo in ("hipoteses", "evidencias", "dados_faltantes"):
        itens = saida.get(campo)
        if not isinstance(itens, list) or any(not isinstance(x, str) or not x.strip() for x in itens):
            raise ValueError(f"O diagnóstico precisa de uma lista de textos em '{campo}'.")
    texto = saida.get("conclusao_provavel")
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("O diagnóstico precisa de uma conclusão provável.")


def validar_perguntas(saida):
    itens = saida.get("itens")
    if not isinstance(itens, list) or not itens:
        raise ValueError("A saída precisa ter perguntas.")
    for item in itens:
        if not isinstance(item, dict) or type(item.get("prioridade")) is not int or item["prioridade"] < 1:
            raise ValueError("A prioridade precisa ser um inteiro positivo.")
        for campo in ("pergunta", "decisao_afetada"):
            if not isinstance(item.get(campo), str) or not item[campo].strip():
                raise ValueError(f"A pergunta precisa preencher '{campo}'.")


def validar_fluxo(saida):
    nos = saida.get("nos")
    if not isinstance(nos, list) or not nos or any(
        not isinstance(no, dict) or not isinstance(no.get("id"), str) or not no["id"]
        for no in nos
    ):
        raise ValueError("O fluxo precisa de nós com identificadores válidos.")
    por_id = {no["id"]: no for no in nos}
    inicio = saida.get("inicio")
    if len(por_id) != len(nos) or not isinstance(inicio, str) or inicio not in por_id:
        raise ValueError("O início do fluxo e os identificadores precisam ser válidos.")
    visitados = set()
    pendentes = set()

    def visitar(identificador):
        if identificador in pendentes:
            raise ValueError("O fluxo não pode conter ciclos.")
        if identificador in visitados:
            return
        pendentes.add(identificador)
        no = por_id[identificador]
        destinos = no.get("destinos")
        if isinstance(destinos, dict) and destinos:
            if not isinstance(no.get("condicao"), str) or not no["condicao"].strip():
                raise ValueError("Um nó de decisão precisa de uma condição.")
            for destino in destinos.values():
                if not isinstance(destino, str) or destino not in por_id:
                    raise ValueError("O fluxo aponta para um destino inexistente.")
                visitar(destino)
        elif not isinstance(no.get("acao_terminal"), str) or not no["acao_terminal"].strip():
            raise ValueError("Um nó terminal precisa de uma ação.")
        pendentes.remove(identificador)
        visitados.add(identificador)

    visitar(inicio)
    if visitados != set(por_id):
        raise ValueError("Todos os nós devem ser alcançáveis pelo início.")
    diagrama = saida.get("ascii_diagram")
    if not isinstance(diagrama, str) or not diagrama.strip():
        raise ValueError("O fluxo precisa de um diagrama.")


def validar_par(primeira, segunda):
    if primeira["run_id"] == segunda["run_id"]:
        raise ValueError("Selecione duas execuções distintas.")
    controles = ("perfil", "ticket", "tipo", "provedor", "modelo", "parametros")
    if any(c not in primeira or c not in segunda for c in controles):
        raise ValueError("As duas execuções precisam ter metadados completos.")
    if any(primeira[c] != segunda[c] for c in controles):
        raise ValueError("Mantenha perfil, ticket, tipo, provedor, modelo e parâmetros iguais.")
    if {primeira.get("versao"), segunda.get("versao")} != {"v1", "v2"}:
        raise ValueError("Compare uma execução v1 com uma v2.")


CRITERIOS = ("clarity", "customer_fit", "actionability")


def validar_rubrica(run_ids, avaliador, notas, conclusao):
    if not isinstance(avaliador, str) or not avaliador.strip():
        raise ValueError("Informe o nome de quem avaliou.")
    if not isinstance(conclusao, str) or not conclusao.strip():
        raise ValueError("Informe a conclusão da comparação.")
    if not isinstance(notas, dict) or set(notas) != set(run_ids):
        raise ValueError("Avalie cada uma das duas execuções.")
    for run_id in run_ids:
        itens = notas[run_id]
        if not isinstance(itens, dict) or set(itens) != set(CRITERIOS):
            raise ValueError("Preencha clareza, adequação ao cliente e acionabilidade.")
        for item in itens.values():
            if not isinstance(item, dict) or type(item.get("nota")) is not int or not 1 <= item["nota"] <= 5:
                raise ValueError("Cada nota precisa ser inteira e de 1 a 5.")
            texto = item.get("justificativa")
            if not isinstance(texto, str) or not texto.strip():
                raise ValueError("Cada nota precisa de uma justificativa.")
