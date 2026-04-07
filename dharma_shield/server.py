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
