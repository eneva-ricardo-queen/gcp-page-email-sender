# gcp-page-email-sender

Job genérico que renderiza páginas Streamlit (headless, via Playwright) e envia por e-mail (Microsoft Graph API). Começa com RDO Futura; extensível a outras páginas via `tasks.yml`.

## Uso local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# .env.local com secrets (prod_RDO_URL, prod_RDO_SENDER, prod_RDO_RECIPIENTS,
# prod_GRAPH_TENANT_ID, prod_GRAPH_CLIENT_ID, prod_GRAPH_CLIENT_SECRET)
python src/main.py --task rdo-futura
```

## Deploy
```bash
docker build -t gcp-page-email-sender:local -f Dockerfile .
# Cloud Run Job + Cloud Scheduler (ver PLANO-RDO-EMAIL.md em analise-futura)
```

## Adicionar nova tarefa
Editar `tasks.yml` e criar os secrets correspondentes. Adicionar um Cloud Scheduler por tarefa chamando `--task <id>`.
PLANEOF
