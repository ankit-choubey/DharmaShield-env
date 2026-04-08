from dharma_shield.grader import (
    TASK_REWARD_WEIGHTS,
    _DEFAULT_WEIGHTS,
    _calibration_delta,
    _calibration_score,
    _reason_quality,
    clamp_01,
    compute_step_reward,
    compute_task_score,
)
from dharma_shield.models import DharmaShieldAction, EpisodeState


def test_clamp_bounds():
    assert clamp_01(-5.0) == 0.0
    assert clamp_01(5.0) == 1.0


def test_grader_returns_clamped_reward():
    state = EpisodeState(task_id="upi-scam-triage")
    action = DharmaShieldAction(
        decision="remove",
        rule_cited="IT_2021_3_1_b_iii",
        evidence_signals=["upi_pin_request"],
        confidence=1.0,
        reason="test",
        notify_user=False,
    )
    reward = compute_step_reward(
        task_id="upi-scam-triage",
        action=action,
        expected_decision="approve",
        expected_rule="",
        expected_signals=[],
        time_remaining_hours=0.0,
        state=state,
    )
    assert 0.0 <= reward.step_reward <= 1.0


def test_reason_quality_prefers_policy_aligned_reasoning():
    strong = _reason_quality(
        "Remove due to child safety risk and csam evidence.",
        "IT_2021_3_1_j",
        "remove",
    )
    weak = _reason_quality(
        "Looks fine to me.",
        "IT_2021_3_1_j",
        "remove",
    )
    assert strong > weak


def test_calibration_penalizes_overconfident_wrong_decision():
    overconfident_wrong = _calibration_score(1.0, 0.0)
    calibrated = _calibration_score(0.5, 0.0)
    assert overconfident_wrong < calibrated


def test_default_weights_sum_equal_one():
    total = sum(_DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9


def test_all_task_weight_sums_equal_one():
    for task_id, weights in TASK_REWARD_WEIGHTS.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f"{task_id} weights sum={total}"


def test_calibration_delta_is_bounded():
    for confidence in (0.0, 0.25, 0.5, 0.75, 1.0):
        for accuracy in (0.0, 0.5, 1.0):
            delta = _calibration_delta(confidence, accuracy)
            assert -0.05 <= delta <= 0.05


def test_cib_sequence_bonus_applied_once():
    base_rewards = [0.6, 0.6, 0.6]
    with_sequence = compute_task_score(
        "cib-graph-takedown",
        base_rewards,
        [
            {"decision": "remove", "target_account": "Account_A"},
            {"decision": "remove", "target_account": "Account_A"},
            {"decision": "remove", "target_account": "Account_A"},
        ],
    )
    without_sequence = compute_task_score(
        "cib-graph-takedown",
        base_rewards,
        [
            {"decision": "remove", "target_account": "Account_B"},
            {"decision": "remove", "target_account": "Account_C"},
            {"decision": "remove", "target_account": "Account_E"},
        ],
    )
    assert abs(with_sequence - without_sequence - 0.1) < 1e-9
