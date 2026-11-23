def validar_saida(tipo, saida):
    if not isinstance(saida, dict):
        raise ValueError("A saída precisa ser um objeto.")
    if tipo == "resolucao":
        validar_resolucao(saida)
    elif tipo == "diagnostico":
        validar_diagnostico(saida)
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
