#!/usr/bin/env bash
set -euo pipefail

source .venv312/bin/activate
python -m uvicorn dharma_shield.server:app --host 0.0.0.0 --port 7860
