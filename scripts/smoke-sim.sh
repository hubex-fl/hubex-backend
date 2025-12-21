#!/usr/bin/env sh
set -eu

echo "SMOKE_SIM: import app.simulator"
python -c "import app.simulator"

echo "SMOKE_SIM: run help"
python -m app.simulator --help
