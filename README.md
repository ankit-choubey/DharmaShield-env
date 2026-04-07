---
title: DharmaShield Env
emoji: 📘
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

[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?logo=github)](https://github.com/ankit-choubey/DharmaShield-env)
[![Hugging Face Space](https://img.shields.io/badge/HuggingFace-Space-FF9D00?logo=huggingface&logoColor=white)](https://huggingface.co/spaces/ankit-choubey/dharmashield-env)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Validated-2E7D32)](https://huggingface.co/blog/openenv-turing)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/)

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

## Baseline scores

Evaluated in strict router mode using `Qwen/Qwen2.5-72B-Instruct` via Hugging Face Router (`REQUIRE_HF_ROUTER=true`).

| Task | Difficulty | Score | Steps |
|------|------------|-------|-------|
| upi-scam-triage | Easy | 0.839 | 8 |
| sgi-compliance-review | Medium | 0.875 | 6 |
| cib-graph-takedown | Hard | 0.556 | 6 |
| **Average** |  | **0.757** |  |

Router evidence from strict run:

- `[ROUTER_SUMMARY] mode=strict successes=20 fallbacks=0 base=https://router.huggingface.co/v1 model=Qwen/Qwen2.5-72B-Instruct provider_model=qwen/qwen-2.5-72b-instruct`
- Fallback path was disabled for this baseline (`fallbacks=0` required to pass).

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
- Deployment baseline commit SHA: `5e99cc5`

## Sources and citations

1. MeitY FAQ and official IT Rules context: `https://www.meity.gov.in/writereaddata/files/FAQ_Intermediary_Rules_2021.pdf`
2. e-Gazette publication reference for IT Rules (official gazette portal): `https://egazette.nic.in/WriteReadData/2021/225464.pdf`
3. RBI Annual Report archive/publications page: `https://www.rbi.org.in/Scripts/AnnualReportPublications.aspx?head=Annual+Report`
4. RBI public awareness on digital/payment fraud risks (RBI Kehta Hai): `https://rbikehtahai.rbi.org.in/dpaw`
