#!/usr/bin/env bash
set -euo pipefail


rm -rf dist/
uv sync
uv build
uv publish
