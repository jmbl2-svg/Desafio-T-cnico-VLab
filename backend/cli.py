def main():
    relato = input("Descreva o problema: ").strip()

    if not relato:
        print("Informe o problema para continuar.")
        return

    print(f"Relato registrado: {relato}")
    print("Orientação inicial: confira se o arquivo aparece na lista de enviados.")


if __name__ == "__main__":
    main()