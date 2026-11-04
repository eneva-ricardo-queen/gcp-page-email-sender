# --- Estágio 1: construtor de dependências ---
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble AS builder

# Instala o gcloud CLI (para autenticar no repositório privado de wheels)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates python3.12-venv \
    && curl -sO https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-479.0.0-linux-x86_64.tar.gz \
    && tar xzf google-cloud-cli-479.0.0-linux-x86_64.tar.gz \
    && rm google-cloud-cli-479.0.0-linux-x86_64.tar.gz \
    && ./google-cloud-sdk/install.sh --quiet --usage-reporting=false --path-update=false \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
ENV PATH="/google-cloud-sdk/bin:${PATH}"

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app
COPY requirements.txt .

# Argumento que recebe o CONTEÚDO do arquivo de credenciais (injetado pelo Actions)
ARG GCLOUD_KEY_CONTENT

RUN echo "${GCLOUD_KEY_CONTENT}" > /tmp/gcloud-key.json && \
    gcloud auth login --cred-file=/tmp/gcloud-key.json --quiet && \
    gcloud config set project eva-prj-prd-preco-gas-gnl-s9 --quiet && \
    export GCLOUD_TOKEN=$(gcloud auth print-access-token) && \
    pip install \
      --extra-index-url "https://oauth2accesstoken:${GCLOUD_TOKEN}@us-central1-python.pkg.dev/eva-prj-prd-preco-gas-gnl-s9/repo-artefatos-imagens-py-lib-custom/simple/" \
      --no-cache-dir -r requirements.txt && \
    rm /tmp/gcloud-key.json


# --- Estágio 2: imagem final (Playwright; chromium pré-instalado) ---
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app
COPY . .

ENV PYTHONPATH=/app
ENTRYPOINT ["python", "src/main.py"]