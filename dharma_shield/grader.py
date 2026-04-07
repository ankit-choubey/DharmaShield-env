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

    # Safe harbour signal — agent must learn to protect compliance status.
    _sh = state.safe_harbour_status if hasattr(state, "safe_harbour_status") else "protected"
    if _sh == "protected":
        _sh_delta = 0.05
    elif _sh == "at_risk":
        _sh_delta = -0.05
    else:  # "lost"
        _sh_delta = -0.10
    step_reward = clamp_01(step_reward + _sh_delta)

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
