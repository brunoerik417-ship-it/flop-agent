#!/usr/bin/env bash
#
# post_x.sh — post scripts/post.txt to X via CloakBrowser (headed, under Xvfb).
#
#   ./scripts/post_x.sh --dry-run    fill composer, screenshot, DO NOT post
#   ./scripts/post_x.sh --post       publish
#
# Runs in the captcha-solver venv because that is where cloakbrowser lives.
# Keeps ONE persistent browser profile so fingerprint + cookie history stay
# stable between runs — a fresh profile each time is itself a bot signal.
#
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV=/home/goonjoru/.hermes/profiles/godhood/workspace/captcha-solver/venv
PY="$VENV/bin/python"

if [ ! -x "$PY" ]; then
  echo "venv python not found: $PY" >&2
  exit 1
fi
if ! command -v xvfb-run >/dev/null 2>&1; then
  echo "xvfb-run missing: sudo apt install xvfb" >&2
  exit 1
fi

exec xvfb-run -a --server-args="-screen 0 1920x1080x24" \
  "$PY" "$DIR/post_x.py" "$@"
