#!/usr/bin/env bash
# Serve the PFM backend from this laptop to the family's phones.
#
#   scripts/serve.sh
#
# Opens a free Cloudflare quick tunnel (https://<random>.trycloudflare.com,
# a new address every start), then runs the backend behind it in production
# mode on its own live database and secret, sending real invitation emails
# whose links carry the address: pfm://activate?token=…&server=…/api/v1.
# Prints the address for anyone signing in by hand. Ctrl-C stops both.
#
# The live data lives in backend/var/live/ (gitignored): pfm.db, the JWT
# secret, and the logs. Back up pfm.db by copying it. The first ADMIN:
#   cd backend && DATABASE_URL=sqlite:///./var/live/pfm.db \
#     uv run python -m app.cli create-admin --email … --password '…'
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="$ROOT/backend/var/live"
PORT="${PORT:-8100}"  # 8000 stays free for the dev backend
CLOUDFLARED="${CLOUDFLARED:-$(command -v cloudflared || echo "$HOME/.local/bin/cloudflared")}"

[ -x "$CLOUDFLARED" ] || { echo "cloudflared not found — see CLAUDE.md §3 (Serving to phones)" >&2; exit 1; }
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "Port $PORT is already in use (an earlier serve.sh?). Stop it first." >&2
  exit 1
fi

mkdir -p "$LIVE"
chmod 700 "$LIVE"
# The live server signs sessions with its own secret, never the dev one.
if [ ! -s "$LIVE/jwt-secret" ]; then
  (umask 077 && head -c 48 /dev/urandom | base64 | tr -d '\n=+/' > "$LIVE/jwt-secret")
fi

pids=()
cleanup() {
  trap - EXIT INT TERM
  for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
  echo; echo "Stopped."
}
trap cleanup EXIT INT TERM

# 1. The tunnel first: its address goes into the invitation links.
: > "$LIVE/tunnel.log"
"$CLOUDFLARED" tunnel --no-autoupdate --url "http://localhost:$PORT" >"$LIVE/tunnel.log" 2>&1 &
pids+=($!)
URL=""
for _ in $(seq 1 60); do
  URL="$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LIVE/tunnel.log" | head -1 || true)"
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || { echo "The tunnel did not come up — see $LIVE/tunnel.log" >&2; exit 1; }
API="$URL/api/v1"

# 2. The backend: production mode, live database, real email.
cd "$ROOT/backend"
export ENVIRONMENT=production
export DATABASE_URL="sqlite:///./var/live/pfm.db"
export JWT_SECRET="$(cat "$LIVE/jwt-secret")"
export EMAIL_TRANSPORT=auto
export ACTIVATION_URL_TEMPLATE="pfm://activate?token={token}&server=$API"
uv run alembic upgrade head >"$LIVE/migrate.log" 2>&1 || { echo "Migration failed — see $LIVE/migrate.log" >&2; exit 1; }
uv run uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >"$LIVE/backend.log" 2>&1 &
pids+=($!)

for _ in $(seq 1 60); do
  curl -s -m 2 -o /dev/null "http://127.0.0.1:$PORT/health" && break
  sleep 1
done

cat <<EOF

  PFM is being served.

  Server address (type it into the app's sign-in screen):
    $API

  Invitation emails carry it automatically.
  Logs: $LIVE/backend.log, $LIVE/tunnel.log
  Ctrl-C to stop. The address changes the next time this starts.

EOF
command -v qrencode >/dev/null && qrencode -t ansiutf8 "$API"

# Stop everything if either process dies, so a half-up server is never left running.
wait -n "${pids[@]}"
echo "A process exited — see $LIVE/backend.log and $LIVE/tunnel.log" >&2
