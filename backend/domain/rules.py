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
