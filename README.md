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

## Why This Problem Is Uniquely Hard

Unlike single-objective moderation benchmarks, DharmaShield models asymmetric legal risk under India-facing platform compliance:

- missing response windows degrades safe-harbour posture
- over-removal of legitimate content creates rights and due-process risk
- both inaction and wrong action are penalized through different pathways
- child-safety escalation requires urgent intervention without collapsing benign safety-awareness speech

This forces policy-aware optimization under time pressure, not just binary harmful-content classification.

## What is included

- OpenEnv-style environment with `reset()`, `step()`, `state()`
- FastAPI server with `POST /reset`, `POST /step`, `GET /state`, `GET /health`
- 4 deterministic tasks with graders and score clamping to `[0.0, 1.0]`
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

Latest V3.1 strict baseline re-run is currently blocked by HF router credit limits (`402`) on this account.
The most recent successful strict run artifact remains available for reference:
`artifacts/router_qwen.txt` (`fallbacks=0`).

Historical strict run snapshot (reference-only):

| Task | Difficulty | Score | Steps |
|------|------------|-------|-------|
| upi-scam-triage | Easy | 0.858 | 8 |
| sgi-compliance-review | Medium | 0.962 | 6 |
| cib-graph-takedown | Hard | 0.569 | 6 |
| child-safety-escalation | Hard | 0.880 | 4 |
| **Average** |  | **0.817** |  |

Router evidence from reference strict run:

- `[ROUTER_SUMMARY] mode=strict successes=24 fallbacks=0 base=https://router.huggingface.co/v1 model=Qwen/Qwen2.5-72B-Instruct provider_model=qwen/qwen-2.5-72b-instruct _router_successes=24 _router_fallbacks=0`
- Fallback path was disabled for this baseline (`fallbacks=0` required to pass).

## Model Benchmark Results

Rows are accepted only when strict-router run completes with `fallbacks=0`.
Benchmark automation uses substitution order:
`Qwen/Qwen2.5-72B-Instruct` -> `Qwen/Qwen2.5-7B-Instruct` -> `HuggingFaceH4/zephyr-7b-beta` -> `mistralai/Mistral-Nemo-Instruct-2407`.
Current run summary is in `artifacts/leaderboard_summary.csv`.

| Requested Model | Selected Model | UPI | SGI | CIB | Child Safety | Avg | Status |
|---|---|---:|---:|---:|---:|---:|---|
| Qwen/Qwen2.5-72B-Instruct | n/a | n/a | n/a | n/a | n/a | n/a | failed (credits/support) |
| meta-llama/Llama-3.3-70B-Instruct | n/a | n/a | n/a | n/a | n/a | n/a | failed (credits/support) |
| mistralai/Mistral-7B-Instruct-v0.3 | n/a | n/a | n/a | n/a | n/a | n/a | failed (credits/support) |

Notes:

- Qwen/Llama runs are currently hitting router credit depletion (`402`) on this account.
- Some substitute model IDs return non-chat / unsupported errors (`400`) under current router availability.
- Raw logs are preserved under `artifacts/router_*.txt`.

## Reward Design Philosophy

DharmaShield scoring is exploit-resistant and operationally grounded:

| Failure mode | Penalty signal |
|---|---|
| Wrong decision on legitimate content | false-positive penalty (−0.40) |
| Over-dominant single-action strategy | diversity penalty (−0.15 at task-score level) |
| Safe-harbour degradation | per-step safe-harbour delta (`+0.05 / −0.05 / −0.10`) |
| Missed response windows | compliance-health degradation through environment state |
| Overconfident wrong decisions | calibration delta (bounded to `±0.05`) |
| Weak policy rationale | rubric-style reason quality contribution |

A naive always-remove strategy is structurally penalized. High scores require context-sensitive, rule-aligned decisions.

## Research Grounding

DharmaShield V3 reward shaping aligns with industrial RL moderation findings from:

- Firooz et al., *Scaling Reinforcement Learning for Content Moderation with Large Language Models* (arXiv:2512.20061, Dec 2025)

Key mappings:

- rubric-style reason quality rewards policy-faithful reasoning traces, not only final labels
- multi-signal shaping reduces reward hacking risk from purely verifiable binary labels
- confidence calibration penalizes overconfident wrong moderation actions in high-risk workflows

## Strict Router Proof

Router integrity requirement for publishable baselines:

- run `python inference.py` with `REQUIRE_HF_ROUTER=true`
- accept run only if `[ROUTER_SUMMARY] ... fallbacks=0`
- reject and rerun if any fallback occurs

Artifacts are captured in `artifacts/router_*.txt` and `artifacts/leaderboard_summary.csv`.

## Docker

```bash
docker build -t dharma-shield-env .
docker run -p 7860:7860 dharma-shield-env
```

## Validation checklist

- `pytest` (current suite: 25 tests)
- `python inference.py`
- `docker build -t dharma-shield-env .`
- `curl -X POST http://127.0.0.1:7860/reset -H "Content-Type: application/json" -d '{}'`
- `openenv validate` (if OpenEnv CLI is installed)

## Submission artifacts

- GitHub repository URL: `https://github.com/ankit-choubey/DharmaShield-env.git`
- Hugging Face Space URL: `https://huggingface.co/spaces/ankit-choubey/dharmashield-env`
- Deployment baseline commit SHA: `1f2cacf`

## Sources and citations

1. MeitY FAQ and official IT Rules context: `https://www.meity.gov.in/writereaddata/files/FAQ_Intermediary_Rules_2021.pdf`
2. e-Gazette publication reference for IT Rules (official gazette portal): `https://egazette.nic.in/WriteReadData/2021/225464.pdf`
3. RBI Annual Report archive/publications page: `https://www.rbi.org.in/Scripts/AnnualReportPublications.aspx?head=Annual+Report`
4. RBI public awareness on digital/payment fraud risks (RBI Kehta Hai): `https://rbikehtahai.rbi.org.in/dpaw`
