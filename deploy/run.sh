#!/usr/bin/env bash
# Executed by cron on the server. The image is already built locally by
# deploy-apply.sh at deploy time, so this just runs it - no build/pull cost
# on the daily schedule.
set -euo pipefail

ENV_FILE="/opt/beach-please/app/.env"

echo "[$(date -Is)] Running beach-please:local"
docker run --rm --env-file "${ENV_FILE}" beach-please:local
echo "[$(date -Is)] Run complete"
