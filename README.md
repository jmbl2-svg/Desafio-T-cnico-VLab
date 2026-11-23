# Assistente de Suporte Técnico V-LAB

Projeto de Jonas para o desafio de engenharia de prompt. A aplicação trabalha
com cinco perfis e gera resolução, diagnóstico, perguntas e fluxo de decisão
a partir de um ticket. A CLI e a aplicação web compartilham o núcleo Python.

## Instalação no Windows

Use Python 3.11 ou 3.12. No PowerShell, na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

O arquivo local inicia em modo `fake`, sem rede. A saída offline demonstra
os formatos e varia com o perfil e a versão. Para usar a API Gemini, configure
`LLM_PROVIDER=gemini` e sua chave em `LLM_API_KEY` no `.env`. A ordem padrão é
`gemini-4-hydrogen`, `gemini-3.8-flash`, `gemini-3.6-flash`.
O modelo efetivo fica no JSON e os logs registram as tentativas.
Também é possível configurar `LLM_PROVIDER=openai`.

## Terminal

Use o Python da venv. O primeiro comando abre o menu interativo.

```powershell
.\.venv\Scripts\python.exe -m backend.cli
.\.venv\Scripts\python.exe -m backend.cli perfis
.\.venv\Scripts\python.exe -m backend.cli gerar --perfil 0001 --ticket-id pasta --tipo resolucao --versao v1
.\.venv\Scripts\python.exe -m backend.cli comparar --perfil 0001 --ticket-id pasta --tipo resolucao --sem-cache
.\.venv\Scripts\python.exe -m backend.cli avaliar --comparacao ID_DA_COMPARACAO
.\.venv\Scripts\python.exe -m backend.cli exportar --comparacao ID_DA_COMPARACAO --destino samples
```

A comparação preserva perfil, ticket, tipo, provedor, modelo efetivo e parâmetros.
Troque `ID_DA_COMPARACAO` pelo ID exibido. Os perfis usam `0001` a `0005`;
cada atendimento recebe um código de 12 dígitos.

## Web

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Abra [a aplicação local](http://127.0.0.1:8000/). Crie uma conta, escolha o cenário,
compare as duas versões, salve a rubrica e baixe o ZIP. As contas da web têm
históricos separados. O terminal usa o histórico local da CLI. Use o seletor
de tema no topo da página. A documentação da API fica em
[`/docs`](http://127.0.0.1:8000/docs).

## Testes e Docker

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend
docker compose build
docker compose up -d
```

O Compose preserva dados em um volume. Para o smoke test, em Bash ou WSL,
configure `SMOKE_USER` e `SMOKE_PASSWORD` e rode `sh smoke.sh http://127.0.0.1:8000`.

## Organização

- `backend/domain` contém modelos e regras. `backend/application` contém os casos de uso.
- `backend/adapters` contém JSON, provedores, sessão e trava de arquivo.
- `IA` guarda prompts, contratos e fixtures. `database` guarda catálogos e esquemas.
- `frontend/standalone.html` contém a interface servida pelo FastAPI.
