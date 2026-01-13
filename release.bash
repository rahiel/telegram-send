#!/usr/bin/env bash
set -euo pipefail


rm -rf dist/
uv sync
uv build

# Make documentation
git checkout gh-pages
rm -rf docs/
pdoc -o docs/ telegram_send/

git add docs/
git commit -m "update docs"
