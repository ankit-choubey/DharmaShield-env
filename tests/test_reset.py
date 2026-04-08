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


def test_observation_has_contextual_fields_and_no_rule_id_leak():
    env = DharmaShieldEnvironment()
    obs = env.reset("upi-scam-triage")
    dumped = obs.model_dump()

    assert "risk_summary" in dumped
    assert "interpreted_signals" in dumped
    assert "decision_context" in dumped
    assert "confidence_hint" in dumped
    assert isinstance(obs.decision_context.get("allowed_actions"), list)

    for hint in obs.active_rule_hints:
        assert not hint.startswith("IT_")
        assert "Relevant category:" in hint
