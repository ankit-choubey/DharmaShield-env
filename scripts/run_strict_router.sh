#!/usr/bin/env bash
set -euo pipefail

source .venv312/bin/activate
REQUIRE_HF_ROUTER=true python inference.py
