# gcp-page-email-sender

Job genérico que renderiza páginas Streamlit (headless, via Playwright) e envia por e-mail (Microsoft Graph API). Começa com RDO Futura; extensível a outras páginas via `tasks.yml`.

## Uso local

### 1. Graph (auth + sendMail) — testado OK
```bash
# Usar o venv do gcp-pep-dashboard (tem gcp-lib, msal, requests)
source .venv/bin/activate
PYTHONPATH=/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-page-email-sender/src python /home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-page-email-sender/scripts/test_graph.py
```
Credenciais via Secret Manager (ADC/gcloud). O teste envia um e-mail de teste para o próprio remetente.

### 2. Render (Playwright) — requer chromium
```bash
# Opção A: instalar chromium (requer deps de sistema)
playwright install chromium
python src/main.py --task rdo-futura

# Opção B: usar imagem Docker (recomendado)
docker build -t gcp-page-email-sender:local -f Dockerfile .
docker run --rm -e prod_RDO_URL=... gcp-page-email-sender:local --task rdo-futura
```
Sem chromium local, o render falha com mensagem clara.

## Deploy
```bash
docker build -t gcp-page-email-sender:local -f Dockerfile .
# Cloud Run Job + Cloud Scheduler (ver PLANO-RDO-EMAIL.md em analise-futura)
```

## Adicionar nova tarefa
Editar `tasks.yml` e criar os secrets correspondentes. Adicionar um Cloud Scheduler por tarefa chamando `--task <id>`.
PLANEOF
