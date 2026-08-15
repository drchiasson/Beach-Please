#!/usr/bin/env bash
# Forced command for the cron-trigger deploy key. Ignores any client-supplied
# command and always just: rebuilds the local image from the source the
# upload key just placed, then (re)installs the crontab. Nothing here is
# parameterized by the SSH client - the client cannot influence what runs.
set -euo pipefail

APP_DIR="/opt/beach-please/app"
CRON_FILE="${APP_DIR}/crontab.txt"

if [[ ! -s "$CRON_FILE" ]]; then
  echo "crontab.txt missing or empty at ${CRON_FILE}" >&2
  exit 1
fi

echo "Building beach-please:local from ${APP_DIR}"
docker build -t beach-please:local "$APP_DIR"

docker image prune -f >/dev/null

crontab "$CRON_FILE"
echo "Installed crontab from ${CRON_FILE}:"
crontab -l
