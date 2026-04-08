from __future__ import annotations

from typing import Dict, List

from .models import DharmaShieldAction, DharmaShieldReward, EpisodeState
from .policy_book import POLICY_BOOK


def clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


TASK_REWARD_WEIGHTS: Dict[str, Dict[str, float]] = {
    "upi-scam-triage": {
        "decision": 0.40,
        "rule": 0.25,
        "time": 0.15,
        "evidence": 0.10,
        "reason": 0.10,
    },
    "sgi-compliance-review": {
        "decision": 0.35,
        "rule": 0.30,
        "time": 0.10,
        "evidence": 0.15,
        "reason": 0.10,
    },
    "cib-graph-takedown": {
        "decision": 0.35,
        "rule": 0.25,
        "time": 0.15,
        "evidence": 0.15,
        "reason": 0.10,
    },
    "child-safety-escalation": {
        "decision": 0.45,
        "rule": 0.25,
        "time": 0.20,
        "evidence": 0.05,
        "reason": 0.05,
    },
}

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "decision": 0.40,
    "rule": 0.30,
    "time": 0.15,
    "evidence": 0.10,
    "reason": 0.05,
}

# Backward-compatible alias for existing imports/tests.
DEFAULT_REWARD_WEIGHTS = _DEFAULT_WEIGHTS


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


def _reason_quality(reason: str, expected_rule: str, expected_decision: str) -> float:
    """
    Rubric-style reason quality score.
    Rewards policy-faithful reasoning traces, not just final labels.
    """
    if not reason or reason in ("", "normalized_input", "absolute_fallback", "regex_fallback"):
        return 0.0

    reason_lower = reason.lower()
    score = 0.3

    policy_keywords = {
        "IT_2021_3_1_b_iii": ["upi", "fraud", "scam", "financial", "payment"],
        "IT_2026_SGI_DEEPFAKE": ["deepfake", "synthetic", "impersonation", "face", "clone"],
        "IT_2026_SGI_LABEL": ["ai generated", "label", "disclose", "undisclosed"],
        "IT_2021_3_1_j": ["child", "minor", "safety", "csam", "urgent"],
        "IT_2021_3_1_b_i": ["national", "security", "threat", "sovereignty"],
        "IT_2021_3_1_d": ["government", "notice", "formal", "escalate"],
    }
    if expected_rule and expected_rule in policy_keywords:
        keywords = policy_keywords[expected_rule]
        matched = sum(1 for kw in keywords if kw in reason_lower)
        score += 0.5 * min(1.0, matched / max(len(keywords), 1))

    decision_keywords = {
        "remove": ["remove", "take down", "violates", "harmful"],
        "approve": ["legitimate", "benign", "safe", "no violation"],
        "label_sgi": ["label", "disclose", "mark"],
        "warn_user": ["warn", "caution", "notify"],
        "escalate": ["escalate", "report", "formal"],
    }
    if expected_decision in decision_keywords:
        if any(kw in reason_lower for kw in decision_keywords[expected_decision]):
            score += 0.2

    return clamp_01(score)


def _calibration_delta(confidence: float, decision_accuracy: float) -> float:
    """
    Bounded calibration signal: penalizes overconfident wrong decisions.
    Max effect: ±0.05 — never dominates step reward.
    """
    calibration = 1.0 - (confidence - decision_accuracy) ** 2
    raw_delta = (calibration - 0.75) * 0.10
    return max(-0.05, min(0.05, raw_delta))


# Backward-compatible alias for existing tests/importers.
def _calibration_score(confidence: float, decision_accuracy: float) -> float:
    return _calibration_delta(confidence, decision_accuracy)


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
    weights = TASK_REWARD_WEIGHTS.get(task_id, _DEFAULT_WEIGHTS)
    decision_accuracy = 1.0 if action.decision == expected_decision else 0.0
    rule_acc = _rule_accuracy(action.rule_cited, expected_rule)
    evidence_qual = _evidence_quality(action.evidence_signals, expected_signals)
    reason_qual = _reason_quality(action.reason, expected_rule, expected_decision)

    time_window = 3.0
    if expected_rule and expected_rule in POLICY_BOOK:
        time_window = POLICY_BOOK[expected_rule]["time_window_hours"]
    time_efficiency = clamp_01(min(1.0, time_remaining_hours / max(time_window, 0.01)))

    false_positive_penalty = 0.0
    if expected_decision == "approve" and action.decision == "remove":
        false_positive_penalty = -0.40

    raw = (
        weights["decision"] * decision_accuracy
        + weights["rule"] * rule_acc
        + weights["time"] * time_efficiency
        + weights["evidence"] * evidence_qual
        + weights["reason"] * reason_qual
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

    calibration_delta = _calibration_delta(action.confidence, decision_accuracy)
    step_reward = clamp_01(step_reward + calibration_delta)

    state.step_rewards.append(step_reward)
    cumulative = clamp_01(sum(state.step_rewards) / len(state.step_rewards))

    return DharmaShieldReward(
        step_reward=step_reward,
        decision_accuracy=decision_accuracy,
        rule_accuracy=rule_acc,
        time_efficiency=time_efficiency,
        evidence_quality=evidence_qual,
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
        if actions:
            first_action = actions[0]
            if first_action.get("target_account") == "Account_A" and first_action.get("decision") == "remove":
                sequence_bonus = 0.1
        return clamp_01(base + sequence_bonus)
    return clamp_01(base)
