from __future__ import annotations

from typing import Dict, List

from .models import DharmaShieldAction, DharmaShieldReward, EpisodeState
from .policy_book import POLICY_BOOK


def clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


DEFAULT_REWARD_WEIGHTS: Dict[str, float] = {
    "decision": 0.35,
    "rule": 0.25,
    "time": 0.15,
    "evidence": 0.20,
    "reason": 0.05,
}


TASK_REWARD_WEIGHTS: Dict[str, Dict[str, float]] = {
    "upi-scam-triage": {
        "decision": 0.35,
        "rule": 0.25,
        "time": 0.20,
        "evidence": 0.15,
        "reason": 0.05,
    },
    "sgi-compliance-review": {
        "decision": 0.30,
        "rule": 0.35,
        "time": 0.15,
        "evidence": 0.15,
        "reason": 0.05,
    },
    "cib-graph-takedown": {
        "decision": 0.35,
        "rule": 0.25,
        "time": 0.15,
        "evidence": 0.15,
        "reason": 0.10,
    },
    "child-safety-escalation": {
        "decision": 0.40,
        "rule": 0.25,
        "time": 0.20,
        "evidence": 0.10,
        "reason": 0.05,
    },
}


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


def _reason_quality(action_reason: str, expected_signals: List[str], expected_decision: str) -> float:
    if not action_reason:
        return 0.5

    reason = action_reason.lower()
    signal_hits = 0
    for signal in expected_signals:
        token = signal.replace("_", " ").lower()
        if token and token in reason:
            signal_hits += 1
    signal_score = signal_hits / max(len(expected_signals), 1) if expected_signals else 1.0

    decision_markers = {
        "remove": ["remove", "takedown", "violation", "harm"],
        "approve": ["approve", "legitimate", "safe", "genuine"],
        "label_sgi": ["label", "sgi", "disclosure", "ai-generated"],
        "warn_user": ["warn", "caution", "risk"],
        "escalate": ["escalate", "authority", "urgent", "report"],
        "request_human_review": ["review", "uncertain", "manual"],
    }
    consistency = 0.0
    for marker in decision_markers.get(expected_decision, []):
        if marker in reason:
            consistency = 1.0
            break

    return clamp_01(0.6 * signal_score + 0.4 * consistency)


def _calibration_score(confidence: float, decision_accuracy: float) -> float:
    raw_calibration = 1.0 - (confidence - decision_accuracy) ** 2
    delta = (raw_calibration - 0.75) * 0.10
    return max(-0.05, min(0.05, delta))


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
    weights = TASK_REWARD_WEIGHTS.get(task_id, DEFAULT_REWARD_WEIGHTS)
    decision_accuracy = 1.0 if action.decision == expected_decision else 0.0
    rule_accuracy = _rule_accuracy(action.rule_cited, expected_rule)
    evidence_quality = _evidence_quality(action.evidence_signals, expected_signals)
    reason_quality = _reason_quality(action.reason, expected_signals, expected_decision)

    time_window = 3.0
    if expected_rule and expected_rule in POLICY_BOOK:
        time_window = POLICY_BOOK[expected_rule]["time_window_hours"]
    time_efficiency = clamp_01(min(1.0, time_remaining_hours / max(time_window, 0.01)))

    false_positive_penalty = 0.0
    if expected_decision == "approve" and action.decision == "remove":
        false_positive_penalty = -0.40

    raw = (
        weights["decision"] * decision_accuracy
        + weights["rule"] * rule_accuracy
        + weights["time"] * time_efficiency
        + weights["evidence"] * evidence_quality
        + weights["reason"] * reason_quality
        + false_positive_penalty
    )
    step_reward = clamp_01(raw)

    # Safe harbour signal — agent must learn to protect compliance status.
    _sh = state.safe_harbour_status if hasattr(state, "safe_harbour_status") else "protected"
    if _sh == "protected":
        _sh_delta = 0.05
    elif _sh == "at_risk":
        _sh_delta = -0.05
    else:  # "lost"
        _sh_delta = -0.10
    step_reward = clamp_01(step_reward + _sh_delta)

    calibration_delta = _calibration_score(action.confidence, decision_accuracy)
    step_reward = clamp_01(step_reward + calibration_delta)

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

    # Anti-exploit: penalize over-dominant single-action strategies.
    if len(actions) >= 3:
        decisions = [a.get("decision", "") for a in actions if isinstance(a, dict)]
        if decisions:
            most_common = max(set(decisions), key=decisions.count)
            dominance = decisions.count(most_common) / len(decisions)
            if dominance > 0.85:
                base -= 0.15

    if task_id == "cib-graph-takedown":
        sequence_bonus = 0.0
        for action in actions:
            if action.get("target_account") == "Account_A":
                sequence_bonus = 0.1 if action.get("decision") == "remove" else 0.0
                break
        return clamp_01(base + sequence_bonus)
    return clamp_01(base)
