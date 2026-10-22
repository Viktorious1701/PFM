#!/usr/bin/env bash
# Develop on a real Android phone: serves the app's code (Metro, :8081) to the
# PFM development build through a free Cloudflare quick tunnel, so the phone
# needs no USB cable and no shared Wi-Fi. Prints the address to type into the
# development build's "Enter URL manually". The web app keeps working at
# http://localhost:8081. Ctrl-C stops both.
#
# The phone's API server is separate: scripts/serve.sh, entered on the app's
# sign-in screen.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$ROOT/mobile/.expo/dev-phone"
CLOUDFLARED="${CLOUDFLARED:-$(command -v cloudflared || echo "$HOME/.local/bin/cloudflared")}"

[ -x "$CLOUDFLARED" ] || { echo "cloudflared not found — see CLAUDE.md §3 (Serving to phones)" >&2; exit 1; }
if lsof -ti:8081 >/dev/null 2>&1; then
  echo "Port 8081 is in use (a web dev server?). Stop it first; this one serves web too." >&2
  exit 1
fi
mkdir -p "$LOGS"

pids=()
cleanup() {
  trap - EXIT INT TERM
  for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
  echo; echo "Stopped."
}
trap cleanup EXIT INT TERM

: > "$LOGS/tunnel.log"
"$CLOUDFLARED" tunnel --no-autoupdate --url http://localhost:8081 >"$LOGS/tunnel.log" 2>&1 &
pids+=($!)
URL=""
for _ in $(seq 1 60); do
  URL="$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOGS/tunnel.log" | head -1 || true)"
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || { echo "The tunnel did not come up — see $LOGS/tunnel.log" >&2; exit 1; }

cd "$ROOT/mobile"
# Metro advertises the tunnel address to the phone instead of localhost.
EXPO_PACKAGER_PROXY_URL="$URL" npx expo start --dev-client --port 8081 --clear >"$LOGS/metro.log" 2>&1 &
pids+=($!)

cat <<EOF

  Metro is being served to the phone.

  In the PFM development build, tap "Enter URL manually" and type:
    $URL

  The first load builds the bundle (a minute or two). Logs: $LOGS/
  Ctrl-C to stop.

EOF
command -v qrencode >/dev/null && qrencode -t ansiutf8 "$URL"

wait -n "${pids[@]}"
echo "A process exited — see $LOGS/metro.log and $LOGS/tunnel.log" >&2
