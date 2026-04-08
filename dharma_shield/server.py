from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI
from pydantic import BaseModel

from .environment import DharmaShieldEnvironment
from .models import DharmaShieldAction, StateResponse, StepResponse
from .runtime_config import SAFE_MODE, VERBOSE
from .validators import normalize_action_payload, validate_step_payload


class ResetRequest(BaseModel):
    task_id: Optional[str] = None


app = FastAPI(title="DharmaShield Env", version="3.1.0")
env = DharmaShieldEnvironment()
logger = logging.getLogger(__name__)
_episode_log: deque = deque(maxlen=20)
_current_episode_steps: list = []


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "dharma-shield",
        "version": "3.1.0",
        "docs": "/docs",
        "health": "/health",
        "tasks": list(env.task_order),
        "openenv": True,
        "safe_mode": SAFE_MODE,
        "verbose": VERBOSE,
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "env": "dharma-shield", "version": "3.1.0"}


@app.post("/reset")
def reset(req: Optional[ResetRequest] = Body(default=None)) -> Dict[str, Any]:
    _current_episode_steps.clear()
    task_id = req.task_id if req else None
    obs = env.reset(task_id)
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
    started = time.time()
    obs, reward, done, info = env.step(action)
    latency_ms = (time.time() - started) * 1000.0
    _current_episode_steps.append(
        {
            "step": env.state_data.current_step,
            "decision": action.decision,
            "rule_cited": action.rule_cited,
            "reward": reward.step_reward,
            "latency_ms": latency_ms,
            "done": done,
        }
    )
    if done:
        _episode_log.append(
            {
                "task_id": env.state_data.task_id,
                "steps": list(_current_episode_steps),
                "avg_reward": sum(s["reward"] for s in _current_episode_steps) / max(len(_current_episode_steps), 1),
                "done": True,
            }
        )
        _current_episode_steps.clear()
    return StepResponse(observation=obs, reward=reward, done=done, info=info)


@app.get("/state", response_model=StateResponse)
def state() -> StateResponse:
    return StateResponse(state=env.state())


@app.get("/episodes")
def get_episodes() -> Dict[str, Any]:
    return {"total_logged": len(_episode_log), "episodes": list(_episode_log)}


# Mount Gradio UI at /ui with non-fatal fallback.
try:
    import gradio as gr

    from .ui import build_ui

    _gradio_demo = build_ui()
    app = gr.mount_gradio_app(app, _gradio_demo, path="/ui")
except Exception as exc:  # pragma: no cover - optional UI dependency
    logger.warning("Gradio UI mount skipped: %s", exc)
