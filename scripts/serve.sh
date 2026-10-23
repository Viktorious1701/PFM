#!/usr/bin/env bash
# Serve the PFM backend from this laptop to the family's phones.
#
#   scripts/serve.sh
#
# Runs the backend in production mode on its own live database and secret,
# published on the laptop's fixed Tailscale Funnel address
# (https://<laptop>.<tailnet>.ts.net — the same on every start, and built into
# the Android app). Sends real invitation emails that open the app:
# pfm://activate?token=…&server=…/api/v1. Ctrl-C stops the backend; Funnel
# itself stays configured in the Tailscale app on Windows.
#
# The live data lives in backend/var/live/ (gitignored): pfm.db, the JWT
# secret, and the logs. Back up pfm.db by copying it. The first ADMIN:
#   cd backend && DATABASE_URL=sqlite:///./var/live/pfm.db \
#     uv run python -m app.cli create-admin --email … --password '…'
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="$ROOT/backend/var/live"
PORT="${PORT:-8100}"  # 8000 stays free for the dev backend
# Tailscale runs on Windows (WSL here has no systemd); its CLI works from WSL.
TAILSCALE="${TAILSCALE:-$(command -v tailscale.exe || echo /mnt/d/tailscale.exe)}"

[ -x "$TAILSCALE" ] || { echo "tailscale.exe not found — see CLAUDE.md §3 (Serving to phones)" >&2; exit 1; }
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "Port $PORT is already in use (an earlier serve.sh?). Stop it first." >&2
  exit 1
fi

# 1. The public address: this laptop's Funnel, pointed at the backend's port.
#    Idempotent; the first time ever, Tailscale prints a link to approve Funnel.
"$TAILSCALE" funnel --bg "$PORT" >/dev/null
HOST="$("$TAILSCALE" status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
URL="https://$HOST"
API="$URL/api/v1"

mkdir -p "$LIVE"
chmod 700 "$LIVE"
# The live server signs sessions with its own secret, never the dev one.
if [ ! -s "$LIVE/jwt-secret" ]; then
  (umask 077 && head -c 48 /dev/urandom | base64 | tr -d '\n=+/' > "$LIVE/jwt-secret")
fi

# 2. The backend: production mode, live database, real email.
cd "$ROOT/backend"
export ENVIRONMENT=production
export DATABASE_URL="sqlite:///./var/live/pfm.db"
export JWT_SECRET="$(cat "$LIVE/jwt-secret")"
export EMAIL_TRANSPORT=auto
export ACTIVATION_URL_TEMPLATE="pfm://activate?token={token}&server=$API"
uv run alembic upgrade head >"$LIVE/migrate.log" 2>&1 || { echo "Migration failed — see $LIVE/migrate.log" >&2; exit 1; }

cat <<EOF

  PFM is being served at
    $URL

  Logs: $LIVE/backend.log
  Ctrl-C to stop.

EOF
# In the foreground: Ctrl-C stops it, and if it dies the script ends with it.
exec uv run uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >>"$LIVE/backend.log" 2>&1
