#!/usr/bin/env bash
# Cria/atualiza um job do Cloud Run + binding de invoker (+ scheduler quando
# houver cron). Adaptado de etl-index-data.
#
# Uso: deploy-job.sh <job> <task-timeout> <memory> <retries> <args> [schedule]
set -euo pipefail

JOB="${1:?job obrigatorio}"
TIMEOUT="${2:?task-timeout obrigatorio}"
MEMORY="${3:?memory obrigatorio}"
RETRIES="${4:?max-retries obrigatorio}"
ARGS="${5:?args obrigatorio}"
SCHEDULE="${6:-}"

: "${IMAGE_URL:?IMAGE_URL obrigatorio (build da imagem)}"
: "${CLOUD_RUN_REGION:?}"
: "${GCP_PROJECT_ID:?}"
: "${CLOUD_RUN_SERVICE_ACCOUNT_EMAIL:?}"
: "${VPC_HOST_PROJECT_ID:?}"
: "${VPC_CONNECTOR_NAME:?}"

VPC_CONNECTOR="projects/${VPC_HOST_PROJECT_ID}/locations/${CLOUD_RUN_REGION}/connectors/${VPC_CONNECTOR_NAME}"

echo "Deploy Job: ${JOB}"
if gcloud run jobs describe "${JOB}" --region "${CLOUD_RUN_REGION}" --project "${GCP_PROJECT_ID}" > /dev/null 2>&1; then
  gcloud run jobs update "${JOB}" \
    --image "${IMAGE_URL}" \
    --tasks 1 \
    --max-retries "${RETRIES}" \
    --task-timeout="${TIMEOUT}" \
    --cpu 1 \
    --memory "${MEMORY}" \
    --args="${ARGS}" \
    --vpc-connector="${VPC_CONNECTOR}" \
    --service-account="${CLOUD_RUN_SERVICE_ACCOUNT_EMAIL}" \
    --region "${CLOUD_RUN_REGION}" \
    --project "${GCP_PROJECT_ID}" \
    --quiet
else
  gcloud run jobs create "${JOB}" \
    --image "${IMAGE_URL}" \
    --tasks 1 \
    --max-retries "${RETRIES}" \
    --task-timeout="${TIMEOUT}" \
    --cpu 1 \
    --memory "${MEMORY}" \
    --args="${ARGS}" \
    --vpc-connector="${VPC_CONNECTOR}" \
    --service-account="${CLOUD_RUN_SERVICE_ACCOUNT_EMAIL}" \
    --region "${CLOUD_RUN_REGION}" \
    --project "${GCP_PROJECT_ID}" \
    --quiet
fi

gcloud run jobs add-iam-policy-binding "${JOB}" \
  --member="serviceAccount:${CLOUD_RUN_SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/run.invoker" \
  --region="${CLOUD_RUN_REGION}" \
  --project="${GCP_PROJECT_ID}"

if [ -n "${SCHEDULE}" ]; then
  : "${SCHEDULER_TIME_ZONE:?}"
  SCHED="${JOB}-scheduler"
  URL="https://${CLOUD_RUN_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${GCP_PROJECT_ID}/jobs/${JOB}:run"
  echo "Sync Scheduler: ${SCHED} (${SCHEDULE})"
  if gcloud scheduler jobs describe "${SCHED}" --location "${CLOUD_RUN_REGION}" --project "${GCP_PROJECT_ID}" > /dev/null 2>&1; then
    gcloud scheduler jobs update http "${SCHED}" \
      --schedule="${SCHEDULE}" \
      --time-zone="${SCHEDULER_TIME_ZONE}" \
      --uri="${URL}" \
      --http-method=POST \
      --oauth-service-account-email="${CLOUD_RUN_SERVICE_ACCOUNT_EMAIL}" \
      --location="${CLOUD_RUN_REGION}" \
      --project="${GCP_PROJECT_ID}" \
      --quiet
  else
    gcloud scheduler jobs create http "${SCHED}" \
      --schedule="${SCHEDULE}" \
      --time-zone="${SCHEDULER_TIME_ZONE}" \
      --uri="${URL}" \
      --http-method=POST \
      --oauth-service-account-email="${CLOUD_RUN_SERVICE_ACCOUNT_EMAIL}" \
      --location="${CLOUD_RUN_REGION}" \
      --project="${GCP_PROJECT_ID}" \
      --quiet
  fi
fi
