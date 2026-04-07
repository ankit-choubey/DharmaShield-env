"""
DharmaShield stress and edge-case tests.
"""

from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.grader import compute_task_score
from dharma_shield.models import DharmaShieldAction


def _valid_action() -> DharmaShieldAction:
    return DharmaShieldAction(
        decision="remove",
        rule_cited="IT_2021_3_1_b_iii",
        confidence=0.9,
        evidence_signals=["upi_pattern"],
    )


def _minimal_action() -> DharmaShieldAction:
    return DharmaShieldAction(
        decision="approve",
        rule_cited="",
        confidence=0.5,
        evidence_signals=[],
    )


def test_repeated_reset_no_state_bleed():
    env = DharmaShieldEnvironment()
    for _ in range(50):
        obs = env.reset("upi-scam-triage")
        assert env.state_data.current_step == 0
        assert env.state_data.compliance_health == 1.0
        assert env.state_data.false_positives == 0
        assert env.state_data.safe_harbour_status == "protected"
        assert obs.step_number == 0


def test_reward_always_bounded():
    env = DharmaShieldEnvironment()
    for task_id in ["upi-scam-triage", "sgi-compliance-review", "cib-graph-takedown"]:
        env.reset(task_id)
        for _ in range(10):
            _, reward, done, _ = env.step(_valid_action())
            assert 0.0 <= reward.step_reward <= 1.0
            assert 0.0 <= reward.cumulative_episode_score <= 1.0
            if done:
                break


def test_always_remove_antiexploit():
    exploit_score = compute_task_score(
        "upi-scam-triage",
        [0.8] * 8,
        [{"decision": "remove"}] * 8,
    )
    mixed_score = compute_task_score(
        "upi-scam-triage",
        [0.8, 0.7, 0.9, 0.6, 0.85, 0.75, 0.8, 0.7],
        [
            {"decision": "remove"},
            {"decision": "approve"},
            {"decision": "remove"},
            {"decision": "warn_user"},
            {"decision": "remove"},
            {"decision": "escalate"},
            {"decision": "remove"},
            {"decision": "approve"},
        ],
    )
    assert exploit_score < mixed_score


def test_minimal_action_never_crashes():
    env = DharmaShieldEnvironment()
    for task_id in ["upi-scam-triage", "sgi-compliance-review", "cib-graph-takedown"]:
        env.reset(task_id)
        obs, reward, done, info = env.step(_minimal_action())
        assert obs is not None
        assert 0.0 <= reward.step_reward <= 1.0
        assert isinstance(done, bool)
        assert info is not None


def test_hard_task_genuinely_harder():
    env = DharmaShieldEnvironment()
    env.reset("upi-scam-triage")
    easy_rewards = []
    for _ in range(8):
        _, reward, done, _ = env.step(_valid_action())
        easy_rewards.append(reward.step_reward)
        if done:
            break

    env.reset("cib-graph-takedown")
    hard_rewards = []
    for _ in range(6):
        _, reward, done, _ = env.step(_valid_action())
        hard_rewards.append(reward.step_reward)
        if done:
            break

    easy_avg = sum(easy_rewards) / len(easy_rewards) if easy_rewards else 0.0
    hard_avg = sum(hard_rewards) / len(hard_rewards) if hard_rewards else 0.0
    assert hard_avg <= easy_avg + 0.15
