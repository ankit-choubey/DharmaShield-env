from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction


def test_reset_produces_fresh_state():
    env = DharmaShieldEnvironment()
    first = env.reset("upi-scam-triage").model_dump()
    env.step(
        DharmaShieldAction(
            decision="remove",
            rule_cited="IT_2021_3_1_b_iii",
            evidence_signals=[],
            confidence=0.5,
            reason="test",
            notify_user=False,
        )
    )
    second = env.reset("upi-scam-triage").model_dump()
    assert first["current_item"]["content_id"] == second["current_item"]["content_id"]
    assert second["step_number"] == 0
