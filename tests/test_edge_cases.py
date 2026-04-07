from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction
from fastapi.testclient import TestClient

from dharma_shield.server import app


def test_invalid_rule_key_does_not_crash():
    env = DharmaShieldEnvironment()
    env.reset("sgi-compliance-review")
    action = DharmaShieldAction(
        decision="remove",
        rule_cited="IT_RULE_99",
        evidence_signals=[],
        confidence=0.1,
        reason="invalid rule",
        notify_user=False,
    )
    _, reward, _, info = env.step(action)
    assert 0.0 <= reward.step_reward <= 1.0
    assert info.rule_valid is False


def test_max_steps_terminates_cleanly():
    env = DharmaShieldEnvironment()
    env.reset("cib-graph-takedown")
    action = DharmaShieldAction(
        decision="request_human_review",
        rule_cited="UNKNOWN",
        evidence_signals=[],
        confidence=0.0,
        reason="stress",
        notify_user=False,
    )
    done = False
    for _ in range(12):
        _, _, done, _ = env.step(action)
        if done:
            break
    assert done is True


def test_step_endpoint_accepts_raw_and_alias_payloads():
    client = TestClient(app)

    r1 = client.post("/step", json={"decision": "remove"})
    assert r1.status_code == 200

    r2 = client.post("/step", json={"action": "approve", "conf": 0.8})
    assert r2.status_code == 200

    r3 = client.post("/step", json={"action": {"decision": "remove "}})
    assert r3.status_code == 200
