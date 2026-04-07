from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from .grader import compute_step_reward
from .models import (
    AccountMeta,
    ContentItem,
    DharmaShieldAction,
    DharmaShieldObservation,
    DharmaShieldReward,
    EpisodeState,
    StepInfo,
)
from .task_data import TASK_DATA, TASK_ORDER
from .validators import apply_safe_harbour_logic, is_time_window_active, is_valid_rule_key, should_terminate


class DharmaShieldEnvironment:
    def __init__(self) -> None:
        self.task_order = TASK_ORDER
        self.current_task_idx = 0
        self.current_task_id = self.task_order[self.current_task_idx]
        self.current_queue: List[Dict[str, Any]] = []
        self.state_data = EpisodeState()
        self.action_history: List[Dict[str, str]] = []
        self.reset(self.current_task_id)

    def _build_observation(self) -> DharmaShieldObservation:
        idx = min(self.state_data.queue_index, len(self.current_queue) - 1)
        item = self.current_queue[idx]
        item_model = ContentItem(
            content_id=item["content_id"],
            text=item["text"],
            content_type=item["content_type"],
            sgi_flag=item.get("sgi_flag", False),
            upi_pattern_detected=item.get("upi_pattern_detected", False),
            toxicity_score=item.get("toxicity_score", 0.0),
            language=item.get("language", "en"),
            linked_accounts=item.get("linked_accounts", []),
            timestamp_offset_sec=item.get("timestamp_offset_sec", 0),
            english_summary=item.get("english_summary"),
            evidence_signals=item.get("evidence_signals", []),
            target_account=item.get("target_account"),
        )
        account_model = AccountMeta(**item["account_meta"])
        expected_rule = item.get("ground_truth_rule", "")
        hints = [expected_rule] if expected_rule else []

        return DharmaShieldObservation(
            current_item=item_model,
            account_meta=account_model,
            time_remaining_hours=self.state_data.time_remaining_hours,
            active_rule_hints=hints,
            similar_past_decisions=[a["decision"] for a in self.action_history[-5:]],
            step_number=self.state_data.current_step,
            queue_size_remaining=max(0, len(self.current_queue) - self.state_data.queue_index),
            platform_compliance_health=max(0.0, min(1.0, self.state_data.compliance_health)),
            safe_harbour_status=self.state_data.safe_harbour_status,
        )

    def reset(self, task_id: Optional[str] = None) -> DharmaShieldObservation:
        if task_id:
            if task_id not in TASK_DATA:
                raise ValueError(f"Unknown task_id: {task_id}")
            self.current_task_id = task_id
            self.current_task_idx = self.task_order.index(task_id)
        task_cfg = TASK_DATA[self.current_task_id]
        self.current_queue = deepcopy(task_cfg["items"])
        self.action_history = []
        self.state_data = EpisodeState(
            current_step=0,
            task_id=self.current_task_id,
            queue_index=0,
            time_remaining_hours=task_cfg["time_budget_hours"],
            compliance_health=1.0,
            missed_deadlines=0,
            false_positives=0,
            safe_harbour_status="protected",
            step_rewards=[],
            reveal_phase=0,
            completed=False,
        )
        return self._build_observation()

    def state(self) -> Dict[str, Any]:
        return self.state_data.model_dump()

    def _advance_task(self) -> None:
        self.current_task_idx = (self.current_task_idx + 1) % len(self.task_order)
        self.current_task_id = self.task_order[self.current_task_idx]

    def step(self, action: DharmaShieldAction) -> Tuple[DharmaShieldObservation, DharmaShieldReward, bool, StepInfo]:
        try:
            task_cfg = TASK_DATA[self.current_task_id]
            max_steps = task_cfg["max_steps"]
            queue_len = len(self.current_queue)
            done, reason = should_terminate(self.state_data, queue_len, max_steps)
            if done:
                info = StepInfo(task_id=self.current_task_id, termination_reason=reason)
                obs = self._build_observation()
                reward = DharmaShieldReward(
                    step_reward=0.0,
                    decision_accuracy=0.0,
                    rule_accuracy=0.0,
                    time_efficiency=0.0,
                    evidence_quality=0.0,
                    false_positive_penalty=0.0,
                    cumulative_episode_score=(sum(self.state_data.step_rewards) / len(self.state_data.step_rewards))
                    if self.state_data.step_rewards
                    else 0.0,
                )
                return obs, reward, True, info

            current = self.current_queue[self.state_data.queue_index]
            expected_decision = current.get("ground_truth_decision", "request_human_review")
            expected_rule = current.get("ground_truth_rule", "")
            expected_signals = current.get("evidence_signals", [])

            rule_valid = is_valid_rule_key(action.rule_cited)
            time_window_active = is_time_window_active(
                expected_rule if expected_rule else action.rule_cited,
                self.state_data.time_remaining_hours,
            )

            if not time_window_active:
                self.state_data.missed_deadlines += 1
                self.state_data.compliance_health = max(0.0, self.state_data.compliance_health - 0.1)
                if self.state_data.safe_harbour_status == "protected":
                    self.state_data.safe_harbour_status = "at_risk"

            reward = compute_step_reward(
                task_id=self.current_task_id,
                action=action,
                expected_decision=expected_decision,
                expected_rule=expected_rule,
                expected_signals=expected_signals,
                time_remaining_hours=self.state_data.time_remaining_hours,
                state=self.state_data,
            )

            if expected_decision == "approve" and action.decision == "remove":
                self.state_data.false_positives += 1
                self.state_data.compliance_health = max(0.0, self.state_data.compliance_health - 0.12)

            apply_safe_harbour_logic(
                self.state_data,
                expected_rule=expected_rule,
                correct_decision=(action.decision == expected_decision),
            )

            self.action_history.append(
                {
                    "decision": action.decision,
                    "rule_cited": action.rule_cited,
                    "target_account": action.target_account or current.get("target_account"),
                }
            )

            self.state_data.current_step += 1
            self.state_data.queue_index += 1
            self.state_data.time_remaining_hours = max(0.0, self.state_data.time_remaining_hours - 0.35)

            done, reason = should_terminate(self.state_data, queue_len, max_steps)
            if done:
                self.state_data.completed = True
                self.state_data.queue_index = min(self.state_data.queue_index, queue_len - 1)
                if self.state_data.queue_index < 0:
                    self.state_data.queue_index = 0
                self._advance_task()

            obs = self._build_observation()
            info = StepInfo(
                task_id=self.current_task_id,
                termination_reason=reason if done else None,
                rule_valid=rule_valid,
                time_window_active=time_window_active,
                expected_decision=expected_decision,
                expected_rule=expected_rule,
            )
            return obs, reward, done, info
        except Exception as exc:  # pragma: no cover - defensive path
            self.state_data.completed = True
            obs = self._build_observation()
            reward = DharmaShieldReward(
                step_reward=0.0,
                decision_accuracy=0.0,
                rule_accuracy=0.0,
                time_efficiency=0.0,
                evidence_quality=0.0,
                false_positive_penalty=0.0,
                cumulative_episode_score=0.0,
            )
            info = StepInfo(
                task_id=self.current_task_id,
                error=str(exc),
                termination_reason="exception",
                rule_valid=False,
                time_window_active=False,
            )
            return obs, reward, True, info


# Backward-compatible alias for older imports.
DharmaShieldEnv = DharmaShieldEnvironment