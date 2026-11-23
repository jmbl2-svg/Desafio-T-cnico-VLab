#!/bin/sh
set -eu
base="${1:-http://127.0.0.1:8000}"
: "${SMOKE_USER:?Informe a conta de teste já cadastrada}"
: "${SMOKE_PASSWORD:?Informe a senha da conta de teste}"
cookies=$(mktemp)
trap 'rm -f "$cookies"' EXIT HUP INT TERM
curl -fsS "$base/api/saude" >/dev/null
python -c 'import json, os; print(json.dumps({"usuario":os.environ["SMOKE_USER"],"senha":os.environ["SMOKE_PASSWORD"]}))' |
  curl -fsS -c "$cookies" -H 'Content-Type: application/json' --data-binary @- "$base/api/auth/login" >/dev/null
curl -fsS -b "$cookies" "$base/api/perfis" >/dev/null
payload='{"perfil_id":"0001","ticket_id":"pasta"}'
curl -fsS -b "$cookies" -H 'Content-Type: application/json' --data "$payload" "$base/api/execucoes" >/dev/null
curl -fsS -b "$cookies" -H 'Content-Type: application/json' --data "$payload" "$base/api/execucoes" |
  python -c 'import json, sys; assert json.load(sys.stdin)["registro"]["cache_hit"]'
curl -fsS -b "$cookies" -X POST "$base/api/auth/logout" >/dev/null
printf '%s\n' 'Saúde, sessão, catálogo, geração e cache verificados.'
