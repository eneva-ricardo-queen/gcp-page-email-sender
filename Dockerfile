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

# Credenciais fornecidas via BuildKit secret, env (ARG) ou gcloud local.
# No CI o token vem via --build-arg GCLOUD_TOKEN=$(gcloud auth print-access-token).
ARG GCLOUD_TOKEN=""
ENV GCLOUD_TOKEN=${GCLOUD_TOKEN}

RUN if [ -f /run/secrets/gcloud-key ]; then \
      gcloud auth login --cred-file=/run/secrets/gcloud-key --quiet && \
      gcloud config set project eva-prj-prd-preco-gas-gnl-s9 --quiet; \
    fi && \
    export GCLOUD_TOKEN="${GCLOUD_TOKEN:-$(gcloud auth print-access-token 2>/dev/null || true)}" && \
    pip install \
      --extra-index-url "https://oauth2accesstoken:${GCLOUD_TOKEN}@us-central1-python.pkg.dev/eva-prj-prd-preco-gas-gnl-s9/repo-artefatos-imagens-py-lib-custom/simple/" \
      --no-cache-dir -r requirements.txt


# --- Estágio 2: imagem final (Playwright; chromium pré-instalado) ---
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app
COPY . .

ENV PYTHONPATH=/app
ENTRYPOINT ["python", "src/main.py"]