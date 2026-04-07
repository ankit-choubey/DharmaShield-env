---
title: DharmaShield Env
emoji: 🛡️
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
tags:
  - openenv
  - rl-environment
  - content-moderation
  - india
pinned: false
---

# DharmaShield Env

AI training environment for policy-driven content moderation aligned to India-focused trust and safety workflows.

## One-line pitch

DharmaShield trains an AI agent to act as a trust-and-safety compliance officer that reviews UPI scams, synthetic content/deepfakes, and coordinated inauthentic behavior under time-bound policy enforcement.

## What is included

- OpenEnv-style environment with `reset()`, `step()`, `state()`
- FastAPI server with `POST /reset`, `POST /step`, `GET /state`, `GET /health`
- 3 deterministic tasks with graders and score clamping to `[0.0, 1.0]`
- Root `inference.py` with strict `[START] [STEP] [END]` logging
- Dockerized deployment for Hugging Face Spaces

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn dharma_shield.server:app --host 0.0.0.0 --port 7860
```

In another terminal:

```bash
curl -X POST http://127.0.0.1:7860/reset -H "Content-Type: application/json" -d '{}'
```

Run baseline:

```bash
python inference.py
```

## Environment variables for inference

- `API_BASE_URL` default: `https://router.huggingface.co/v1`
- `MODEL_NAME` default: `Qwen/Qwen2.5-72B-Instruct`
- `HF_TOKEN` (or `API_KEY`)

If token is absent, inference falls back to deterministic local policy heuristics.

## Docker

```bash
docker build -t dharma-shield-env .
docker run -p 7860:7860 dharma-shield-env
```

## Validation checklist

- `pytest`
- `python inference.py`
- `docker build -t dharma-shield-env .`
- `curl -X POST http://127.0.0.1:7860/reset -H "Content-Type: application/json" -d '{}'`
- `openenv validate` (if OpenEnv CLI is installed)

## Submission artifacts

- GitHub repository URL: `https://github.com/ankit-choubey/DharmaShield-env.git`
- Hugging Face Space URL: `https://huggingface.co/spaces/ankit-choubey/dharmashield-env`
- Final commit SHA: `PENDING_FIRST_COMMIT`

## Sources and citations

1. Gazette Notification **G.S.R. 120(E), February 10, 2026 (MeitY)** for India IT-rule framing.
2. **RBI Annual Report 2025-26 / RBI circular references** for UPI fraud pattern grounding.

Add canonical links to the exact documents above before submission.
