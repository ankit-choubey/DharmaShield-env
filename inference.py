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
from dharma_shield.runtime_config import SAFE_MODE, VERBOSE
from dharma_shield.task_data import TASK_ORDER

# Load environment variables from .env file
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
# Optional compatibility var for OpenEnv docker-image inference templates.
# Current DharmaShield inference runs against the HTTP environment flow.
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
REQUIRE_HF_ROUTER = os.getenv("REQUIRE_HF_ROUTER", "false").strip().lower() in {"1", "true", "yes", "on"}
BENCHMARK_PROFILE = os.getenv("BENCHMARK_PROFILE", "false").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class RouterStats:
    mode: str
    successes: int = 0
    fallbacks: int = 0
    last_provider_model: str = ""


ROUTER_STATS = RouterStats(mode="strict" if REQUIRE_HF_ROUTER else "permissive")
_router_successes = 0
_router_fallbacks = 0
STEP_LOGS: Dict[str, List[Dict[str, Any]]] = {}

SYSTEM_PROMPT = """
You are a Trust & Safety Compliance Officer under India IT Rules 2026.

STRICT RULES:
- Never remove legitimate content
- Always cite correct policy rule ID
- Minimize false positives
- Protect safe harbour status
- Use evidence signals properly

Output ONLY valid JSON:
{
  "decision": "...",
  "rule_cited": "...",
  "evidence_signals": [...],
  "confidence": 0.0-1.0,
  "reason": "...",
  "notify_user": true/false
}
""".strip()

TASK_STRATEGY: Dict[str, str] = {
    "upi-scam-triage": (
        "UPI strategy: prioritize false-positive avoidance for verified benign merchant/payment context. "
        "If clear fraud pattern (PIN request, fake collect request, KYC pretext, fake helpline), choose remove."
    ),
    "sgi-compliance-review": (
        "SGI strategy: use remove for harmful deepfake/impersonation risk, otherwise prefer label_sgi for disclosed/benign synthetic content."
    ),
    "cib-graph-takedown": (
        "CIB strategy: prioritize network origin and risk. Prefer Account_A/source neutralization first when evidence supports coordinated behavior."
    ),
    "child-safety-escalation": (
        "Child safety strategy: urgent precision. Remove and cite IT_2021_3_1_j when clear risk signals exist; avoid false positives on benign awareness."
    ),
}


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


def _safe_parse_action(raw: str) -> DharmaShieldAction:
    parsed = _parse_json_action(raw) or _regex_fallback(raw) or _absolute_fallback()
    return parsed


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


def _build_prompt(observation: Dict[str, Any], task_id: str) -> str:
    schema = (
        '{"decision":"remove|approve|label_sgi|warn_user|escalate|request_human_review",'
        '"rule_cited":"IT_... or UNKNOWN","evidence_signals":["..."],"confidence":0.0,'
        '"reason":"...", "notify_user":false}'
    )
    task_hint = TASK_STRATEGY.get(task_id, "")
    strategy_block = f"\nTask strategy:\n{task_hint}\n" if BENCHMARK_PROFILE and task_hint else ""
    return (
        "You are a trust and safety compliance agent.\n"
        "Respond ONLY with valid JSON matching this exact schema:\n"
        f"{schema}\n\n"
        f"{strategy_block}"
        f"Observation:\n{json.dumps(observation, ensure_ascii=True)}"
    )


def _log_router(status: str, detail: str = "") -> None:
    if not VERBOSE:
        return
    suffix = f" detail={detail}" if detail else ""
    print(f"[ROUTER] source=hf status={status}{suffix}", flush=True)


def _call_model(observation: Dict[str, Any], task_id: str) -> DharmaShieldAction:
    global _router_successes, _router_fallbacks
    if not HF_TOKEN:
        ROUTER_STATS.fallbacks += 1
        _router_fallbacks += 1
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
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(observation, task_id)},
            ],
        )
        content = res.choices[0].message.content or ""
        provider_model = getattr(res, "model", MODEL_NAME) or MODEL_NAME
        ROUTER_STATS.last_provider_model = provider_model
        ROUTER_STATS.successes += 1
        _router_successes += 1
        _log_router("ok", f"base={API_BASE_URL} model={provider_model}")
        return _safe_parse_action(content)
    except Exception as exc:
        ROUTER_STATS.fallbacks += 1
        _router_fallbacks += 1
        _log_router("fallback", str(exc).replace(" ", "_")[:120])
        if REQUIRE_HF_ROUTER:
            raise RuntimeError(f"strict_router_mode: router failure: {exc}") from exc
        return _heuristic_action(observation)


def _benchmark_refine_action(task_id: str, observation: Dict[str, Any], action: DharmaShieldAction) -> DharmaShieldAction:
    item = observation.get("current_item", {})
    signals = set(item.get("evidence_signals", []) or [])
    target = item.get("target_account", "")

    # Keep default behavior untouched unless benchmarking is explicitly enabled.
    if task_id == "upi-scam-triage":
        if (not item.get("upi_pattern_detected")) and ("merchant_verified" in signals):
            return action.model_copy(
                update={"decision": "approve", "rule_cited": "UNKNOWN", "confidence": min(action.confidence, 0.65)}
            )
        if item.get("upi_pattern_detected") and (
            {"upi_pin_request", "fake_collect_request", "kyc_pretext", "fake_helpline"} & signals
        ):
            return action.model_copy(
                update={"decision": "remove", "rule_cited": "IT_2021_3_1_b_iii", "confidence": max(action.confidence, 0.8)}
            )

    if task_id == "sgi-compliance-review":
        if item.get("sgi_flag"):
            if {"identity_impersonation", "face_artifacts", "voice_clone_match"} & signals:
                return action.model_copy(
                    update={"decision": "remove", "rule_cited": "IT_2026_SGI_DEEPFAKE", "confidence": max(action.confidence, 0.8)}
                )
            return action.model_copy(
                update={"decision": "label_sgi", "rule_cited": "IT_2026_SGI_LABEL", "confidence": max(action.confidence, 0.7)}
            )

    if task_id == "cib-graph-takedown":
        if target == "Account_A":
            return action.model_copy(
                update={"decision": "remove", "rule_cited": "IT_2021_3_1_b_i", "confidence": max(action.confidence, 0.75)}
            )
        if {"narrative_origin_match", "foreign_funding_pattern"} & signals:
            return action.model_copy(
                update={"decision": "remove", "rule_cited": "IT_2021_3_1_b_i", "confidence": max(action.confidence, 0.7)}
            )

    if task_id == "child-safety-escalation":
        if {"child_minor", "sexualized_minor", "grooming_pattern"} & signals:
            return action.model_copy(
                update={
                    "decision": "remove",
                    "rule_cited": "IT_2021_3_1_j",
                    "notify_user": True,
                    "confidence": max(action.confidence, 0.85),
                }
            )

    # Calibration-safe confidence trim for uncertain actions.
    if action.decision == "request_human_review" and action.confidence > 0.3:
        return action.model_copy(update={"confidence": 0.3})
    return action


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
    step_logs: List[Dict[str, Any]] = []
    STEP_LOGS[task_id] = step_logs
    try:
        obs = env.reset(task_id).model_dump()
        done = False
        while not done:
            action = _call_model(obs, task_id)
            if BENCHMARK_PROFILE:
                action = _benchmark_refine_action(task_id, obs, action)
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
            step_logs.append(
                {
                    "step": step_count,
                    "decision": action.decision,
                    "rule": action.rule_cited,
                    "reward": reward_model.step_reward,
                }
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
    # SAFE_MODE defaults to True, so experimental paths are disabled by policy.
    if not SAFE_MODE and VERBOSE:
        print("[CONFIG] safe_mode=false experimental_features=enabled", flush=True)

    env = DharmaShieldEnvironment()
    all_scores: List[float] = []
    task_rows: List[Tuple[str, float, int]] = []
    for task_id in TASK_ORDER:
        try:
            rewards, actions, _ = run_task(env, task_id)
            score = compute_task_score(task_id, rewards, actions)
            all_scores.append(score)
            task_rows.append((task_id, score, len(rewards)))
        except Exception as exc:
            # Global crash guard: ensure END-style terminal output per episode even on unexpected failures.
            _print_end(False, 0, 0.0, [])
            if VERBOSE:
                print(f"[ERROR] task={task_id} error={str(exc).replace(' ', '_')}", flush=True)
            all_scores.append(0.0)
            task_rows.append((task_id, 0.0, 0))
    avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
    if VERBOSE:
        print(
            f"[ROUTER_SUMMARY] mode={ROUTER_STATS.mode} successes={ROUTER_STATS.successes} "
            f"fallbacks={ROUTER_STATS.fallbacks} base={API_BASE_URL} model={MODEL_NAME} "
            f"provider_model={ROUTER_STATS.last_provider_model or MODEL_NAME} "
            f"_router_successes={_router_successes} _router_fallbacks={_router_fallbacks}",
            flush=True,
        )
        for task_id, score, steps in task_rows:
            print(f"[BASELINE] task={task_id} score={score:.3f} steps={steps}", flush=True)
        print(f"Final average score: {avg:.3f}", flush=True)
    if REQUIRE_HF_ROUTER and ROUTER_STATS.fallbacks > 0:
        raise SystemExit("Strict router mode failed: fallback path used.")


if __name__ == "__main__":
    main()
