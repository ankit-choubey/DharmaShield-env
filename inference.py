from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
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
REQUIRE_HF_ROUTER = os.getenv("REQUIRE_HF_ROUTER", "false").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class RouterStats:
    mode: str
    successes: int = 0
    fallbacks: int = 0
    last_provider_model: str = ""


ROUTER_STATS = RouterStats(mode="strict" if REQUIRE_HF_ROUTER else "permissive")


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


def _log_router(status: str, detail: str = "") -> None:
    suffix = f" detail={detail}" if detail else ""
    print(f"[ROUTER] source=hf status={status}{suffix}", flush=True)


def _call_model(observation: Dict[str, Any]) -> DharmaShieldAction:
    if not HF_TOKEN:
        ROUTER_STATS.fallbacks += 1
        _log_router("fallback", "missing_token")
        if REQUIRE_HF_ROUTER:
            raise RuntimeError("strict_router_mode: missing HF token")
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
        provider_model = getattr(res, "model", MODEL_NAME) or MODEL_NAME
        ROUTER_STATS.last_provider_model = provider_model
        ROUTER_STATS.successes += 1
        _log_router("ok", f"base={API_BASE_URL} model={provider_model}")
        parsed = _parse_json_action(content) or _regex_fallback(content) or _absolute_fallback()
        return parsed
    except Exception as exc:
        ROUTER_STATS.fallbacks += 1
        _log_router("fallback", str(exc).replace(" ", "_")[:120])
        if REQUIRE_HF_ROUTER:
            raise RuntimeError(f"strict_router_mode: router failure: {exc}") from exc
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
    task_rows: List[Tuple[str, float, int]] = []
    for task_id in TASK_ORDER:
        rewards, actions, _ = run_task(env, task_id)
        score = compute_task_score(task_id, rewards, actions)
        all_scores.append(score)
        task_rows.append((task_id, score, len(rewards)))
    avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
    print(
        f"[ROUTER_SUMMARY] mode={ROUTER_STATS.mode} successes={ROUTER_STATS.successes} "
        f"fallbacks={ROUTER_STATS.fallbacks} base={API_BASE_URL} model={MODEL_NAME} "
        f"provider_model={ROUTER_STATS.last_provider_model or MODEL_NAME}",
        flush=True,
    )
    for task_id, score, steps in task_rows:
        print(f"[BASELINE] task={task_id} score={score:.3f} steps={steps}", flush=True)
    print(f"Final average score: {avg:.3f}", flush=True)
    if REQUIRE_HF_ROUTER and ROUTER_STATS.fallbacks > 0:
        raise SystemExit("Strict router mode failed: fallback path used.")


if __name__ == "__main__":
    main()
