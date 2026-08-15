# Deploying Beach Please

GitHub Actions builds the image once on the runner as a sanity check (fails
fast on a broken Dockerfile/dependency, nothing is pushed anywhere), then
deploys over SSH using two single-purpose keys, each locked down with an
`authorized_keys` forced command so it can do exactly one thing:

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

5. Pin the server's host key so the workflow isn't vulnerable to a
   machine-in-the-middle on first connect. From your local machine:
   ```
   ssh-keyscan -t ed25519 your.server.example.com
   ```
   Save the full output line(s) — this goes in `DEPLOY_KNOWN_HOSTS` below.

## GitHub Actions secrets

Add these under the repo's Settings → Secrets and variables → Actions:

| Secret               | Value                                                        |
|-----------------------|--------------------------------------------------------------|
| `DEPLOY_HOST`         | Server hostname/IP                                            |
| `DEPLOY_USER`         | `deploy`                                                       |
| `DEPLOY_KNOWN_HOSTS`  | Output of `ssh-keyscan` from step 5                            |
| `DEPLOY_UPLOAD_KEY`   | Private key contents of `beach-please-upload`                  |
| `DEPLOY_CRON_KEY`     | Private key contents of `beach-please-cron`                    |

## Changing the schedule

Edit `deploy/crontab.txt` and push to `main`. The next deploy uploads the new
file and reinstalls it via the cron key — no server access required.

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

## Known caveat

The upload step removes and re-uploads `src/` on each deploy so files
deleted from the repo don't linger on the server (`-rm -r src` in the sftp
batch). Recursive `rm` requires a reasonably recent OpenSSH on the server; if
yours doesn't support it that one command is silently skipped (the batch
continues) and old files may accumulate under `src/` — harmless since Python
won't import unreferenced files, but worth an occasional manual cleanup if
you rename/delete source files often.
