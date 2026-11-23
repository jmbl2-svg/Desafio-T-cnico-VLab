# Notas de engenharia de prompt

## Estratégias

A base define persona, nível, estilo, canal e limites. As estratégias pedem
diagnóstico, resolução, perguntas de esclarecimento e fluxo de decisão.
Cada estratégia tem regras para validar a estrutura da saída.

## Variável do teste

Em resolução, mantenha o perfil e o ticket iguais. A v2 acrescenta uma instrução
para ligar o sinal observável à próxima ação e oferecer uma contingência.
Na simulação, o sinal da v1 termina com uma descrição e a v2 acrescenta a
confirmação pelo canal. A simulação serve para demonstrar o fluxo da rubrica.

## Protocolo para a evidência real

1. Configure um modelo acessível e gere v1 e v2 com `--sem-cache`.
2. Confira se o modelo efetivo e os parâmetros são equivalentes.
3. Atribua 1 a 5 em clareza, adequação ao cliente e acionabilidade.
4. Justifique cada nota com trechos concretos e relate limitações.
5. Exporte o par concluído junto com as duas execuções.

A amostra deste repositório usa provedor simulado e rubrica ilustrativa.
