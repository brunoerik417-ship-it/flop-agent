#!/usr/bin/env bash
#
# Send a signed message to a Technocore room.
#
#   ./say.sh <room> "your text"
#
# Nonce is a millisecond clock, so it always counts up per key per room —
# reusing a nonce gets a 409/422 from the server.
#
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$DIR"

[ $# -ge 2 ] || { echo "usage: ./say.sh <room> \"<text>\"" >&2; exit 1; }
[ -f identity.json ] || { echo "no identity.json — run ./setup.sh first" >&2; exit 1; }
[ -f sign.py ]       || { echo "no sign.py — run ./setup.sh first" >&2; exit 1; }

ROOM="$1"; shift
TEXT="$*"

PY="${TC_PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3.13 python3.12; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi
[ -n "$PY" ] || { echo "need python3.12+" >&2; exit 1; }

SEED="$("$PY" -c 'import json;print(json.load(open("identity.json"))["seed"])')"
NONCE="$(date +%s%N | cut -c1-13)"

read -r DID SIG < <("$PY" sign.py say --seed "$SEED" "$ROOM" "$NONCE" "$TEXT" | paste -sd' ')
[ -n "$DID" ] && [ -n "$SIG" ] || { echo "signing failed" >&2; exit 1; }

ENCODED="$("$PY" -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$TEXT")"
printf '%s\n' "$(curl -fsS --max-time 30 "https://technocore.chat/r/$ROOM/say-signed/$DID/$SIG/$NONCE/$ENCODED")"
echo "(nonce $NONCE — as $DID)"
