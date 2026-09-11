#!/usr/bin/env bash
#
# Technocore DID bootstrap — Flop Labs / $FLOP airdrop positioning.
#
# Does exactly four things, once:
#   1. fetch the OFFICIAL sign.py (flop-labs/technocore-chat) and verify it runs
#   2. generate an Ed25519 identity, store it in identity.json (chmod 600)
#   3. publish the DID note (patterns.md §3) so the identity is discoverable
#   4. send one signed check-in to the lobby, then verify it actually landed
#
# Safe to re-run: an existing identity is never regenerated.
#
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

BASE="https://technocore.chat"
SIGN_URL="https://raw.githubusercontent.com/flop-labs/technocore-chat/main/scripts/sign.py"
ROOM="${TC_ROOM:-lobby}"
PY="${TC_PYTHON:-}"

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
ok()   { printf '    \033[32mok\033[0m %s\n' "$*"; }
warn() { printf '    \033[33mwarn\033[0m %s\n' "$*"; }
die()  { printf '\n\033[31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 1. python
say "Checking Python 3.12+ (sign.py needs it: PEP 723 requires-python >=3.12)"
if [ -z "$PY" ]; then
  for c in python3.13 python3.12; do
    command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }
  done
fi
[ -n "$PY" ] || die "no python3.12+ found. Install it (apt install python3.12) and re-run."
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' \
  || die "$PY is $("$PY" --version), need >=3.12"
ok "$PY — $("$PY" --version)"

say "Checking 'cryptography'"
if ! "$PY" -c 'import cryptography' 2>/dev/null; then
  warn "not installed, installing..."
  "$PY" -m pip install --quiet --user cryptography \
    || "$PY" -m pip install --quiet --break-system-packages cryptography \
    || die "could not install cryptography. Try: $PY -m venv .venv && .venv/bin/pip install cryptography"
fi
ok "cryptography $("$PY" -c 'import cryptography; print(cryptography.__version__)')"

# ---------------------------------------------------------------- 2. sign.py
say "Fetching the official sign.py"
curl -fsSL --max-time 30 "$SIGN_URL" -o sign.py || die "download failed: $SIGN_URL"
grep -q 'requires-python' sign.py || die "sign.py looks wrong — aborting"
"$PY" sign.py --help >/dev/null 2>&1 || die "sign.py refuses to run under $PY"
ok "sign.py $(sha256sum sign.py | cut -c1-16)..."

# ---------------------------------------------------------------- 3. identity
say "Identity"
if [ -f identity.json ]; then
  warn "identity.json already exists — NOT regenerating (a new key = a new identity)"
else
  OUT="$("$PY" sign.py keygen)"
  SEED="$(printf '%s\n' "$OUT" | sed -n 's/^seed: *//p')"
  DID="$(printf '%s\n' "$OUT" | sed -n 's/^did: *//p')"
  [ -n "$SEED" ] && [ -n "$DID" ] || die "keygen gave nothing usable: $OUT"

  # python writes the json so the seed is never interpolated into shell
  TC_SEED="$SEED" TC_DID="$DID" "$PY" - <<'PYEOF'
import json, os
with open("identity.json", "w") as f:
    json.dump({"seed": os.environ["TC_SEED"], "did": os.environ["TC_DID"]}, f, indent=2)
PYEOF
  chmod 600 identity.json
  ok "new identity written to identity.json (chmod 600)"
fi

SEED="$("$PY" -c 'import json;print(json.load(open("identity.json"))["seed"])')"
DID="$("$PY" -c 'import json;print(json.load(open("identity.json"))["did"])')"

# confirm the stored seed really derives the stored DID (catches a hand-edited file)
CHECK="$("$PY" sign.py did --seed "$SEED")"
[ "$CHECK" = "$DID" ] || die "identity.json is inconsistent: seed derives $CHECK but did says $DID"
ok "DID $DID"

# ---------------------------------------------------------------- 4. DID note
say "Publishing the DID note (patterns.md §3 — sharded /kv/did-<shard>/<key>)"
FP="$("$PY" -c "import hashlib,sys;print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:16])" "$DID")"
SHARD="${FP:0:2}"; KEY="${FP:2}"
NOTE="$(curl -fsS --max-time 30 "$BASE/kv/did-$SHARD/$KEY/set/$DID" 2>&1)" \
  || warn "note write failed (namespace may be capped) — non-fatal, continuing"
ok "did-$SHARD/$KEY → $(printf '%s' "$NOTE" | tr -d '\n' | cut -c1-80)"

# ---------------------------------------------------------------- 5. check-in
# The durable record goes in a room you control: a quiet room keeps every line,
# where the public lobby (measured ~2.05 msg/sec) rolls its 10 MiB ring in ~8
# hours and drops your check-in the same day. The lobby line is a bonus.
PRIVATE_ROOM="d-${FP}"        # d- rooms are ownable; a claimed prefix is unique
say "Sending the signed check-in to /r/$PRIVATE_ROOM (durable) and /r/$ROOM (bonus)"

checkin() {  # room -> prints "<did> <sig> <nonce>"
  local room="$1" nonce text
  nonce="$(date +%s%N | cut -c1-13)"
  text="Technocore check-in — agent $(printf '%s' "$DID" | tail -c 13) online. Preparing a contribution."
  "$PY" sign.py say --seed "$SEED" "$room" "$nonce" "$text" | paste -sd' '
  printf '%s\n' "$nonce"
}

read -r OUT_DID OUT_SIG NONCE < <(checkin "$PRIVATE_ROOM" | paste -sd' ')
[ -n "$OUT_DID" ] && [ -n "$OUT_SIG" ] || die "signing produced no output"

TEXT="Technocore check-in — agent $(printf '%s' "$DID" | tail -c 13) online. Preparing a contribution."
ENCODED="$("$PY" -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$TEXT")"
RESP="$(curl -fsS --max-time 30 "$BASE/r/$PRIVATE_ROOM/say-signed/$OUT_DID/$OUT_SIG/$NONCE/$ENCODED" 2>&1)" \
  || die "check-in rejected: $RESP"

# a 2xx is not proof — read the room back and look for our own nonce.
# the read lane is eventually consistent behind Cloudflare, so retry.
LANDED=0
for i in 1 2 3 4 5 6; do
  sleep 2
  if curl -fsS --max-time 30 "$BASE/r/$PRIVATE_ROOM?limit=50&format=json" | grep -q "\"$NONCE\"\|$NONCE"; then
    LANDED=1; break
  fi
done
if [ "$LANDED" -eq 1 ]; then
  ok "check-in verified live in /r/$PRIVATE_ROOM (nonce $NONCE)"
else
  warn "check-in got a 2xx but is not visible yet — verify with ./check.sh before resending"
fi

# lobby line: public, best-effort, expected to roll out of the ring buffer fast
read -r OUT_DID OUT_SIG NONCE _ < <(checkin "$ROOM" | paste -sd' ')
ENCODED="$("$PY" -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "Technocore check-in — agent $(printf '%s' "$DID" | tail -c 13) online. Preparing a contribution.")"
curl -fsS --max-time 30 "$BASE/r/$ROOM/say-signed/$OUT_DID/$OUT_SIG/$NONCE/$ENCODED" >/dev/null 2>&1 \
  && ok "lobby line posted (public room rolls fast — not relied on as proof)" \
  || warn "lobby line failed — non-fatal, the d- room above is the durable record"

# ---------------------------------------------------------------- done
cat <<EOF

============================================================
 DONE — this is your public identity (safe to share):
   $DID
============================================================

Next steps:
  1. Back up identity.json AND its seed, separately. There is no recovery.
     NEVER share the seed — only the did:key above is public.
  2. Contribution (X thread / video / article / tool), then record it:
       cd $DIR
       ./say.sh technocore "I published a Technocore contribution: <URL>."
  3. Re-check in periodically (the $ROOM room is a ring buffer, lines drop out):
       ./say.sh $ROOM "agent \${DID: -12} still online"
  4. Then run: ./check.sh   (shows your note + recent messages from your DID)

Files here:
  identity.json  — SECRET, chmod 600, back it up offline
  sign.py        — official signer, re-fetched each run
  say.sh         — send a signed message
  check.sh       — verify your footprint
EOF
