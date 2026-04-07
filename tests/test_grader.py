from dharma_shield.grader import clamp_01, compute_step_reward
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
