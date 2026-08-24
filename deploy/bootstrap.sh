#!/usr/bin/env bash
# One-time server bootstrap for Beach Please deployment.
# Run once as root (or via sudo) on the target server, from this deploy/ directory:
#   sudo ./bootstrap.sh
set -euo pipefail

DEPLOY_USER="deploy"
DEPLOY_HOME="/opt/beach-please"
APP_DIR="${DEPLOY_HOME}/app"
BIN_DIR="${DEPLOY_HOME}/bin"

if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  useradd --create-home --home-dir "$DEPLOY_HOME" --shell /bin/bash "$DEPLOY_USER"
fi

usermod -aG docker "$DEPLOY_USER"

mkdir -p "$APP_DIR" "$BIN_DIR" "${DEPLOY_HOME}/.ssh"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$DEPLOY_HOME"
chmod 700 "${DEPLOY_HOME}/.ssh"

# Fixed forced-command entrypoint for the cron key. Deliberately never
# changes and stays out of the upload key's reach (it's owned by root, and
# lives outside APP_DIR which is all the upload key can write to) - it just
# execs the real deploy-apply.sh from APP_DIR, which every deploy's sftp
# upload keeps current (see deploy.yml). This indirection means deploy
# logic changes ship automatically from here on; this stub is the only
# thing that ever needs installing by hand, and only this once.
cat > "${BIN_DIR}/deploy-apply.sh" << STUB
#!/usr/bin/env bash
set -euo pipefail
exec "${APP_DIR}/deploy-apply.sh"
STUB
chown root:root "${BIN_DIR}/deploy-apply.sh"
chmod 755 "${BIN_DIR}/deploy-apply.sh"

touch "${DEPLOY_HOME}/.ssh/authorized_keys"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_HOME}/.ssh/authorized_keys"
chmod 600 "${DEPLOY_HOME}/.ssh/authorized_keys"

echo
echo "Bootstrap complete. Remaining one-time steps:"
echo
echo "1. Generate two ed25519 keypairs on your local machine (not the server):"
echo "     ssh-keygen -t ed25519 -N '' -C beach-please-upload -f beach-please-upload"
echo "     ssh-keygen -t ed25519 -N '' -C beach-please-cron   -f beach-please-cron"
echo
echo "2. Append these two lines to ${DEPLOY_HOME}/.ssh/authorized_keys"
echo "   (replace <upload pub key> / <cron pub key> with the .pub file contents):"
echo "     command=\"internal-sftp -d ${APP_DIR}\",restrict,no-pty,no-port-forwarding,no-X11-forwarding,no-agent-forwarding <upload pub key>"
echo "     command=\"${BIN_DIR}/deploy-apply.sh\",restrict,no-pty,no-port-forwarding,no-X11-forwarding,no-agent-forwarding <cron pub key>"
echo
echo "3. Place the app's runtime secrets at ${APP_DIR}/.env (chmod 600, owned by ${DEPLOY_USER})."
echo "   This file is never touched by the deploy pipeline."
echo
echo "4. Add the private keys + host details as GitHub Actions secrets (see deploy/DEPLOY.md)."
