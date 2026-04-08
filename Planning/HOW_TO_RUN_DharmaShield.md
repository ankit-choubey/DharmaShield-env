# DharmaShield — How To Run (Beginner Friendly)

This guide is for anyone running the project for the first time on local machine, CI, or while validating the Hugging Face Space.

## 1. Prerequisites

- Python `3.11+` (project tested on 3.11/3.12)
- Git
- Internet access (required for HF router model calls)
- Optional: Docker (for container validation)

## 2. Clone and Setup

```bash
git clone https://github.com/ankit-choubey/DharmaShield-env.git
cd DharmaShield-env
python -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt
```

## 3. Configure Environment Variables

Create/update `.env` in project root:

```bash
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
HF_TOKEN=hf_xxxxxxxxxxxxxxxxx
SAFE_MODE=true
VERBOSE=false
```

Notes:
- `SAFE_MODE=true` keeps submission-safe behavior.
- `VERBOSE=false` prints only required benchmark logs by default.

## 4. Run Validation Gates (Local)

```bash
source .venv312/bin/activate
pytest tests/ -q
openenv validate
```

Expected:
- Tests should pass.
- `openenv validate` should print readiness status.

## 5. Run Server Locally

```bash
source .venv312/bin/activate
uvicorn dharma_shield.server:app --host 0.0.0.0 --port 7860
```

Check endpoints:

```bash
curl http://127.0.0.1:7860/
curl http://127.0.0.1:7860/health
curl -X POST http://127.0.0.1:7860/reset -H "Content-Type: application/json" -d '{}'
curl -X POST http://127.0.0.1:7860/step -H "Content-Type: application/json" -d '{"decision":"approve"}'
curl http://127.0.0.1:7860/episodes
```

UI:
- Open `http://127.0.0.1:7860/ui`

## 6. Run Baseline Inference

```bash
source .venv312/bin/activate
python inference.py
```

Log format should contain:
- `[START]`
- `[STEP]`
- `[END]`

## 7. Strict Router Benchmark Run

Single strict run:

```bash
source .venv312/bin/activate
REQUIRE_HF_ROUTER=true python inference.py
```

Multi-model strict script:

```bash
source .venv312/bin/activate
bash scripts/run_leaderboard_strict.sh
```

Outputs:
- `artifacts/leaderboard_summary.csv`
- `artifacts/router_*.txt`

Important:
- A row is considered valid only when router summary has `fallbacks=0`.
- Credit exhaustion / unsupported model may produce `n/a` rows (expected).

## 8. Docker Check

```bash
docker build -t dharmashield-env .
docker run --rm -p 7860:7860 dharmashield-env
```

Then test:

```bash
curl http://127.0.0.1:7860/health
```

## 9. Hugging Face Space Validation

After pushing to HF Space:

```bash
curl https://ankit-choubey-dharmashield-env.hf.space/
curl https://ankit-choubey-dharmashield-env.hf.space/health
curl -X POST https://ankit-choubey-dharmashield-env.hf.space/reset -H "Content-Type: application/json" -d '{}'
curl -X POST https://ankit-choubey-dharmashield-env.hf.space/step -H "Content-Type: application/json" -d '{"decision":"approve"}'
```

Expected HTTP codes: `200`.

## 10. Common Issues

- `402` from HF router:
  - Token credits exhausted; strict runs will fail and show fallbacks.
- `400 unsupported/non-chat model`:
  - Use a router-supported chat model from benchmark substitution list.
- `openenv validate` says lock out of date:
  - Run `uv lock`, then rerun `openenv validate`.

---

If all checks in sections 4, 5, 6, and 9 pass, the environment is operational for judge-style endpoint interaction.
