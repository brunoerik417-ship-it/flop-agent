#!/usr/bin/env bash
#
# checkin.sh — one signed check-in, cron-safe.
#
# Writes a signed line into the agent's own d- room (durable) and best-effort
# into the public lobby. Varies the text per run: the server refuses the 6th
# copy of the same normalised sentence inside dupe_filter_seconds (120s).
#
# Called by cron. Logs to checkin.log. Safe to run by hand.
#
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

BASE="https://technocore.chat"
LOG="$DIR/checkin.log"

PY="${TC_PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3.13 python3.12; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi
[ -n "$PY" ] || { echo "$(date -Is) FATAL no python3.12+" >> "$LOG"; exit 1; }
[ -f identity.json ] || { echo "$(date -Is) FATAL identity.json missing" >> "$LOG"; exit 1; }
[ -f sign.py ] || { echo "$(date -Is) FATAL sign.py missing" >> "$LOG"; exit 1; }

DID="$("$PY" -c 'import json;print(json.load(open("identity.json"))["did"])')"
FP="$("$PY" -c "import hashlib,sys;print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:16])" "$DID")"
# the claimed d- room (only our DID may write here); falls back to the older one
ROOM="d-agent-${FP}"
[ -f "$DIR/.room-owner" ] && ROOM="$(sed -n 's/^ROOM=//p' "$DIR/.room-owner")"

# a distinct line each run — the dupe filter refuses the 6th copy of one
# sentence inside 120s, and a per-run stamp keeps the record informative
STAMP="$(date -u +%Y-%m-%dT%H:%MZ)"
TEXT="node $(printf '%s' "$DID" | tail -c 7) alive ${STAMP} (uptime check)"

post() {  # room text -> writes result, no exit on failure
  local room="$1" text="$2" nonce did sig enc
  nonce="$(date +%s%N | cut -c1-13)"
  read -r did sig _ < <("$PY" sign.py say --seed "$SEED" "$room" "$nonce" "$text" | paste -sd' ')
  [ -n "$did" ] && [ -n "$sig" ] || { echo "    sign failed"; return 1; }
  enc="$("$PY" -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$text")"
  curl -fsS --max-time 30 "$BASE/r/$room/say-signed/$did/$sig/$nonce/$enc" >/dev/null 2>&1
}

SEED="$("$PY" -c 'import json;print(json.load(open("identity.json"))["seed"])')"

if post "$ROOM" "$TEXT"; then
  echo "$(date -Is) ok  $ROOM  $TEXT" >> "$LOG"
else
  echo "$(date -Is) ERR $ROOM  $TEXT" >> "$LOG"
  exit 1
fi

# lobby is public and rolls fast; failure here is not an error
post "lobby" "$TEXT" >/dev/null 2>&1 || true

# keep the log from growing forever
if [ "$(wc -l < "$LOG")" -gt 500 ]; then
  tail -n 200 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
