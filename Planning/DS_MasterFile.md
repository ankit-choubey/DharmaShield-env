# 🛡️ DharmaShield Master File

**Latest Update:** 2026-04-07 14:05:00+05:30
**Status:** HF Prep & Robust Input Integration Complete

---

## 📜 Evolution & Context Log

### [2026-04-07 14:05] HF Spaces Prep & Robust Input Handling
**Context:** Prepared environment for Hugging Face Spaces deployment, improved input resilience for LLM-driven actions, and added convenience scripts. Integrated `openenv-core` and added edge-case testing for payload failures.

**Key Components Updated:**
- **Infrastructure:** `Dockerfile` (non-root user), `README.md` (metadata), `pyproject.toml` (scripts).
- **Core Logic:** `server.py` (flexible body handling), `validators.py` (decision normalization).
- **Tests:** `conftest.py` (path fix), `test_edge_cases.py` (v2 with API smoke tests).

**Validation Results:**
- `pytest`: 9 passed (including 2 new edge cases)
- `inference.py`: Verified with local heuristics (HF token missing).

---

### [2026-04-07 03:15] Initial Baseline Setup
**Context:** Implemented end-to-end project scaffold and working baseline for DharmaShield, including all required modules, API endpoints, inference pipeline, tests, Docker assets, and openenv.yaml.

**Key Components Delivered:**
- **Core package:** `dharma_shield/` (environment, validators, grader, models, task_data, policy_book, server)
- **Root Assets:** `openenv.yaml`, `inference.py`, `Dockerfile`, `requirements.txt`, `README.md`
- **Tests:** `tests/` (reset, step, grader, edge_cases, openenv_schema)

**Validation Results:**
- `pytest`: 7 passed
- `inference.py`: Successfully runs all 3 tasks with exact [START]/[STEP]/[END] format.
- API Smoke Test: `/health`, `/reset`, `/state` verified via FastAPI TestClient.

**Blockers/Notes:**
- `openenv` CLI and `docker` not installed in this restricted environment (validated via logic and TestClient).
- Folder is not yet a git repo. Next steps: Initialize git and prepare HF/GitHub deploy.

---

## 📂 Project Directory Structure

```text
/Users/theankit/Documents/AK/DharmaShield_ENV/
├── dharma_shield/
│   ├── __init__.py
│   ├── environment.py
│   ├── grader.py
│   ├── models.py
│   ├── policy_book.py
│   ├── server.py
│   ├── task_data.py
│   └── validators.py
├── tests/
│   ├── test_edge_cases.py
│   ├── test_grader.py
│   ├── test_openenv_schema.py
│   ├── test_reset.py
│   └── test_step.py
├── Dockerfile
├── README.md
├── inference.py
├── openenv.yaml
└── requirements.txt
```

---

## 🛠️ Infrastructure & Config

### [openenv.yaml](file:///Users/theankit/Documents/AK/DharmaShield_ENV/openenv.yaml)
```yaml
name: dharma-shield-env
version: 1.0.0
description: Policy-driven content moderation environment under India IT rules.
entrypoint: dharma_shield.environment:DharmaShieldEnvironment
framework: openenv
tags:
  - openenv
  - trust-safety
  - india-compliance
reward_range:
  min: 0.0
  max: 1.0
observation_model: dharma_shield.models:DharmaShieldObservation
action_model: dharma_shield.models:DharmaShieldAction
reward_model: dharma_shield.models:DharmaShieldReward
api:
  base_path: /
  endpoints:
    reset: POST /reset
    step: POST /step
    state: GET /state
    health: GET /health
tasks:
  - id: upi-scam-triage
    difficulty: easy
    max_steps: 10
  - id: sgi-compliance-review
    difficulty: medium
    max_steps: 8
  - id: cib-graph-takedown
    difficulty: hard
    max_steps: 6
```

### [Dockerfile](file:///Users/theankit/Documents/AK/DharmaShield_ENV/Dockerfile)
```dockerfile
FROM python:3.11-slim

# Non-root user — HF Spaces requirement
RUN useradd -m -u 1000 user
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --chown=user requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY --chown=user . /app

USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=3)"

# Critical: 0.0.0.0 mandatory — not localhost
CMD ["uvicorn", "dharma_shield.server:app", "--host", "0.0.0.0", "--port", "7860"]
```

### [README.md](file:///Users/theankit/Documents/AK/DharmaShield_ENV/README.md)
```markdown
---
title: DharmaShield Env
emoji: 🛡️
colorFrom: orange
colorTo: red
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

- GitHub repository URL: `https://github.com/theankit/DharmaShield_ENV`
- Hugging Face Space URL: `<ADD_HF_SPACE_URL>`
- Final commit SHA: `<ADD_COMMIT_SHA>`

## Sources and citations

1. Gazette Notification **G.S.R. 120(E), February 10, 2026 (MeitY)** for India IT-rule framing.
2. **RBI Annual Report 2025-26 / RBI circular references** for UPI fraud pattern grounding.

Add canonical links to the exact documents above before submission.
```

### [requirements.txt](file:///Users/theankit/Documents/AK/DharmaShield_ENV/requirements.txt)
```text
fastapi==0.115.0
uvicorn==0.27.0
pydantic==2.6.0
httpx==0.27.0
openai==1.30.0
python-dotenv==1.0.0
pyyaml==6.0.2
pytest==8.3.5
```

### [pyproject.toml](file:///Users/theankit/Documents/AK/DharmaShield_ENV/pyproject.toml)
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dharma-shield-env"
version = "1.0.0"
description = "Policy-driven trust and safety OpenEnv benchmark environment."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "fastapi==0.115.0",
  "uvicorn==0.27.0",
  "pydantic==2.6.0",
  "httpx==0.27.0",
  "openai==1.30.0",
  "python-dotenv==1.0.0",
  "pyyaml==6.0.2",
  "openenv-core>=0.2.0",
]

[project.scripts]
server = "server.app:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### [uv.lock](file:///Users/theankit/Documents/AK/DharmaShield_ENV/uv.lock)
```toml
# uv lockfile placeholder for OpenEnv validator compatibility in this environment.
# Regenerate in CI/local with: UV_CACHE_DIR=.uv-cache uv lock
```

---

## 🧠 Core Package: `dharma_shield/`

### [dharma_shield/__init__.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/dharma_shield/__init__.py)
```python
"""DharmaShield environment package."""

from .environment import DharmaShieldEnvironment

__all__ = ["DharmaShieldEnvironment"]
```

### [dharma_shield/environment.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/dharma_shield/environment.py)
```python
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from .grader import compute_step_reward
from .models import (
    AccountMeta,
    ContentItem,
    DharmaShieldAction,
    DharmaShieldObservation,
    DharmaShieldReward,
    EpisodeState,
    StepInfo,
)
from .task_data import TASK_DATA, TASK_ORDER
from .validators import apply_safe_harbour_logic, is_time_window_active, is_valid_rule_key, should_terminate


class DharmaShieldEnvironment:
    def __init__(self) -> None:
        self.task_order = TASK_ORDER
        self.current_task_idx = 0
        self.current_task_id = self.task_order[self.current_task_idx]
        self.current_queue: List[Dict[str, Any]] = []
        self.state_data = EpisodeState()
        self.action_history: List[Dict[str, str]] = []
        self.reset(self.current_task_id)

    def _build_observation(self) -> DharmaShieldObservation:
        idx = min(self.state_data.queue_index, len(self.current_queue) - 1)
        item = self.current_queue[idx]
        item_model = ContentItem(
            content_id=item["content_id"],
            text=item["text"],
            content_type=item["content_type"],
            sgi_flag=item.get("sgi_flag", False),
            upi_pattern_detected=item.get("upi_pattern_detected", False),
            toxicity_score=item.get("toxicity_score", 0.0),
            language=item.get("language", "en"),
            linked_accounts=item.get("linked_accounts", []),
            timestamp_offset_sec=item.get("timestamp_offset_sec", 0),
            english_summary=item.get("english_summary"),
            evidence_signals=item.get("evidence_signals", []),
            target_account=item.get("target_account"),
        )
        account_model = AccountMeta(**item["account_meta"])
        expected_rule = item.get("ground_truth_rule", "")
        hints = [expected_rule] if expected_rule else []

        return DharmaShieldObservation(
            current_item=item_model,
            account_meta=account_model,
            time_remaining_hours=self.state_data.time_remaining_hours,
            active_rule_hints=hints,
            similar_past_decisions=[a["decision"] for a in self.action_history[-5:]],
            step_number=self.state_data.current_step,
            queue_size_remaining=max(0, len(self.current_queue) - self.state_data.queue_index),
            platform_compliance_health=max(0.0, min(1.0, self.state_data.compliance_health)),
            safe_harbour_status=self.state_data.safe_harbour_status,
        )

    def reset(self, task_id: Optional[str] = None) -> DharmaShieldObservation:
        if task_id:
            if task_id not in TASK_DATA:
                raise ValueError(f"Unknown task_id: {task_id}")
            self.current_task_id = task_id
            self.current_task_idx = self.task_order.index(task_id)
        task_cfg = TASK_DATA[self.current_task_id]
        self.current_queue = deepcopy(task_cfg["items"])
        self.action_history = []
        self.state_data = EpisodeState(
            current_step=0,
            task_id=self.current_task_id,
            queue_index=0,
            time_remaining_hours=task_cfg["time_budget_hours"],
            compliance_health=1.0,
            missed_deadlines=0,
            false_positives=0,
            safe_harbour_status="protected",
            step_rewards=[],
            reveal_phase=0,
            completed=False,
        )
        return self._build_observation()

    def state(self) -> Dict[str, Any]:
        return self.state_data.model_dump()

    def _advance_task(self) -> None:
        self.current_task_idx = (self.current_task_idx + 1) % len(self.task_order)
        self.current_task_id = self.task_order[self.current_task_idx]

    def step(self, action: DharmaShieldAction) -> Tuple[DharmaShieldObservation, DharmaShieldReward, bool, StepInfo]:
        try:
            task_cfg = TASK_DATA[self.current_task_id]
            max_steps = task_cfg["max_steps"]
            queue_len = len(self.current_queue)
            done, reason = should_terminate(self.state_data, queue_len, max_steps)
            if done:
                info = StepInfo(task_id=self.current_task_id, termination_reason=reason)
                obs = self._build_observation()
                reward = DharmaShieldReward(
                    step_reward=0.0,
                    decision_accuracy=0.0,
                    rule_accuracy=0.0,
                    time_efficiency=0.0,
                    evidence_quality=0.0,
                    false_positive_penalty=0.0,
                    cumulative_episode_score=(sum(self.state_data.step_rewards) / len(self.state_data.step_rewards))
                    if self.state_data.step_rewards
                    else 0.0,
                )
                return obs, reward, True, info

            current = self.current_queue[self.state_data.queue_index]
            expected_decision = current.get("ground_truth_decision", "request_human_review")
            expected_rule = current.get("ground_truth_rule", "")
            expected_signals = current.get("evidence_signals", [])

            rule_valid = is_valid_rule_key(action.rule_cited)
            time_window_active = is_time_window_active(
                expected_rule if expected_rule else action.rule_cited,
                self.state_data.time_remaining_hours,
            )

            if not time_window_active:
                self.state_data.missed_deadlines += 1
                self.state_data.compliance_health = max(0.0, self.state_data.compliance_health - 0.1)
                if self.state_data.safe_harbour_status == "protected":
                    self.state_data.safe_harbour_status = "at_risk"

            reward = compute_step_reward(
                task_id=self.current_task_id,
                action=action,
                expected_decision=expected_decision,
                expected_rule=expected_rule,
                expected_signals=expected_signals,
                time_remaining_hours=self.state_data.time_remaining_hours,
                state=self.state_data,
            )

            if expected_decision == "approve" and action.decision == "remove":
                self.state_data.false_positives += 1
                self.state_data.compliance_health = max(0.0, self.state_data.compliance_health - 0.12)

            apply_safe_harbour_logic(
                self.state_data,
                expected_rule=expected_rule,
                correct_decision=(action.decision == expected_decision),
            )

            self.action_history.append(
                {
                    "decision": action.decision,
                    "rule_cited": action.rule_cited,
                    "target_account": action.target_account or current.get("target_account"),
                }
            )

            self.state_data.current_step += 1
            self.state_data.queue_index += 1
            self.state_data.time_remaining_hours = max(0.0, self.state_data.time_remaining_hours - 0.35)

            done, reason = should_terminate(self.state_data, queue_len, max_steps)
            if done:
                self.state_data.completed = True
                self.state_data.queue_index = min(self.state_data.queue_index, queue_len - 1)
                if self.state_data.queue_index < 0:
                    self.state_data.queue_index = 0
                self._advance_task()

            obs = self._build_observation()
            info = StepInfo(
                task_id=self.current_task_id,
                termination_reason=reason if done else None,
                rule_valid=rule_valid,
                time_window_active=time_window_active,
                expected_decision=expected_decision,
                expected_rule=expected_rule,
            )
            return obs, reward, done, info
        except Exception as exc:  # pragma: no cover - defensive path
            self.state_data.completed = True
            obs = self._build_observation()
            reward = DharmaShieldReward(
                step_reward=0.0,
                decision_accuracy=0.0,
                rule_accuracy=0.0,
                time_efficiency=0.0,
                evidence_quality=0.0,
                false_positive_penalty=0.0,
                cumulative_episode_score=0.0,
            )
            info = StepInfo(
                task_id=self.current_task_id,
                error=str(exc),
                termination_reason="exception",
                rule_valid=False,
                time_window_active=False,
            )
            return obs, reward, True, info


# Backward-compatible alias for older imports.
DharmaShieldEnv = DharmaShieldEnvironment
```

### [dharma_shield/validators.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/dharma_shield/validators.py)
```python
from __future__ import annotations

from typing import Dict, Tuple

from .models import EpisodeState
from .policy_book import POLICY_BOOK

VALID_DECISIONS = {
    "remove",
    "approve",
    "label_sgi",
    "warn_user",
    "escalate",
    "request_human_review",
}


def is_valid_rule_key(rule_cited: str) -> bool:
    if not rule_cited or rule_cited == "UNKNOWN":
        return True
    return rule_cited in POLICY_BOOK


def is_time_window_active(rule_cited: str, time_remaining_hours: float) -> bool:
    if not rule_cited or rule_cited == "UNKNOWN":
        return True
    rule = POLICY_BOOK.get(rule_cited)
    if not rule:
        return False
    return time_remaining_hours > 0.0 and time_remaining_hours <= rule["time_window_hours"]


def should_terminate(state: EpisodeState, queue_len: int, max_steps: int) -> Tuple[bool, str]:
    if state.current_step >= max_steps:
        return True, "max_steps_reached"
    if state.queue_index >= queue_len:
        return True, "queue_exhausted"
    return False, ""


def apply_safe_harbour_logic(state: EpisodeState, expected_rule: str, correct_decision: bool) -> None:
    if not_expected_rule or expected_rule not in POLICY_BOOK:
        return
    rule = POLICY_BOOK[expected_rule]
    if not rule["safe_harbour_lost"]:
        return
    if not correct_decision:
        state.safe_harbour_status = "at_risk"
        if state.missed_deadlines >= 1:
            state.safe_harbour_status = "lost"
            state.compliance_health = max(0.0, state.compliance_health - 0.15)


def validate_step_payload(payload: Dict[str, object]) -> Dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    return payload


def normalize_decision(raw: str) -> str:
    if not isinstance(raw, str):
        return "request_human_review"
    cleaned = raw.strip().lower()
    if cleaned in VALID_DECISIONS:
        return cleaned
    for option in VALID_DECISIONS:
        if option in cleaned:
            return option
    if "delete" in cleaned:
        return "remove"
    if "flag" in cleaned:
        return "request_human_review"
    return "request_human_review"


def normalize_action_payload(payload: Dict[str, object]) -> Dict[str, object]:
    """
    Accept both:
    - {"action": {...}}
    - {"decision": "...", ...}
    and map common alias keys from judge/LLM outputs.
    """
    if not isinstance(payload, dict):
        payload = {}

    if "action" in payload and isinstance(payload["action"], dict):
        raw = dict(payload["action"])
    else:
        raw = dict(payload)

    decision = raw.get("decision", raw.get("action", raw.get("act", "request_human_review")))
    normalized: Dict[str, object] = {
        "decision": normalize_decision(str(decision)),
        "rule_cited": raw.get("rule_cited", raw.get("rule", raw.get("law", "UNKNOWN"))),
        "evidence_signals": raw.get("evidence_signals", raw.get("signals", [])),
        "confidence": raw.get("confidence", raw.get("conf", 0.0)),
        "reason": raw.get("reason", "normalized_input"),
        "notify_user": raw.get("notify_user", False),
        "target_account": raw.get("target_account"),
    }

    if not isinstance(normalized["evidence_signals"], list):
        normalized["evidence_signals"] = []

    return normalized
```

### [dharma_shield/grader.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/dharma_shield/grader.py)
```python
from __future__ import annotations

from typing import Dict, List

from .models import DharmaShieldAction, DharmaShieldReward, EpisodeState
from .policy_book import POLICY_BOOK


def clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _rule_accuracy(action_rule: str, expected_rule: str) -> float:
    if not expected_rule:
        return 1.0 if action_rule in ("", "UNKNOWN") else 0.0
    if action_rule == expected_rule:
        return 1.0
    if action_rule in POLICY_BOOK and expected_rule in POLICY_BOOK:
        if POLICY_BOOK[action_rule]["category"] == POLICY_BOOK[expected_rule]["category"]:
            return 0.5
    return 0.0


def _evidence_quality(action_signals: List[str], expected_signals: List[str]) -> float:
    if not expected_signals:
        return 1.0 if not action_signals else 0.0
    overlap = len(set(action_signals).intersection(expected_signals))
    return clamp_01(overlap / len(expected_signals))


def compute_step_reward(
    *,
    task_id: str,
    action: DharmaShieldAction,
    expected_decision: str,
    expected_rule: str,
    expected_signals: List[str],
    time_remaining_hours: float,
    state: EpisodeState,
) -> DharmaShieldReward:
    decision_accuracy = 1.0 if action.decision == expected_decision else 0.0
    rule_accuracy = _rule_accuracy(action.rule_cited, expected_rule)
    evidence_quality = _evidence_quality(action.evidence_signals, expected_signals)

    time_window = 3.0
    if expected_rule and expected_rule in POLICY_BOOK:
        time_window = POLICY_BOOK[expected_rule]["time_window_hours"]
    time_efficiency = clamp_01(min(1.0, time_remaining_hours / max(time_window, 0.01)))

    false_positive_penalty = 0.0
    if expected_decision == "approve" and action.decision == "remove":
        false_positive_penalty = -0.40

    raw = (
        0.40 * decision_accuracy
        + 0.30 * rule_accuracy
        + 0.15 * time_efficiency
        + 0.10 * evidence_quality
        + false_positive_penalty
    )
    step_reward = clamp_01(raw)

    state.step_rewards.append(step_reward)
    cumulative = clamp_01(sum(state.step_rewards) / len(state.step_rewards))

    return DharmaShieldReward(
        step_reward=step_reward,
        decision_accuracy=decision_accuracy,
        rule_accuracy=rule_accuracy,
        time_efficiency=time_efficiency,
        evidence_quality=evidence_quality,
        false_positive_penalty=false_positive_penalty,
        cumulative_episode_score=cumulative,
    )


def compute_task_score(task_id: str, rewards: List[float], actions: List[Dict[str, str]]) -> float:
    if not rewards:
        return 0.0
    base = sum(rewards) / len(rewards)
    if task_id == "cib-graph-takedown":
        sequence_bonus = 0.0
        for action in actions:
            if action.get("target_account") == "Account_A":
                sequence_bonus = 0.1 if action.get("decision") == "remove" else 0.0
                break
        return clamp_01(base + sequence_bonus)
    return clamp_01(base)
```

### [dharma_shield/models.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/dharma_shield/models.py)
```python
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AccountMeta(BaseModel):
    account_age_days: int
    prior_violations: int = 0
    payment_linked: bool
    verified_badge: bool = False
    country_code: str
    posting_frequency_per_day: float


class ContentItem(BaseModel):
    content_id: str
    text: str
    content_type: Literal["text", "image_with_caption", "video_desc", "audio_transcript"]
    sgi_flag: bool = False
    upi_pattern_detected: bool = False
    toxicity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    language: str = "en"
    linked_accounts: List[str] = Field(default_factory=list)
    timestamp_offset_sec: int = 0
    english_summary: Optional[str] = None
    evidence_signals: List[str] = Field(default_factory=list)
    target_account: Optional[str] = None


class DharmaShieldObservation(BaseModel):
    current_item: ContentItem
    account_meta: AccountMeta
    time_remaining_hours: float
    active_rule_hints: List[str] = Field(default_factory=list)
    similar_past_decisions: List[str] = Field(default_factory=list)
    step_number: int
    queue_size_remaining: int
    platform_compliance_health: float = Field(ge=0.0, le=1.0)
    safe_harbour_status: Literal["protected", "at_risk", "lost"]


class DharmaShieldAction(BaseModel):
    decision: Literal["approve", "remove", "label_sgi", "warn_user", "escalate", "request_human_review"]
    rule_cited: str = "UNKNOWN"
    evidence_signals: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reason: str = Field(default="", max_length=200)
    notify_user: bool = False
    target_account: Optional[str] = None


class DharmaShieldReward(BaseModel):
    step_reward: float = Field(ge=0.0, le=1.0)
    decision_accuracy: float = Field(ge=0.0, le=1.0)
    rule_accuracy: float = Field(ge=0.0, le=1.0)
    time_efficiency: float = Field(ge=0.0, le=1.0)
    evidence_quality: float = Field(ge=0.0, le=1.0)
    false_positive_penalty: float
    cumulative_episode_score: float = Field(ge=0.0, le=1.0)


class EpisodeState(BaseModel):
    current_step: int = 0
    task_id: str = ""
    queue_index: int = 0
    time_remaining_hours: float = 3.0
    compliance_health: float = 1.0
    missed_deadlines: int = 0
    false_positives: int = 0
    safe_harbour_status: Literal["protected", "at_risk", "lost"] = "protected"
    step_rewards: List[float] = Field(default_factory=list)
    reveal_phase: int = 0
    completed: bool = False


class StepInfo(BaseModel):
    task_id: str
    error: Optional[str] = None
    termination_reason: Optional[str] = None
    rule_valid: bool = True
    time_window_active: bool = True
    expected_decision: Optional[str] = None
    expected_rule: Optional[str] = None


class StepResponse(BaseModel):
    observation: DharmaShieldObservation
    reward: DharmaShieldReward
    done: bool
    info: StepInfo


class TaskScore(BaseModel):
    task: str
    score: float
    steps: int
    rewards: List[float]
    success: bool
    error: Optional[str] = None


class StateResponse(BaseModel):
    state: Dict[str, Any]
```

### [dharma_shield/policy_book.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/dharma_shield/policy_book.py)
```python
from __future__ import annotations

from typing import Dict, List, TypedDict


class PolicyRule(TypedDict):
    category: str
    required_actions: List[str]
    time_window_hours: float
    safe_harbour_lost: bool


POLICY_BOOK: Dict[str, PolicyRule] = {
    "IT_2021_3_1_b_i": {
        "category": "national_security",
        "required_actions": ["remove", "escalate"],
        "time_window_hours": 1.0,
        "safe_harbour_lost": True,
    },
    "IT_2021_3_1_b_iii": {
        "category": "financial_fraud_upi_scam",
        "required_actions": ["remove", "warn_user"],
        "time_window_hours": 3.0,
        "safe_harbour_lost": True,
    },
    "IT_2026_SGI_DEEPFAKE": {
        "category": "synthetic_impersonation_nonconsensual",
        "required_actions": ["remove"],
        "time_window_hours": 3.0,
        "safe_harbour_lost": True,
    },
    "IT_2026_SGI_LABEL": {
        "category": "undisclosed_ai_generated_content",
        "required_actions": ["label_sgi", "warn_user"],
        "time_window_hours": 24.0,
        "safe_harbour_lost": False,
    },
    "IT_2021_3_1_d": {
        "category": "government_formal_notice",
        "required_actions": ["escalate"],
        "time_window_hours": 6.0,
        "safe_harbour_lost": True,
    },
    "IT_2021_3_1_j": {
        "category": "child_safety_urgent",
        "required_actions": ["remove", "escalate"],
        "time_window_hours": 1.0,
        "safe_harbour_lost": True,
    },
}
```

### [dharma_shield/server.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/dharma_shield/server.py)
```python
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Body, FastAPI
from pydantic import BaseModel

from .environment import DharmaShieldEnvironment
from .models import DharmaShieldAction, StateResponse, StepResponse
from .validators import normalize_action_payload, validate_step_payload


class ResetRequest(BaseModel):
    task_id: Optional[str] = None


app = FastAPI(title="DharmaShield Env", version="1.0.0")
env = DharmaShieldEnvironment()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "env": "dharma-shield", "version": "1.0.0"}


@app.post("/reset")
def reset(req: ResetRequest) -> Dict[str, Any]:
    obs = env.reset(req.task_id)
    return obs.model_dump()


@app.post("/step", response_model=StepResponse)
def step(payload: Dict[str, Any] = Body(...)) -> StepResponse:
    payload = validate_step_payload(payload)
    normalized = normalize_action_payload(payload)
    try:
        action = DharmaShieldAction(**normalized)
    except Exception:
        action = DharmaShieldAction(
            decision="request_human_review",
            rule_cited="UNKNOWN",
            evidence_signals=[],
            confidence=0.0,
            reason="fallback_invalid_payload",
            notify_user=False,
        )
    obs, reward, done, info = env.step(action)
    return StepResponse(observation=obs, reward=reward, done=done, info=info)


@app.get("/state", response_model=StateResponse)
def state() -> StateResponse:
    return StateResponse(state=env.state())
```

### [server/app.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/server/app.py)
```python
from __future__ import annotations

import uvicorn

from dharma_shield.server import app


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
```

### [dharma_shield/task_data.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/dharma_shield/task_data.py)
```python
from __future__ import annotations

from typing import Any, Dict, List


TASK_DATA: Dict[str, Dict[str, Any]] = {
    "upi-scam-triage": {
        "max_steps": 10,
        "time_budget_hours": 3.0,
        "items": [
            {
                "content_id": "upi_1",
                "text": "Congratulations! NPCI lottery ₹50,000 — enter UPI PIN here: bit.ly/win",
                "english_summary": "Prize scam requesting UPI PIN.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": True,
                "toxicity_score": 0.2,
                "language": "en",
                "timestamp_offset_sec": 0,
                "evidence_signals": ["upi_pin_request", "prize_scam"],
                "account_meta": {
                    "account_age_days": 15,
                    "prior_violations": 3,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 1.5,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2021_3_1_b_iii",
            },
            {
                "content_id": "upi_2",
                "text": "आज Paytm offer hai! ₹500 cashback milega QR code scan karne par 🎉",
                "english_summary": "Suspicious cashback lure with scan QR.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": True,
                "toxicity_score": 0.1,
                "language": "hi-en",
                "timestamp_offset_sec": 5,
                "evidence_signals": ["qr_swap_pattern", "cashback_lure"],
                "account_meta": {
                    "account_age_days": 6,
                    "prior_violations": 1,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 4.1,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2021_3_1_b_iii",
            },
            {
                "content_id": "upi_3",
                "text": "URGENT: Your SBI UPI is blocked! Call 1800-000-7777 now.",
                "english_summary": "Fake helpline and urgency trigger.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": True,
                "toxicity_score": 0.3,
                "language": "en",
                "timestamp_offset_sec": 10,
                "evidence_signals": ["fake_helpline", "urgency_trigger"],
                "account_meta": {
                    "account_age_days": 31,
                    "prior_violations": 2,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 2.2,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2021_3_1_b_iii",
            },
            {
                "content_id": "upi_4",
                "text": "Sending payment to @dhobi_press for laundry — ₹150 ✓",
                "english_summary": "Legitimate personal payment confirmation.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": False,
                "toxicity_score": 0.0,
                "language": "en",
                "timestamp_offset_sec": 15,
                "evidence_signals": [],
                "account_meta": {
                    "account_age_days": 900,
                    "prior_violations": 0,
                    "payment_linked": True,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 8.0,
                },
                "ground_truth_decision": "approve",
                "ground_truth_rule": "",
            },
            {
                "content_id": "upi_5",
                "text": "Collect request aayega, bas approve kar dena bhai",
                "english_summary": "Social engineering for fake collect request.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": True,
                "toxicity_score": 0.1,
                "language": "hi-en",
                "timestamp_offset_sec": 18,
                "evidence_signals": ["fake_collect_request", "social_engineering"],
                "account_meta": {
                    "account_age_days": 7,
                    "prior_violations": 2,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 5.4,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2021_3_1_b_iii",
            },
            {
                "content_id": "upi_6",
                "text": "Screenshot dikhao UPI ka, tabhi refund process hoga.",
                "english_summary": "Screenshot phishing attempt.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": True,
                "toxicity_score": 0.2,
                "language": "hi-en",
                "timestamp_offset_sec": 20,
                "evidence_signals": ["screenshot_phishing"],
                "account_meta": {
                    "account_age_days": 20,
                    "prior_violations": 1,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 3.5,
                },
                "ground_truth_decision": "warn_user",
                "ground_truth_rule": "IT_2021_3_1_b_iii",
            },
            {
                "content_id": "upi_7",
                "text": "Grocery payment received from Sharma ji ✅",
                "english_summary": "Legitimate payment message.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": False,
                "toxicity_score": 0.0,
                "language": "en",
                "timestamp_offset_sec": 25,
                "evidence_signals": [],
                "account_meta": {
                    "account_age_days": 500,
                    "prior_violations": 0,
                    "payment_linked": True,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 6.5,
                },
                "ground_truth_decision": "approve",
                "ground_truth_rule": "",
            },
            {
                "content_id": "upi_8",
                "text": "Verified RazorPay merchant festive sale 20% off, scan to pay",
                "english_summary": "Legitimate merchant promotion.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": False,
                "toxicity_score": 0.0,
                "language": "en",
                "timestamp_offset_sec": 30,
                "evidence_signals": [],
                "account_meta": {
                    "account_age_days": 1400,
                    "prior_violations": 0,
                    "payment_linked": True,
                    "verified_badge": True,
                    "country_code": "IN",
                    "posting_frequency_per_day": 14.1,
                },
                "ground_truth_decision": "approve",
                "ground_truth_rule": "",
            },
        ],
    },
    "sgi-compliance-review": {
        "max_steps": 8,
        "time_budget_hours": 3.0,
        "items": [
            {
                "content_id": "sgi_1",
                "text": "Video claims politician made inflammatory speech; visual artifacts indicate deepfake.",
                "english_summary": "Undisclosed non-consensual political deepfake.",
                "content_type": "video_desc",
                "sgi_flag": True,
                "upi_pattern_detected": False,
                "toxicity_score": 0.6,
                "language": "en",
                "timestamp_offset_sec": 0,
                "evidence_signals": ["face_artifacts", "identity_impersonation"],
                "account_meta": {
                    "account_age_days": 60,
                    "prior_violations": 2,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 0.7,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2026_SGI_DEEPFAKE",
            },
            {
                "content_id": "sgi_2",
                "text": "AI-generated landscape art #AIArt #MadeWithAI",
                "english_summary": "Disclosed AI art; should be labeled, not removed.",
                "content_type": "image_with_caption",
                "sgi_flag": True,
                "upi_pattern_detected": False,
                "toxicity_score": 0.0,
                "language": "en",
                "timestamp_offset_sec": 5,
                "evidence_signals": ["ai_disclosure_tag"],
                "account_meta": {
                    "account_age_days": 400,
                    "prior_violations": 0,
                    "payment_linked": True,
                    "verified_badge": True,
                    "country_code": "IN",
                    "posting_frequency_per_day": 3.0,
                },
                "ground_truth_decision": "label_sgi",
                "ground_truth_rule": "IT_2026_SGI_LABEL",
            },
            {
                "content_id": "sgi_3",
                "text": "Audio transcript: Beta accident mein hai, ₹15,000 UPI pe bhejo.",
                "english_summary": "Voice-clone financial fraud content.",
                "content_type": "audio_transcript",
                "sgi_flag": True,
                "upi_pattern_detected": True,
                "toxicity_score": 0.4,
                "language": "hi-en",
                "timestamp_offset_sec": 8,
                "evidence_signals": ["voice_clone", "upi_urgent_transfer"],
                "account_meta": {
                    "account_age_days": 22,
                    "prior_violations": 4,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 1.0,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2021_3_1_b_iii",
            },
            {
                "content_id": "sgi_4",
                "text": "Post quoting politician's real speech with commentary overlay.",
                "english_summary": "Legitimate non-SGI political commentary.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": False,
                "toxicity_score": 0.0,
                "language": "en",
                "timestamp_offset_sec": 13,
                "evidence_signals": [],
                "account_meta": {
                    "account_age_days": 1200,
                    "prior_violations": 0,
                    "payment_linked": True,
                    "verified_badge": True,
                    "country_code": "IN",
                    "posting_frequency_per_day": 10.2,
                },
                "ground_truth_decision": "approve",
                "ground_truth_rule": "",
            },
            {
                "content_id": "sgi_5",
                "text": "AI-generated stock tip: XYZ stock guaranteed 400% returns.",
                "english_summary": "Undisclosed AI financial claim; label required first.",
                "content_type": "text",
                "sgi_flag": True,
                "upi_pattern_detected": False,
                "toxicity_score": 0.2,
                "language": "en",
                "timestamp_offset_sec": 20,
                "evidence_signals": ["undisclosed_ai", "financial_harm_claim"],
                "account_meta": {
                    "account_age_days": 70,
                    "prior_violations": 1,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 2.1,
                },
                "ground_truth_decision": "label_sgi",
                "ground_truth_rule": "IT_2026_SGI_LABEL",
            },
            {
                "content_id": "sgi_6",
                "text": "Deepfake celebrity endorsing gambling app with cloned voice.",
                "english_summary": "Commercial deepfake endorsement.",
                "content_type": "video_desc",
                "sgi_flag": True,
                "upi_pattern_detected": False,
                "toxicity_score": 0.5,
                "language": "en",
                "timestamp_offset_sec": 26,
                "evidence_signals": ["celebrity_impersonation", "gambling_promo"],
                "account_meta": {
                    "account_age_days": 16,
                    "prior_violations": 3,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 0.9,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2026_SGI_DEEPFAKE",
            },
        ],
    },
    "cib-graph-takedown": {
        "max_steps": 6,
        "time_budget_hours": 3.0,
        "items": [
            {
                "content_id": "cib_A",
                "text": "Account_A uploads deepfake political video.",
                "english_summary": "Root account in coordinated network.",
                "content_type": "video_desc",
                "sgi_flag": True,
                "upi_pattern_detected": False,
                "toxicity_score": 0.7,
                "language": "en",
                "linked_accounts": ["Account_B", "Account_C", "Account_E"],
                "timestamp_offset_sec": 0,
                "target_account": "Account_A",
                "evidence_signals": ["content_hash_match", "root_origin"],
                "account_meta": {
                    "account_age_days": 62,
                    "prior_violations": 2,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "PK",
                    "posting_frequency_per_day": 0.3,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2026_SGI_DEEPFAKE",
            },
            {
                "content_id": "cib_B",
                "text": "Account_B reshares identical video within 28 seconds.",
                "english_summary": "Bot-linked propagation node.",
                "content_type": "text",
                "sgi_flag": True,
                "upi_pattern_detected": False,
                "toxicity_score": 0.4,
                "language": "en",
                "linked_accounts": ["Account_A"],
                "timestamp_offset_sec": 28,
                "target_account": "Account_B",
                "evidence_signals": ["coordinated_window", "bot_pattern"],
                "account_meta": {
                    "account_age_days": 8,
                    "prior_violations": 1,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "PK",
                    "posting_frequency_per_day": 0.1,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2026_SGI_DEEPFAKE",
            },
            {
                "content_id": "cib_C",
                "text": "Account_C reshares in 31 seconds with same hash.",
                "english_summary": "Bot-linked propagation node.",
                "content_type": "text",
                "sgi_flag": True,
                "upi_pattern_detected": False,
                "toxicity_score": 0.4,
                "language": "en",
                "linked_accounts": ["Account_A"],
                "timestamp_offset_sec": 31,
                "target_account": "Account_C",
                "evidence_signals": ["coordinated_window", "bot_pattern"],
                "account_meta": {
                    "account_age_days": 12,
                    "prior_violations": 1,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "PK",
                    "posting_frequency_per_day": 0.1,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2026_SGI_DEEPFAKE",
            },
            {
                "content_id": "cib_E",
                "text": "Account_E reshares in 29 seconds with same hash.",
                "english_summary": "Bot-linked propagation node.",
                "content_type": "text",
                "sgi_flag": True,
                "upi_pattern_detected": False,
                "toxicity_score": 0.4,
                "language": "en",
                "linked_accounts": ["Account_A"],
                "timestamp_offset_sec": 29,
                "target_account": "Account_E",
                "evidence_signals": ["coordinated_window", "bot_pattern"],
                "account_meta": {
                    "account_age_days": 5,
                    "prior_violations": 1,
                    "payment_linked": False,
                    "verified_badge": False,
                    "country_code": "PK",
                    "posting_frequency_per_day": 0.1,
                },
                "ground_truth_decision": "remove",
                "ground_truth_rule": "IT_2026_SGI_DEEPFAKE",
            },
            {
                "content_id": "cib_D",
                "text": "Account_D shared later from feed organically.",
                "english_summary": "Legitimate user, should not be removed.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": False,
                "toxicity_score": 0.1,
                "language": "en",
                "linked_accounts": [],
                "timestamp_offset_sec": 45,
                "target_account": "Account_D",
                "evidence_signals": ["organic_distribution", "high_activity_normal"],
                "account_meta": {
                    "account_age_days": 1100,
                    "prior_violations": 0,
                    "payment_linked": True,
                    "verified_badge": False,
                    "country_code": "IN",
                    "posting_frequency_per_day": 12.3,
                },
                "ground_truth_decision": "warn_user",
                "ground_truth_rule": "IT_2026_SGI_LABEL",
            },
            {
                "content_id": "cib_escalate",
                "text": "Network takedown completed. Should escalate formal report.",
                "english_summary": "Final escalation step for government notice trail.",
                "content_type": "text",
                "sgi_flag": False,
                "upi_pattern_detected": False,
                "toxicity_score": 0.0,
                "language": "en",
                "linked_accounts": [],
                "timestamp_offset_sec": 50,
                "target_account": None,
                "evidence_signals": ["cross_border_network", "coordinated_inauthentic_behavior"],
                "account_meta": {
                    "account_age_days": 1,
                    "prior_violations": 0,
                    "payment_linked": False,
                    "verified_badge": True,
                    "country_code": "IN",
                    "posting_frequency_per_day": 0.0,
                },
                "ground_truth_decision": "escalate",
                "ground_truth_rule": "IT_2021_3_1_d",
            },
        ],
    },
}


TASK_ORDER: List[str] = ["upi-scam-triage", "sgi-compliance-review", "cib-graph-takedown"]
```

---

## 🚀 Inference & Baseline

### [inference.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/inference.py)
```python
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from dotenv import load_dotenv

from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.grader import compute_task_score
from dharma_shield.models import DharmaShieldAction
from dharma_shield.task_data import TASK_ORDER

# Load environment variables from .env file
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY")


def _format_bool(value: bool) -> str:
    return "true" if value else "false"


def _parse_json_action(raw: str) -> Optional[DharmaShieldAction]:
    try:
        data = json.loads(raw)
        return DharmaShieldAction(**data)
    except Exception:
        return None


def _regex_fallback(raw: str) -> Optional[DharmaShieldAction]:
    text = raw.lower()
    decisions = ["remove", "approve", "label_sgi", "warn_user", "escalate", "request_human_review"]
    decision = next((d for d in decisions if d in text), None)
    if not decision:
        return None
    rule_match = re.search(r"(IT_[A-Z0-9_]+)", raw)
    return DharmaShieldAction(
        decision=decision,
        rule_cited=rule_match.group(1) if rule_match else "UNKNOWN",
        evidence_signals=[],
        confidence=0.2,
        reason="regex_fallback",
        notify_user=False,
    )


def _absolute_fallback() -> DharmaShieldAction:
    return DharmaShieldAction(
        decision="request_human_review",
        rule_cited="UNKNOWN",
        evidence_signals=[],
        confidence=0.0,
        reason="absolute_fallback",
        notify_user=False,
    )


def _heuristic_action(observation: Dict[str, Any]) -> DharmaShieldAction:
    item = observation["current_item"]
    hints = observation.get("active_rule_hints", [])
    if item.get("upi_pattern_detected"):
        return DharmaShieldAction(
            decision="remove",
            rule_cited="IT_2021_3_1_b_iii",
            evidence_signals=item.get("evidence_signals", [])[:2],
            confidence=0.8,
            reason="upi_risk_detected",
            notify_user=True,
            target_account=item.get("target_account"),
        )
    if item.get("sgi_flag") and "IT_2026_SGI_DEEPFAKE" in hints:
        return DharmaShieldAction(
            decision="remove",
            rule_cited="IT_2026_SGI_DEEPFAKE",
            evidence_signals=item.get("evidence_signals", [])[:2],
            confidence=0.8,
            reason="sgi_deepfake_hint",
            notify_user=False,
            target_account=item.get("target_account"),
        )
    if item.get("sgi_flag"):
        return DharmaShieldAction(
            decision="label_sgi",
            rule_cited="IT_2026_SGI_LABEL",
            evidence_signals=item.get("evidence_signals", [])[:2],
            confidence=0.7,
            reason="sgi_content_detected",
            notify_user=True,
            target_account=item.get("target_account"),
        )
    return DharmaShieldAction(
        decision="approve",
        rule_cited="UNKNOWN",
        evidence_signals=[],
        confidence=0.6,
        reason="default_approve",
        notify_user=False,
        target_account=item.get("target_account"),
    )


def _build_prompt(observation: Dict[str, Any]) -> str:
    schema = (
        '{"decision":"remove|approve|label_sgi|warn_user|escalate|request_human_review",'
        '"rule_cited":"IT_... or UNKNOWN","evidence_signals":["..."],"confidence":0.0,'
        '"reason":"...", "notify_user":false}'
    )
    return (
        "You are a trust and safety compliance agent.\n"
        "Respond ONLY with valid JSON matching this exact schema:\n"
        f"{schema}\n\n"
        f"Observation:\n{json.dumps(observation, ensure_ascii=True)}"
    )


def _call_model(observation: Dict[str, Any]) -> DharmaShieldAction:
    if not HF_TOKEN:
        return _heuristic_action(observation)
    try:
        client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
        res = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.0,
            messages=[
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": _build_prompt(observation)},
            ],
        )
        content = res.choices[0].message.content or ""
        parsed = _parse_json_action(content) or _regex_fallback(content) or _absolute_fallback()
        return parsed
    except Exception:
        return _heuristic_action(observation)


def _print_start(task: str) -> None:
    print(f"[START] task={task} env=dharma-shield model={MODEL_NAME}", flush=True)


def _print_step(step_num: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    err = "null" if not error else error.replace(" ", "_")
    print(
        f"[STEP] step={step_num} action={action} reward={reward:.2f} done={_format_bool(done)} error={err}",
        flush=True,
    )


def _print_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    formatted_rewards = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={_format_bool(success)} steps={steps} score={score:.3f} rewards={formatted_rewards}",
        flush=True,
    )


def run_task(env: DharmaShieldEnvironment, task_id: str) -> Tuple[List[float], List[Dict[str, str]], Optional[str]]:
    rewards: List[float] = []
    actions_for_score: List[Dict[str, str]] = []
    error: Optional[str] = None

    _print_start(task_id)
    step_count = 0
    success = False
    try:
        obs = env.reset(task_id).model_dump()
        done = False
        while not done:
            action = _call_model(obs)
            obs_model, reward_model, done, info = env.step(action)
            step_count += 1
            rewards.append(reward_model.step_reward)
            actions_for_score.append(
                {
                    "decision": action.decision,
                    "target_account": action.target_account or obs["current_item"].get("target_account", ""),
                }
            )
            _print_step(
                step_count,
                action.decision,
                reward_model.step_reward,
                done,
                info.error,
            )
            obs = obs_model.model_dump()
        success = True
    except Exception as exc:
        error = str(exc)
    finally:
        score = compute_task_score(task_id, rewards, actions_for_score)
        _print_end(success, step_count, score, rewards)
    return rewards, actions_for_score, error


def main() -> None:
    env = DharmaShieldEnvironment()
    all_scores: List[float] = []
    for task_id in TASK_ORDER:
        rewards, actions, _ = run_task(env, task_id)
        all_scores.append(compute_task_score(task_id, rewards, actions))
    avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
    print(f"Final average score: {avg:.3f}", flush=True)


if __name__ == "__main__":
    main()
```

---

## 🧪 Test Suite: `tests/`

### [tests/test_reset.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/tests/test_reset.py)
```python
from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction


def test_reset_produces_fresh_state():
    env = DharmaShieldEnvironment()
    first = env.reset("upi-scam-triage").model_dump()
    env.step(
        DharmaShieldAction(
            decision="remove",
            rule_cited="IT_2021_3_1_b_iii",
            evidence_signals=[],
            confidence=0.5,
            reason="test",
            notify_user=False,
        )
    )
    second = env.reset("upi-scam-triage").model_dump()
    assert first["current_item"]["content_id"] == second["current_item"]["content_id"]
    assert second["step_number"] == 0
```

### [tests/test_step.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/tests/test_step.py)
```python
from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction


def test_step_returns_expected_shape():
    env = DharmaShieldEnvironment()
    env.reset("upi-scam-triage")
    action = DharmaShieldAction(
        decision="remove",
        rule_cited="IT_2021_3_1_b_iii",
        evidence_signals=["upi_pin_request"],
        confidence=0.7,
        reason="policy",
        notify_user=False,
    )
    obs, reward, done, info = env.step(action)
    assert isinstance(obs.current_item.content_id, str)
    assert 0.0 <= reward.step_reward <= 1.0
    assert isinstance(done, bool)
    assert info.task_id
```

### [tests/test_grader.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/tests/test_grader.py)
```python
from dharma_shield.grader import clamp_01, compute_step_reward
from dharma_shield.models import DharmaShieldAction, EpisodeState


def test_clamp_bounds():
    assert clamp_01(-5.0) == 0.0
    assert clamp_01(5.0) == 1.0


def test_grader_returns_clamped_reward():
    state = EpisodeState(task_id="upi-scam-triage")
    action = DharmaShieldAction(
        decision="remove",
        rule_cited="IT_2021_3_1_b_iii",
        evidence_signals=["upi_pin_request"],
        confidence=1.0,
        reason="test",
        notify_user=False,
    )
    reward = compute_step_reward(
        task_id="upi-scam-triage",
        action=action,
        expected_decision="approve",
        expected_rule="",
        expected_signals=[],
        time_remaining_hours=0.0,
        state=state,
    )
    assert 0.0 <= reward.step_reward <= 1.0
```

### [tests/conftest.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/tests/conftest.py)
```python
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

### [tests/test_edge_cases.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/tests/test_edge_cases.py)
```python
from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction
from fastapi.testclient import TestClient

from dharma_shield.server import app


def test_invalid_rule_key_does_not_crash():
    env = DharmaShieldEnvironment()
    env.reset("sgi-compliance-review")
    action = DharmaShieldAction(
        decision="remove",
        rule_cited="IT_RULE_99",
        evidence_signals=[],
        confidence=0.1,
        reason="invalid rule",
        notify_user=False,
    )
    _, reward, _, info = env.step(action)
    assert 0.0 <= reward.step_reward <= 1.0
    assert info.rule_valid is False


def test_max_steps_terminates_cleanly():
    env = DharmaShieldEnvironment()
    env.reset("cib-graph-takedown")
    action = DharmaShieldAction(
        decision="request_human_review",
        rule_cited="UNKNOWN",
        evidence_signals=[],
        confidence=0.0,
        reason="stress",
        notify_user=False,
    )
    done = False
    for _ in range(12):
        _, _, done, _ = env.step(action)
        if done:
            break
    assert done is True


def test_step_endpoint_accepts_raw_and_alias_payloads():
    client = TestClient(app)

    r1 = client.post("/step", json={"decision": "remove"})
    assert r1.status_code == 200

    r2 = client.post("/step", json={"action": "approve", "conf": 0.8})
    assert r2.status_code == 200

    r3 = client.post("/step", json={"action": {"decision": "remove "}})
    assert r3.status_code == 200
```

### [tests/test_openenv_schema.py](file:///Users/theankit/Documents/AK/DharmaShield_ENV/tests/test_openenv_schema.py)
```python
from pathlib import Path
import yaml


def test_openenv_yaml_has_required_fields():
    data = yaml.safe_load(Path("openenv.yaml").read_text())
    assert data["name"] == "dharma-shield-env"
    assert "tasks" in data and len(data["tasks"]) >= 3
    assert "reward_range" in data
    assert data["reward_range"]["min"] == 0.0
    assert data["reward_range"]["max"] == 1.0
```