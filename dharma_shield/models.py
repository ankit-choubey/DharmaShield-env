from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AccountMeta(BaseModel):
    account_age_days: int
    prior_violations: int = 0
    payment_linked: bool
    verified_badge: bool = False
    country_code: str
    posting_frequency_per_day: float


class ContentItem(BaseModel):
    content_id: str
    text: str
    content_type: Literal["text", "image_with_caption", "video_desc", "audio_transcript"]
    sgi_flag: bool = False
    upi_pattern_detected: bool = False
    toxicity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    language: str = "en"
    linked_accounts: List[str] = Field(default_factory=list)
    timestamp_offset_sec: int = 0
    english_summary: Optional[str] = None
    evidence_signals: List[str] = Field(default_factory=list)
    target_account: Optional[str] = None


class DharmaShieldObservation(BaseModel):
    current_item: ContentItem
    account_meta: AccountMeta
    time_remaining_hours: float
    active_rule_hints: List[str] = Field(default_factory=list)
    similar_past_decisions: List[str] = Field(default_factory=list)
    step_number: int
    queue_size_remaining: int
    platform_compliance_health: float = Field(ge=0.0, le=1.0)
    safe_harbour_status: Literal["protected", "at_risk", "lost"]


class DharmaShieldAction(BaseModel):
    decision: Literal["approve", "remove", "label_sgi", "warn_user", "escalate", "request_human_review"]
    rule_cited: str = "UNKNOWN"
    evidence_signals: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reason: str = Field(default="", max_length=200)
    notify_user: bool = False
    target_account: Optional[str] = None


class DharmaShieldReward(BaseModel):
    step_reward: float = Field(ge=0.0, le=1.0)
    decision_accuracy: float = Field(ge=0.0, le=1.0)
    rule_accuracy: float = Field(ge=0.0, le=1.0)
    time_efficiency: float = Field(ge=0.0, le=1.0)
    evidence_quality: float = Field(ge=0.0, le=1.0)
    false_positive_penalty: float
    cumulative_episode_score: float = Field(ge=0.0, le=1.0)


class EpisodeState(BaseModel):
    current_step: int = 0
    task_id: str = ""
    queue_index: int = 0
    time_remaining_hours: float = 3.0
    compliance_health: float = 1.0
    missed_deadlines: int = 0
    false_positives: int = 0
    safe_harbour_status: Literal["protected", "at_risk", "lost"] = "protected"
    step_rewards: List[float] = Field(default_factory=list)
    reveal_phase: int = 0
    completed: bool = False


class StepInfo(BaseModel):
    task_id: str
    error: Optional[str] = None
    termination_reason: Optional[str] = None
    rule_valid: bool = True
    time_window_active: bool = True
    expected_decision: Optional[str] = None
    expected_rule: Optional[str] = None


class StepResponse(BaseModel):
    observation: DharmaShieldObservation
    reward: DharmaShieldReward
    done: bool
    info: StepInfo


class TaskScore(BaseModel):
    task: str
    score: float
    steps: int
    rewards: List[float]
    success: bool
    error: Optional[str] = None


class StateResponse(BaseModel):
    state: Dict[str, Any]
