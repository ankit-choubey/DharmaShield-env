"""V4 grader tests: weight sums, reason quality, calibration bounds."""

from dharma_shield.grader import (
    TASK_REWARD_WEIGHTS,
    _DEFAULT_WEIGHTS,
    _calibration_delta,
    _reason_quality,
    compute_task_score,
)


def test_all_task_weight_sums_equal_one_v4():
    for task_id, weights in TASK_REWARD_WEIGHTS.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f"{task_id} weights sum={total}, expected 1.0"


def test_default_weights_sum_equal_one_v4():
    total = sum(_DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"default weights sum={total}"


def test_calibration_delta_always_bounded_v4():
    for conf in [0.0, 0.1, 0.5, 0.9, 1.0]:
        for acc in [0.0, 1.0]:
            delta = _calibration_delta(conf, acc)
            assert -0.05 <= delta <= 0.05, f"delta={delta} out of bounds"


def test_reason_quality_empty_returns_zero_v4():
    assert _reason_quality("", "IT_2021_3_1_b_iii", "remove") == 0.0
    assert _reason_quality("absolute_fallback", "IT_2021_3_1_b_iii", "remove") == 0.0


def test_reason_quality_policy_keyword_boosts_score_v4():
    score = _reason_quality("UPI fraud scam detected in payment flow", "IT_2021_3_1_b_iii", "remove")
    assert score > 0.5


def test_reason_quality_always_clamped_v4():
    score = _reason_quality(
        "upi fraud scam financial payment remove violates rules",
        "IT_2021_3_1_b_iii",
        "remove",
    )
    assert 0.0 <= score <= 1.0


def test_cib_sequence_bonus_at_task_level_only_v4():
    actions_with_a_first = [
        {"decision": "remove", "target_account": "Account_A"},
        {"decision": "remove", "target_account": "Account_B"},
        {"decision": "remove", "target_account": "Account_C"},
    ]
    actions_without_a = [
        {"decision": "remove", "target_account": "Account_B"},
        {"decision": "remove", "target_account": "Account_C"},
        {"decision": "remove", "target_account": "Account_A"},
    ]
    rewards = [0.7, 0.7, 0.7]
    score_with = compute_task_score("cib-graph-takedown", rewards, actions_with_a_first)
    score_without = compute_task_score("cib-graph-takedown", rewards, actions_without_a)
    assert score_with > score_without
