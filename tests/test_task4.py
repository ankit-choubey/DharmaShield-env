from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction
from dharma_shield.task_data import TASK_DATA


def test_task4_registered_and_manifest_ready():
    assert "child-safety-escalation" in TASK_DATA
    cfg = TASK_DATA["child-safety-escalation"]
    assert cfg["max_steps"] == 4
    assert cfg["time_budget_hours"] == 1.5
    assert len(cfg["items"]) == 4


def test_task4_rule_mapping_explicit():
    cfg = TASK_DATA["child-safety-escalation"]["items"]
    harmful = [item for item in cfg if item["ground_truth_decision"] == "remove"]
    benign = [item for item in cfg if item["ground_truth_decision"] == "approve"]

    assert len(harmful) == 2
    assert len(benign) == 2
    assert all(item["ground_truth_rule"] == "IT_2021_3_1_j" for item in harmful)
    assert all(item["ground_truth_rule"] == "" for item in benign)


def test_task4_env_flow_completes_without_crash():
    env = DharmaShieldEnvironment()
    env.reset("child-safety-escalation")

    done = False
    steps = 0
    while not done:
        action = DharmaShieldAction(
            decision="request_human_review",
            rule_cited="UNKNOWN",
            evidence_signals=[],
            confidence=0.0,
            reason="safety_test",
            notify_user=False,
        )
        obs, reward, done, info = env.step(action)
        assert 0.0 <= reward.step_reward <= 1.0
        assert info is not None
        assert obs is not None
        steps += 1
        if steps > 6:
            break

    assert steps <= 4
