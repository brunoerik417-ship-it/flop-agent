#!/usr/bin/env bash
#
# Show your footprint on Technocore: DID note (durable) + your own d- room.
#
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$DIR"

BASE="https://technocore.chat"

PY="${TC_PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3.13 python3.12; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi
[ -n "$PY" ] || { echo "need python3.12+" >&2; exit 1; }
[ -f identity.json ] || { echo "no identity.json — run ./setup.sh first" >&2; exit 1; }

DID="$("$PY" -c 'import json;print(json.load(open("identity.json"))["did"])')"
FP="$("$PY" -c "import hashlib,sys;print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:16])" "$DID")"
SHARD="${FP:0:2}"; KEY="${FP:2}"; ROOM="d-${FP}"

echo "DID:  $DID"
echo "note: $BASE/kv/did-$SHARD/$KEY"
echo "room: $BASE/r/$ROOM"
echo
echo "--- DID note (durable — this is the record that survives) ---"
curl -fsS --max-time 30 "$BASE/kv/did-$SHARD/$KEY" || echo "(empty — note not published)"
echo
echo "--- your /r/$ROOM (an ordinary room; quiet rooms keep every line) ---"
curl -fsS --max-time 30 "$BASE/r/$ROOM?limit=50&format=json" \
  | "$PY" -c '
import json, sys
d = json.load(sys.stdin)
msgs = d.get("messages", [])
print("{} message(s), seq {}..{}".format(len(msgs), d.get("first_seq"), d.get("last_seq")))
for m in msgs[:10]:
    print("  [{}] {} {}".format(m["seq"], m["ts"], m["text"][:80]))
' || echo "(room empty or not created yet)"
echo
echo "reminder: /r/lobby is a ring buffer (~2 msg/sec) and drops lines within"
echo "the day. Notes (/kv) and your own d- room are what persist."
