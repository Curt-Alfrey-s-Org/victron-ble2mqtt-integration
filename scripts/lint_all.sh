#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Python: ruff (lint) =="
ruff check .

echo "== Python: ruff (format) =="
ruff format .

echo "== Python: black =="
black .

echo "== Python: isort =="
isort .

echo "== Shell: shellcheck =="
find scripts bin -type f -name "*.sh" -print0 | xargs -0 -r shellcheck || true

echo "== Shell: shfmt (check only) =="
shfmt -d scripts bin || true

echo "== YAML: yamllint =="
yamllint -s . || true

echo "All linters completed."
