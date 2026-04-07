#!/usr/bin/env bash
set -euo pipefail

source .venv312/bin/activate
pytest tests/ -v --tb=short
openenv validate
REQUIRE_HF_ROUTER=true python inference.py
