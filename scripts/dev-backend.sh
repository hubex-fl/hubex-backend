#!/usr/bin/env sh
set -eu

PORT=""

if [ ! -d ".venv" ]; then
  echo "Missing .venv. Create it with:"
  echo "  python3 -m venv .venv"
  echo "  . ./.venv/bin/activate"
  echo "  python -m pip install -r requirements.txt"
  exit 1
fi

. ./.venv/bin/activate

echo "Tip: install deps if needed: python -m pip install -r requirements.txt"
echo "Starting backend on port ..."
python -m uvicorn app.main:app --reload --port ""
