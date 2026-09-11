#!/usr/bin/env bash
#
# push.sh — push repo ini pakai `gh` CLI (login device-code, tanpa browser di server).
#
# Prasyarat (sekali saja):
#   sudo apt install gh -y
#   gh auth login --web          # kode 8 karakter, approve dari HP/laptop
#
# Setelah itu script ini tinggal jalan — nggak minta token lagi.
#
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if ! command -v gh >/dev/null 2>&1; then
  cat >&2 <<'EOF'
gh belum keinstall.

  sudo apt install gh -y
  gh auth login --web

Terus jalanin script ini lagi.
EOF
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Belum login ke GitHub.

  gh auth login --web

Pilih: GitHub.com → HTTPS → Login with a web browser → copy kode → approve dari HP.
EOF
  exit 1
fi

# pastikan git pakai gh sebagai credential helper (sekali; idempoten)
if [ "$(git config --local --get credential.helper 2>/dev/null || true)" != "!gh auth git-credential" ]; then
  gh auth setup-git 2>/dev/null || true
fi

echo "==> gh: $(gh auth status 2>&1 | sed -n 's/.*Logged in to \(.*\) account \(.*\) .*/\1 sebagai \2/p' | head -1)"
echo "==> commit yang belum dipush:"
git log --oneline @{u}..HEAD 2>/dev/null || git log --oneline -3

echo
echo "==> push"
git push "$@"
echo "==> selesai: $(git remote get-url origin)"
