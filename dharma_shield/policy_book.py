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
