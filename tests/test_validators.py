from dharma_shield.models import EpisodeState
from dharma_shield.validators import apply_safe_harbour_logic


def test_safe_harbour_noop_for_empty_rule():
    state = EpisodeState(task_id="upi-scam-triage")
    apply_safe_harbour_logic(state, expected_rule="", correct_decision=False)
    assert state.safe_harbour_status == "protected"
    assert state.compliance_health == 1.0


def test_safe_harbour_transitions_to_at_risk():
    state = EpisodeState(task_id="upi-scam-triage", missed_deadlines=0)
    apply_safe_harbour_logic(state, expected_rule="IT_2021_3_1_b_iii", correct_decision=False)
    assert state.safe_harbour_status == "at_risk"
    assert state.compliance_health == 1.0


def test_safe_harbour_transitions_to_lost():
    state = EpisodeState(task_id="upi-scam-triage", missed_deadlines=1)
    apply_safe_harbour_logic(state, expected_rule="IT_2021_3_1_b_iii", correct_decision=False)
    assert state.safe_harbour_status == "lost"
    assert state.compliance_health == 0.85
