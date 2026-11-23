# Evolução dos registros

Os catálogos ficam em `database/`. As execuções e comparações ficam no diretório
`DATA_DIR`; a API separa os registros por conta. Preserve IDs como texto.
As execuções antigas podem ser abertas pelo código numérico. Uma comparação
nova exige registros com versão, provedor, modelo e parâmetros completos.
Acrescente campos compatíveis e conserve o histórico original ao evoluir o formato.
