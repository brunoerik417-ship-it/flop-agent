#!/usr/bin/env bash
#
# x.sh — wrapper: run the X operator toolkit in the captcha-solver venv under Xvfb.
#
#   ./scripts/x.sh whoami
#   ./scripts/x.sh check
#   ./scripts/x.sh mentions 10
#   ./scripts/x.sh post "hello world"
#   ./scripts/x.sh post --file scripts/post.txt --dry-run
#   ./scripts/x.sh reply https://x.com/user/status/123 "nice"
#   ./scripts/x.sh like https://x.com/user/status/123
#
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV=/home/goonjoru/.hermes/profiles/godhood/workspace/captcha-solver/venv
PY="$VENV/bin/python"

[ -x "$PY" ] || { echo "venv python missing: $PY" >&2; exit 1; }
command -v xvfb-run >/dev/null || { echo "xvfb-run missing: sudo apt install xvfb" >&2; exit 1; }

exec xvfb-run -a --server-args="-screen 0 1920x1080x24" \
  "$PY" "$DIR/x_ops.py" "$@"
