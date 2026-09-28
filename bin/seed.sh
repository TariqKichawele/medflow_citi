#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

if [[ ! -x "$BACKEND/.venv/bin/python" ]]; then
  echo "Virtual environment missing. Run bin/setup.sh first." >&2
  exit 1
fi

cd "$BACKEND"
# shellcheck disable=SC1091
source "$BACKEND/.venv/bin/activate"
python -m app.seed
