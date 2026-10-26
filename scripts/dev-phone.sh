#!/usr/bin/env bash
# Develop on a real Android phone: serves the app's code (Metro, :8081) to
# the PFM development build at a fixed address, through Tailscale Funnel on
# port 8443 — https://<laptop>.<tailnet>.ts.net:8443, the same every time, so
# the development build reopens it from its recent list. The web app keeps
# working at http://localhost:8081. Ctrl-C stops Metro.
#
# The phone's API server is separate: scripts/serve.sh (port 443 of the same
# address). The family APK needs neither this script nor this address.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$ROOT/mobile/.expo/dev-phone"
TAILSCALE="${TAILSCALE:-$(command -v tailscale.exe || echo /mnt/d/tailscale.exe)}"

[ -x "$TAILSCALE" ] || { echo "tailscale.exe not found — see CLAUDE.md §3 (Serving to phones)" >&2; exit 1; }
if lsof -ti:8081 >/dev/null 2>&1; then
  echo "Port 8081 is in use (a web dev server?). Stop it first; this one serves web too." >&2
  exit 1
fi
mkdir -p "$LOGS"

# Idempotent; Funnel's configuration survives restarts. Metro listens on IPv6
# only, which Windows reaches as localhost/[::1] — a bare port would mean
# 127.0.0.1 and answer 502.
"$TAILSCALE" funnel --bg --https=8443 http://localhost:8081 >/dev/null
HOST="$("$TAILSCALE" status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
URL="https://$HOST:8443"

cat <<EOF

  Metro is being served to the phone at
    $URL

  In the PFM development build: open it from the recent list, or
  "Enter URL manually" once. The first load builds the bundle (a minute or two).
  Logs: $LOGS/metro.log — Ctrl-C to stop.

EOF

cd "$ROOT/mobile"
# Metro advertises the public address to the phone instead of localhost.
EXPO_PACKAGER_PROXY_URL="$URL" exec npx expo start --dev-client --port 8081 --clear >"$LOGS/metro.log" 2>&1
