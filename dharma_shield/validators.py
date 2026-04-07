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
    if not expected_rule or expected_rule not in POLICY_BOOK:
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
