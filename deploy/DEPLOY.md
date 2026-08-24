# Deploying Beach Please

Every push to `main` runs `build-check` (builds the image on the runner as a
fast-failing sanity check; nothing is pushed anywhere or touches the server).
The actual deploy only runs when you manually trigger it: repo → **Actions**
→ **Deploy** → **Run workflow**. Pushing to `main` alone does not deploy.

Deploying goes over SSH using two single-purpose keys, each locked down with
an `authorized_keys` forced command so it can do exactly one thing:

- **upload key** — can only open an SFTP session rooted at
  `/opt/beach-please/app` on the server. Cannot run shell commands.
- **cron key** — can only execute `deploy/deploy-apply.sh` on the server,
  which rebuilds the image locally (`docker build -t beach-please:local .`)
  from the source the upload key just placed, then reinstalls the crontab.
  Any command sent by the client is ignored.

No image or source code ever leaves your server — there's no registry
involved, so there's no visibility (public/private) question at all. The
`deploy` user's crontab (`deploy/crontab.txt`) runs `deploy/run.sh`, which
just does `docker run --rm beach-please:local` — the image is already built
by the time cron fires, so the scheduled run has no build cost. Secrets the
container needs (Gemini/Telegram/etc. API keys) live only in
`/opt/beach-please/app/.env` on the server — the pipeline never reads,
uploads, or has access to that file.

## One-time server setup

1. Copy the `deploy/` directory to the server (any way you like — scp,
   pasting, git clone) and run as root:
   ```
   sudo ./bootstrap.sh
   ```
   This creates the `deploy` system user (home `/opt/beach-please`, added to
   the `docker` group so it can build/run containers), installs
   `deploy-apply.sh`, and prepares `~deploy/.ssh/authorized_keys`.

2. On your local machine, generate the two deploy keypairs:
   ```
   ssh-keygen -t ed25519 -N '' -C beach-please-upload -f beach-please-upload
   ssh-keygen -t ed25519 -N '' -C beach-please-cron   -f beach-please-cron
   ```

3. Append to `/opt/beach-please/.ssh/authorized_keys` on the server (the
   bootstrap script prints these lines for you, with the paths filled in):
   ```
   command="internal-sftp -d /opt/beach-please/app",restrict,no-pty,no-port-forwarding,no-X11-forwarding,no-agent-forwarding <contents of beach-please-upload.pub>
   command="/opt/beach-please/bin/deploy-apply.sh",restrict,no-pty,no-port-forwarding,no-X11-forwarding,no-agent-forwarding <contents of beach-please-cron.pub>
   ```

4. Place the app's `.env` on the server (never handled by CI):
   ```
   sudo -u deploy install -m 600 /dev/null /opt/beach-please/app/.env
   sudo -u deploy tee /opt/beach-please/app/.env <<'EOF'
   GOOGLE_API_KEY=...
   TELEGRAM_BOT_KEY=...
   TELEGRAM_CHANNEL_KEY=...
   EOF
   ```

5. If your server is only reachable on your local network (no public
   IP/port-forwarding), GitHub's cloud runners can't reach it - a connection
   from `deploy.yml` will just time out. Rather than exposing SSH to the
   internet, install a **self-hosted GitHub Actions runner directly on the
   server**, so the deploy job's SSH steps go over `localhost`:

   - Repo → **Settings → Actions → Runners → New self-hosted runner**, pick
     Linux/x64, and run the exact commands it shows you on the server, as
     your normal sudo user (not `deploy`) - e.g.:
     ```
     mkdir ~/actions-runner && cd ~/actions-runner
     curl -o actions-runner.tar.gz -L <url from the GitHub page>
     tar xzf actions-runner.tar.gz
     ./config.sh --url https://github.com/drchiasson/Beach-Please --token <token from the GitHub page>
     ```
   - Install it as a persistent service so it survives reboots/disconnects:
     ```
     sudo ./svc.sh install
     sudo ./svc.sh start
     ```
   - `deploy.yml`'s `deploy` job is already set to `runs-on: self-hosted` to
     use it (the `build-check` job stays on GitHub's cloud runners, since it
     doesn't need to reach the server).

   If your server *is* publicly reachable (a cloud VM, or you've deliberately
   port-forwarded 22), you can skip this and use GitHub's regular
   `ubuntu-latest` runners instead - just change `runs-on: self-hosted` back
   to `runs-on: ubuntu-latest` for the `deploy` job.

6. Pin the SSH host key so the workflow isn't vulnerable to a
   machine-in-the-middle on first connect. Run this **on the server itself**
   (since the runner connects over localhost):
   ```
   ssh-keyscan -t ed25519 localhost
   ```
   Save the full output line(s) — this goes in `DEPLOY_KNOWN_HOSTS` below.
   (If you skipped step 5 and are connecting over the public internet
   instead, run this from your local machine against the real hostname.)

## GitHub Actions secrets

Add these under the repo's Settings → Secrets and variables → Actions:

| Secret               | Value                                                        |
|-----------------------|--------------------------------------------------------------|
| `DEPLOY_HOST`         | `localhost` (self-hosted runner on the server) or the server's public hostname/IP |
| `DEPLOY_USER`         | `deploy`                                                       |
| `DEPLOY_KNOWN_HOSTS`  | Output of `ssh-keyscan` from step 6                            |
| `DEPLOY_UPLOAD_KEY`   | Private key contents of `beach-please-upload`                  |
| `DEPLOY_CRON_KEY`     | Private key contents of `beach-please-cron`                    |

## Changing the schedule

Edit `deploy/crontab.txt`, push to `main`, then manually trigger **Run
workflow** — the deploy uploads the new file and reinstalls it via the cron
key. No server access required.

## What the deploy credentials cannot do

Both keys are scoped by `authorized_keys` forced commands, independent of
whatever command the client sends. Even if a deploy secret leaked, it could
only overwrite files under `/opt/beach-please/app` (upload key) or re-run
`docker build` + `crontab crontab.txt` on whatever source is currently
uploaded there (cron key) — no general shell, no access to `.env`, no ability
to install arbitrary cron jobs without also compromising the upload key. Both
keys log in as the same `deploy` OS user, which is a member of the `docker`
group so it can build/run containers — that group membership (not either
deploy key) is what actually gives Docker access. If you need Docker access
isolated even from `deploy` itself, consider rootless Docker as a follow-up
hardening step.

## How src/ gets replaced on each deploy

When the target directory already exists, sftp's `put -r local remote`
uploads `local` as a subdirectory inside `remote`. So `put -r src src`,
against a server that already has `src/` from a previous deploy, produces
`src/src/*`. Docker's `COPY src ./src` never looks there, so the container
keeps running whatever was in the top-level `src/` before — even though the
deploy reports success.

To avoid uploading onto a directory that might already exist, the upload
always goes to `src_incoming/` instead of `src/`. `deploy-apply.sh`, running
as a real shell command on the server, then does `rm -rf src && mv
src_incoming src` before building.

`src_incoming` itself needs to not already exist for the same reason, so
`deploy-apply.sh` also guarantees it's gone by the time the script exits:

```bash
trap 'rm -rf "${APP_DIR}/src_incoming"' EXIT
```

This registers a cleanup command that bash runs when the script exits — at
the end, or on any failure along the way — not at the line where it's
written. On a normal deploy it's a no-op, since the `mv` above already
removed `src_incoming`. It only matters if the script fails before reaching
that `mv`.
