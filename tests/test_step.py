from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction


def test_step_returns_expected_shape():
    env = DharmaShieldEnvironment()
    env.reset("upi-scam-triage")
    action = DharmaShieldAction(
        decision="remove",
        rule_cited="IT_2021_3_1_b_iii",
        evidence_signals=["upi_pin_request"],
        confidence=0.7,
        reason="policy",
        notify_user=False,
    )
    obs, reward, done, info = env.step(action)
    assert isinstance(obs.current_item.content_id, str)
    assert 0.0 <= reward.step_reward <= 1.0
    assert isinstance(done, bool)
    assert info.task_id
