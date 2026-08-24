#!/usr/bin/env bash
# Deploy logic, run by the fixed stub the cron key's forced command execs
# (see bootstrap.sh). Uploaded to APP_DIR on every deploy (see deploy.yml),
# so unlike the stub, this file's logic updates automatically - no server
# access needed to change it. Rebuilds the local image from the source the
# upload key just placed, then (re)installs the crontab.
set -euo pipefail

APP_DIR="/opt/beach-please/app"
CRON_FILE="${APP_DIR}/crontab.txt"

# Registered now, runs on exit (not here) - cleans up src_incoming even if
# we exit early below, so the next deploy always starts with it absent.
trap 'rm -rf "${APP_DIR}/src_incoming"' EXIT

if [[ ! -s "$CRON_FILE" ]]; then
  echo "crontab.txt missing or empty at ${CRON_FILE}" >&2
  exit 1
fi

# sftp can't reliably overwrite src/ in place (see DEPLOY.md), so uploads
# land in src_incoming and get swapped into place with a real rm/mv here.
if [[ ! -d "${APP_DIR}/src_incoming" ]]; then
  echo "src_incoming missing at ${APP_DIR} - upload step didn't run?" >&2
  exit 1
fi
rm -rf "${APP_DIR}/src"
mv "${APP_DIR}/src_incoming" "${APP_DIR}/src"

echo "Building beach-please:local from ${APP_DIR}"
docker build -t beach-please:local "$APP_DIR"

docker image prune -f >/dev/null

crontab "$CRON_FILE"
echo "Installed crontab from ${CRON_FILE}:"
crontab -l
