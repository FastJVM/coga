#!/usr/bin/env bash
#
# Deploy the Coga telemetry relay (Cloud Functions gen2) and lock down its
# request logs so the client IP is never persisted.
#
# Idempotent: re-running redeploys the function in place and re-applies the same
# log-exclusion filter. The only owner inputs are the GCP project/region and the
# internal Slack webhook (held as a Secret Manager secret, never in the client).
#
# Usage:
#   PROJECT_ID=my-proj REGION=us-central1 \
#   SLACK_WEBHOOK_URL='https://hooks.slack.com/services/XXX' \
#     ./deploy.sh
#
# On success it prints the function URL — paste that into the client's
# `TELEMETRY_URL` constant in `src/coga/telemetry.py` (or set
# `COGA_TELEMETRY_URL` to point a checkout at a test relay).

set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID to your GCP project}"
: "${REGION:=us-central1}"
: "${SLACK_WEBHOOK_URL:?set SLACK_WEBHOOK_URL to the internal Slack incoming webhook}"

FUNCTION_NAME="${FUNCTION_NAME:-coga-telemetry}"
SECRET_NAME="${SECRET_NAME:-coga-telemetry-slack-webhook}"
RUNTIME="${RUNTIME:-python312}"
ENTRY_POINT="telemetry"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Project: ${PROJECT_ID}  Region: ${REGION}  Function: ${FUNCTION_NAME}"

# 1. Store the Slack webhook as a Secret Manager secret (create-or-add-version).
#    The function reads it as an env var at runtime; it is never in the client.
if ! gcloud secrets describe "${SECRET_NAME}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "==> Creating secret ${SECRET_NAME}"
  gcloud secrets create "${SECRET_NAME}" \
    --project "${PROJECT_ID}" \
    --replication-policy="automatic"
fi
echo "==> Adding webhook secret version"
printf '%s' "${SLACK_WEBHOOK_URL}" | gcloud secrets versions add "${SECRET_NAME}" \
  --project "${PROJECT_ID}" \
  --data-file=-

# 2. Deploy the gen2 HTTP function. `--allow-unauthenticated` because anonymous
#    installs POST without credentials. The webhook is injected from the secret
#    as the SLACK_WEBHOOK_URL env var.
echo "==> Deploying function"
gcloud functions deploy "${FUNCTION_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --gen2 \
  --runtime "${RUNTIME}" \
  --source "${SOURCE_DIR}" \
  --entry-point "${ENTRY_POINT}" \
  --trigger-http \
  --allow-unauthenticated \
  --set-secrets "SLACK_WEBHOOK_URL=${SECRET_NAME}:latest"

# 3. Drop the client IP at the edge. Cloud Functions request access logs
#    include httpRequest.remoteIp by default; a project-level Cloud Logging
#    exclusion on this function's run.googleapis.com requests stops that field
#    (and the rest of the request log) from being persisted. This is the
#    load-bearing no-PII control — keep it in sync with the no-IP handler.
EXCLUSION_NAME="${EXCLUSION_NAME:-coga-telemetry-drop-ip}"
EXCLUSION_FILTER="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${FUNCTION_NAME}\" AND logName:\"requests\""
echo "==> Applying Cloud Logging exclusion ${EXCLUSION_NAME} (drops request logs incl. remoteIp)"
if gcloud logging sinks describe _Default --project "${PROJECT_ID}" >/dev/null 2>&1; then
  if gcloud logging sinks describe _Default --project "${PROJECT_ID}" \
       --format="value(exclusions.name)" 2>/dev/null | grep -qw "${EXCLUSION_NAME}"; then
    echo "    (updating existing exclusion)"
    gcloud logging sinks update _Default \
      --project "${PROJECT_ID}" \
      --update-exclusion="name=${EXCLUSION_NAME},filter=${EXCLUSION_FILTER}"
  else
    echo "    (adding exclusion)"
    gcloud logging sinks update _Default \
      --project "${PROJECT_ID}" \
      --add-exclusion="name=${EXCLUSION_NAME},filter=${EXCLUSION_FILTER}"
  fi
fi

# 4. Print the URL to pin into the client.
URL="$(gcloud functions describe "${FUNCTION_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --gen2 \
  --format='value(serviceConfig.uri)')"
echo ""
echo "==> Deployed. Function URL:"
echo "    ${URL}"
echo ""
echo "Pin this into TELEMETRY_URL in src/coga/telemetry.py (or export"
echo "COGA_TELEMETRY_URL=${URL} to point a single checkout at it)."
