# DharmaShield V4 — Complete Agent-Ready Execution Plan
## "Win-Grade" Submission Plan | Deadline: Tonight

---

## AGENT BRIEFING

You are implementing the final "win-grade" version of DharmaShield — an OpenEnv-compliant
RL training environment for AI trust & safety compliance under India IT Act 2021/2026.

Project root: /Users/theankit/Documents/AK/DharmaShield_ENV/
Python venv:  .venv312 (Python 3.12)
Current tests: 25 passed (maintain all, add more)
Current state: V3.1 — 4 tasks, 25 tests, openenv validated, live on HF

CRITICAL RULE: Every change is ADDITIVE. No deletions of existing working code.
Stop after each block and run: source .venv312/bin/activate && pytest tests/ -q
Do NOT proceed if any test fails.

---

## BLOCK 0 — CRITICAL BUG FIX (Do this FIRST, before anything else)

### File: dharma_shield/validators.py

Find line with `apply_safe_harbour_logic`. There is a NameError bug:

CURRENT (broken):
    if not_expected_rule or expected_rule not in POLICY_BOOK:

CORRECT (fix):
    if not expected_rule or expected_rule not in POLICY_BOOK:

Fix this ONE character change. Then run pytest — must still pass 25 tests.

---

## BLOCK 1 — DIFFICULTY CALIBRATION (Remove answer hints for medium/hard tasks)

### File: dharma_shield/environment.py

Find `_build_observation()` method. Current code:
    expected_rule = item.get("ground_truth_rule", "")
    hints = [expected_rule] if expected_rule else []

Replace with:
    expected_rule = item.get("ground_truth_rule", "")
    task_difficulty = TASK_DATA.get(self.current_task_id, {}).get("difficulty", "easy")
    if task_difficulty == "easy":
        hints = [expected_rule] if expected_rule else []
    else:
        hints = []  # medium/hard tasks: no answer hints — agent must reason independently

Also add "difficulty" field to TASK_DATA entries in task_data.py:
    "upi-scam-triage":         add  "difficulty": "easy"
    "sgi-compliance-review":   add  "difficulty": "medium"
    "cib-graph-takedown":      add  "difficulty": "hard"
    "child-safety-escalation": add  "difficulty": "hard"

RATIONALE: Active rule hints literally hand the answer to the agent. Removing them for
medium/hard tasks reduces avg score from ~0.82 to ~0.68-0.72 — the ideal training range
where RL actually learns something. A 72B model scoring 0.95 means the env is trivial.

Verification: pytest must still pass. SGI and CIB scores will drop (this is CORRECT behavior).

---

## BLOCK 2 — GRADER UPGRADE (Task-specific weights + reason_quality + calibration)

### File: dharma_shield/grader.py

ADD these constants BEFORE compute_step_reward():

```python
TASK_REWARD_WEIGHTS = {
    "upi-scam-triage": {
        "decision": 0.40,
        "rule":     0.25,
        "time":     0.15,
        "evidence": 0.10,
        "reason":   0.10,
    },
    "sgi-compliance-review": {
        "decision": 0.35,
        "rule":     0.30,
        "time":     0.10,
        "evidence": 0.15,
        "reason":   0.10,
    },
    "cib-graph-takedown": {
        "decision": 0.35,
        "rule":     0.25,
        "time":     0.15,
        "evidence": 0.15,
        "reason":   0.10,
    },
    "child-safety-escalation": {
        "decision": 0.45,
        "rule":     0.25,
        "time":     0.20,
        "evidence": 0.05,
        "reason":   0.05,
    },
}

_DEFAULT_WEIGHTS = {
    "decision": 0.40,
    "rule":     0.30,
    "time":     0.15,
    "evidence": 0.10,
    "reason":   0.05,
}
```

ADD these two helper functions:

```python
def _reason_quality(reason: str, expected_rule: str, expected_decision: str) -> float:
    """
    Rubric-style reason quality score.
    Rewards policy-faithful reasoning traces, not just final labels.
    Aligned with: Firooz et al. arXiv:2512.20061 — reason signal reduces reward hacking.
    """
    if not reason or reason in ("", "normalized_input", "absolute_fallback", "regex_fallback"):
        return 0.0
    reason_lower = reason.lower()
    score = 0.3  # base for any non-empty reason

    # Policy keyword match
    policy_keywords = {
        "IT_2021_3_1_b_iii": ["upi", "fraud", "scam", "financial", "payment"],
        "IT_2026_SGI_DEEPFAKE": ["deepfake", "synthetic", "impersonation", "face", "clone"],
        "IT_2026_SGI_LABEL": ["ai generated", "label", "disclose", "undisclosed"],
        "IT_2021_3_1_j": ["child", "minor", "safety", "csam", "urgent"],
        "IT_2021_3_1_b_i": ["national", "security", "threat", "sovereignty"],
        "IT_2021_3_1_d": ["government", "notice", "formal", "escalate"],
    }
    if expected_rule and expected_rule in policy_keywords:
        keywords = policy_keywords[expected_rule]
        matched = sum(1 for kw in keywords if kw in reason_lower)
        score += 0.5 * min(1.0, matched / max(len(keywords), 1))

    # Decision alignment
    decision_keywords = {
        "remove": ["remove", "take down", "violates", "harmful"],
        "approve": ["legitimate", "benign", "safe", "no violation"],
        "label_sgi": ["label", "disclose", "mark"],
        "warn_user": ["warn", "caution", "notify"],
        "escalate": ["escalate", "report", "formal"],
    }
    if expected_decision in decision_keywords:
        if any(kw in reason_lower for kw in decision_keywords[expected_decision]):
            score += 0.2

    return clamp_01(score)


def _calibration_delta(confidence: float, decision_accuracy: float) -> float:
    """
    Bounded calibration signal: penalizes overconfident wrong decisions.
    Max effect: ±0.05 — never dominates step reward.
    """
    calibration = 1.0 - (confidence - decision_accuracy) ** 2
    raw_delta = (calibration - 0.75) * 0.10
    return max(-0.05, min(0.05, raw_delta))
```

REPLACE compute_step_reward() body with:

```python
def compute_step_reward(
    *,
    task_id: str,
    action: DharmaShieldAction,
    expected_decision: str,
    expected_rule: str,
    expected_signals: List[str],
    time_remaining_hours: float,
    state: EpisodeState,
) -> DharmaShieldReward:
    decision_accuracy = 1.0 if action.decision == expected_decision else 0.0
    rule_acc = _rule_accuracy(action.rule_cited, expected_rule)
    evidence_qual = _evidence_quality(action.evidence_signals, expected_signals)
    reason_qual = _reason_quality(action.reason, expected_rule, expected_decision)

    time_window = 3.0
    if expected_rule and expected_rule in POLICY_BOOK:
        time_window = POLICY_BOOK[expected_rule]["time_window_hours"]
    time_eff = clamp_01(min(1.0, time_remaining_hours / max(time_window, 0.01)))

    false_positive_penalty = 0.0
    if expected_decision == "approve" and action.decision == "remove":
        false_positive_penalty = -0.40

    w = TASK_REWARD_WEIGHTS.get(task_id, _DEFAULT_WEIGHTS)
    raw = (
        w["decision"] * decision_accuracy
        + w["rule"]     * rule_acc
        + w["time"]     * time_eff
        + w["evidence"] * evidence_qual
        + w["reason"]   * reason_qual
        + false_positive_penalty
    )
    step_reward = clamp_01(raw)

    # Safe harbour signal (additive, after clamp — existing style preserved)
    _sh = getattr(state, "safe_harbour_status", "protected")
    if _sh == "protected":
        _sh_delta = 0.05
    elif _sh == "at_risk":
        _sh_delta = -0.05
    else:
        _sh_delta = -0.10
    step_reward = clamp_01(step_reward + _sh_delta)

    # Calibration signal: bounded ±0.05, never dominant
    step_reward = clamp_01(step_reward + _calibration_delta(action.confidence, decision_accuracy))

    state.step_rewards.append(step_reward)
    cumulative = clamp_01(sum(state.step_rewards) / len(state.step_rewards))

    return DharmaShieldReward(
        step_reward=step_reward,
        decision_accuracy=decision_accuracy,
        rule_accuracy=rule_acc,
        time_efficiency=time_eff,
        evidence_quality=evidence_qual,
        false_positive_penalty=false_positive_penalty,
        cumulative_episode_score=cumulative,
    )
```

VERIFY: sum(w.values()) == 1.0 for ALL task weight dicts. Add assertion in test (not here).

---

## BLOCK 3 — ADVERSARIAL TASK ITEMS (2-3 per task, additive only)

### File: dharma_shield/task_data.py

ADD these adversarial items to existing task item lists (append, do not remove existing):

#### To "upi-scam-triage" items list (append after upi_8):
```python
{
    "content_id": "upi_adv_1",
    "text": "Payment from SBI-Official-Care@okicici: ₹0.01 test credit. Please confirm receipt to complete KYC verification for ₹49,999 prize.",
    "english_summary": "Adversarial: perfect grammar, real IFSC format, staged micro-credit → large fraud.",
    "content_type": "text",
    "sgi_flag": False,
    "upi_pattern_detected": True,
    "toxicity_score": 0.05,
    "language": "en",
    "timestamp_offset_sec": 35,
    "evidence_signals": ["staged_micro_credit", "kyc_pretext", "prize_escalation"],
    "account_meta": {
        "account_age_days": 3,
        "prior_violations": 0,
        "payment_linked": True,
        "verified_badge": False,
        "country_code": "IN",
        "posting_frequency_per_day": 0.2,
    },
    "ground_truth_decision": "remove",
    "ground_truth_rule": "IT_2021_3_1_b_iii",
},
{
    "content_id": "upi_adv_2",
    "text": "Google Pay festive cashback: Scan the QR below for instant ₹250 credited to your linked bank — valid till midnight.",
    "english_summary": "Adversarial FP trap: looks exactly like UPI scam but is legitimate merchant promo from verified source.",
    "content_type": "image_with_caption",
    "sgi_flag": False,
    "upi_pattern_detected": False,
    "toxicity_score": 0.0,
    "language": "en",
    "timestamp_offset_sec": 38,
    "evidence_signals": ["merchant_verified", "official_cashback_program"],
    "account_meta": {
        "account_age_days": 2100,
        "prior_violations": 0,
        "payment_linked": True,
        "verified_badge": True,
        "country_code": "IN",
        "posting_frequency_per_day": 22.0,
    },
    "ground_truth_decision": "approve",
    "ground_truth_rule": "",
},
```

#### To "sgi-compliance-review" items list (append after sgi_6):
```python
{
    "content_id": "sgi_adv_1",
    "text": "Satire video: AI-generated version of politician dancing — clearly labeled '#AIParody #Satire' in caption.",
    "english_summary": "Adversarial: deepfake-quality generation BUT fully disclosed satire. Label, do not remove.",
    "content_type": "video_desc",
    "sgi_flag": True,
    "upi_pattern_detected": False,
    "toxicity_score": 0.1,
    "language": "en",
    "timestamp_offset_sec": 30,
    "evidence_signals": ["ai_disclosure_tag", "satire_label", "no_impersonation_intent"],
    "account_meta": {
        "account_age_days": 800,
        "prior_violations": 0,
        "payment_linked": False,
        "verified_badge": True,
        "country_code": "IN",
        "posting_frequency_per_day": 2.5,
    },
    "ground_truth_decision": "label_sgi",
    "ground_truth_rule": "IT_2026_SGI_LABEL",
},
{
    "content_id": "sgi_adv_2",
    "text": "Breaking: Voice recording of minister confirming policy reversal — no metadata available.",
    "english_summary": "Adversarial: no explicit SGI flags but voice clone evidence pattern. Must escalate, not remove.",
    "content_type": "audio_transcript",
    "sgi_flag": False,
    "upi_pattern_detected": False,
    "toxicity_score": 0.3,
    "language": "en",
    "timestamp_offset_sec": 33,
    "evidence_signals": ["no_metadata", "audio_artifact_pattern", "political_sensitivity"],
    "account_meta": {
        "account_age_days": 45,
        "prior_violations": 1,
        "payment_linked": False,
        "verified_badge": False,
        "country_code": "IN",
        "posting_frequency_per_day": 0.5,
    },
    "ground_truth_decision": "escalate",
    "ground_truth_rule": "IT_2021_3_1_d",
},
```

#### To "cib-graph-takedown" items list (append after cib_escalate):
```python
{
    "content_id": "cib_adv_1",
    "text": "Account_F shares political commentary 4 hours after original — no hash match, independent post.",
    "english_summary": "Adversarial FP: looks like CIB network member but is organic late sharer. Approve.",
    "content_type": "text",
    "sgi_flag": False,
    "upi_pattern_detected": False,
    "toxicity_score": 0.1,
    "language": "en",
    "linked_accounts": [],
    "timestamp_offset_sec": 14400,
    "target_account": "Account_F",
    "evidence_signals": ["no_hash_match", "delayed_organic_share", "independent_commentary"],
    "account_meta": {
        "account_age_days": 650,
        "prior_violations": 0,
        "payment_linked": True,
        "verified_badge": False,
        "country_code": "IN",
        "posting_frequency_per_day": 7.2,
    },
    "ground_truth_decision": "approve",
    "ground_truth_rule": "",
},
```

VERIFICATION: All items must have ground_truth_decision and ground_truth_rule set.
max_steps for upi and sgi need to be updated to accommodate new items:
    "upi-scam-triage":      change max_steps from 10 to 12
    "sgi-compliance-review": change max_steps from 8 to 10
    "cib-graph-takedown":    change max_steps from 6 to 8
Also update openenv.yaml task metadata to match new max_steps.

---

## BLOCK 4 — NEW API ENDPOINTS (/episodes + GET /)

### File: dharma_shield/server.py

ADD episode logging to environment state. First, add to EpisodeState in models.py:
    (Do NOT add here — EpisodeState is Pydantic. Track episodes in server.py directly)

In server.py, add at module level (after env = DharmaShieldEnvironment()):
```python
from collections import deque
_episode_log: deque = deque(maxlen=20)
_current_episode_steps: list = []
```

Modify the /step endpoint to log episodes:
```python
@app.post("/step", response_model=StepResponse)
def step(payload: Dict[str, Any] = Body(...)) -> StepResponse:
    payload = validate_step_payload(payload)
    normalized = normalize_action_payload(payload)
    try:
        action = DharmaShieldAction(**normalized)
    except Exception:
        action = DharmaShieldAction(
            decision="request_human_review",
            rule_cited="UNKNOWN",
            evidence_signals=[],
            confidence=0.0,
            reason="fallback_invalid_payload",
            notify_user=False,
        )
    obs, reward, done, info = env.step(action)
    _current_episode_steps.append({
        "step": env.state_data.current_step,
        "decision": action.decision,
        "rule_cited": action.rule_cited,
        "reward": reward.step_reward,
        "done": done,
    })
    if done:
        _episode_log.append({
            "task_id": info.task_id,
            "steps": list(_current_episode_steps),
            "avg_reward": sum(s["reward"] for s in _current_episode_steps) / max(len(_current_episode_steps), 1),
        })
        _current_episode_steps.clear()
    return StepResponse(observation=obs, reward=reward, done=done, info=info)
```

ADD new endpoints:
```python
@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "dharma-shield",
        "version": "3.1.0",
        "docs": "/docs",
        "health": "/health",
        "tasks": list(env.task_order),
        "openenv": True,
    }


@app.get("/episodes")
def get_episodes() -> Dict[str, Any]:
    """Return last 20 episode trajectories for training analysis."""
    return {
        "total_logged": len(_episode_log),
        "episodes": list(_episode_log),
    }
```

UPDATE /health endpoint version to "3.1.0":
```python
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "env": "dharma-shield", "version": "3.1.0"}
```

---

## BLOCK 5 — PROFESSIONAL GRADIO UI

### New file: dharma_shield/ui.py

This is the most important UI design constraint:
- MUST look like an internal Trust & Safety operations dashboard
- Dark theme: background #0f1117, surface #1a1d27, accent #3b82f6 (blue, NOT teal/green)
- Monospace font for JSON/code: JetBrains Mono or similar
- NO emojis in UI labels (use text labels: "REMOVE", "APPROVE", etc.)
- NO gradient backgrounds, NO neon colors, NO decorative elements
- Looks like: Linear.app or Vercel dashboard — functional, spare, professional
- 3 columns: [Task Control] | [Current Item] | [Action + Result]

```python
from __future__ import annotations
import json
import gradio as gr
from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction
from dharma_shield.task_data import TASK_ORDER, TASK_DATA

_ui_env = DharmaShieldEnvironment()
_ui_obs = None
_ui_done = False


def _format_observation(obs_dict: dict) -> str:
    item = obs_dict.get("current_item", {})
    meta = obs_dict.get("account_meta", {})
    out = []
    out.append(f"CONTENT ID:    {item.get('content_id', 'N/A')}")
    out.append(f"TYPE:          {item.get('content_type', 'N/A')}")
    out.append(f"TEXT:          {item.get('text', 'N/A')}")
    out.append(f"SUMMARY:       {item.get('english_summary', 'N/A')}")
    out.append("")
    out.append(f"SGI FLAG:      {item.get('sgi_flag', False)}")
    out.append(f"UPI DETECTED:  {item.get('upi_pattern_detected', False)}")
    out.append(f"TOXICITY:      {item.get('toxicity_score', 0.0):.2f}")
    out.append(f"LANGUAGE:      {item.get('language', 'en')}")
    out.append(f"SIGNALS:       {', '.join(item.get('evidence_signals', []))}")
    out.append("")
    out.append("ACCOUNT META:")
    out.append(f"  Age:         {meta.get('account_age_days', 0)} days")
    out.append(f"  Violations:  {meta.get('prior_violations', 0)}")
    out.append(f"  Verified:    {meta.get('verified_badge', False)}")
    out.append(f"  Country:     {meta.get('country_code', 'N/A')}")
    out.append("")
    out.append(f"STEP:          {obs_dict.get('step_number', 0)}")
    out.append(f"TIME LEFT:     {obs_dict.get('time_remaining_hours', 0.0):.2f}h")
    out.append(f"COMPLIANCE:    {obs_dict.get('platform_compliance_health', 1.0):.2f}")
    out.append(f"SAFE HARBOUR:  {obs_dict.get('safe_harbour_status', 'protected').upper()}")
    return "\n".join(out)


def _format_reward(reward_dict: dict, done: bool, info_dict: dict) -> str:
    out = []
    out.append(f"STEP REWARD:        {reward_dict.get('step_reward', 0.0):.4f}")
    out.append(f"DECISION ACCURACY:  {reward_dict.get('decision_accuracy', 0.0):.2f}")
    out.append(f"RULE ACCURACY:      {reward_dict.get('rule_accuracy', 0.0):.2f}")
    out.append(f"TIME EFFICIENCY:    {reward_dict.get('time_efficiency', 0.0):.2f}")
    out.append(f"EVIDENCE QUALITY:   {reward_dict.get('evidence_quality', 0.0):.2f}")
    out.append(f"FP PENALTY:         {reward_dict.get('false_positive_penalty', 0.0):.2f}")
    out.append(f"CUMULATIVE SCORE:   {reward_dict.get('cumulative_episode_score', 0.0):.4f}")
    out.append("")
    out.append(f"EPISODE DONE:       {done}")
    if info_dict.get("termination_reason"):
        out.append(f"TERMINATION:        {info_dict.get('termination_reason', '')}")
    if info_dict.get("expected_decision"):
        out.append(f"EXPECTED DECISION:  {info_dict.get('expected_decision', '')}")
    if info_dict.get("expected_rule"):
        out.append(f"EXPECTED RULE:      {info_dict.get('expected_rule', '')}")
    return "\n".join(out)


def ui_reset(task_id: str):
    global _ui_obs, _ui_done
    obs = _ui_env.reset(task_id)
    _ui_obs = obs.model_dump()
    _ui_done = False
    return (
        _format_observation(_ui_obs),
        "Reset complete. Ready for first step.",
        f"Task: {task_id} | Items: {len(_ui_env.current_queue)} | Max Steps: {TASK_DATA[task_id]['max_steps']}",
    )


def ui_step(decision: str, rule_cited: str, evidence_input: str, confidence: float, reason: str, notify_user: bool):
    global _ui_obs, _ui_done
    if _ui_done:
        return _format_observation(_ui_obs), "Episode complete. Reset to start a new task.", ""
    if not _ui_obs:
        return "No active episode. Reset first.", "No active episode.", ""

    signals = [s.strip() for s in evidence_input.split(",") if s.strip()]
    try:
        action = DharmaShieldAction(
            decision=decision,
            rule_cited=rule_cited if rule_cited else "UNKNOWN",
            evidence_signals=signals,
            confidence=float(confidence),
            reason=reason if reason else "manual_ui_action",
            notify_user=notify_user,
        )
        obs_model, reward_model, done, info = _ui_env.step(action)
        _ui_obs = obs_model.model_dump()
        _ui_done = done
        return (
            _format_observation(_ui_obs),
            _format_reward(reward_model.model_dump(), done, info.model_dump()),
            f"Step {_ui_env.state_data.current_step} | Cumulative: {reward_model.cumulative_episode_score:.4f}",
        )
    except Exception as e:
        return _format_observation(_ui_obs), f"Error: {str(e)}", ""


CSS = """
body { background: #0f1117 !important; }
.gradio-container { background: #0f1117 !important; font-family: 'JetBrains Mono', 'Fira Code', monospace !important; }
.gr-box, .gr-panel, .gr-form { background: #1a1d27 !important; border: 1px solid #2d3148 !important; border-radius: 4px !important; }
.gr-button { background: #1e3a5f !important; color: #93c5fd !important; border: 1px solid #2563eb !important; border-radius: 4px !important; font-family: monospace !important; font-size: 13px !important; }
.gr-button:hover { background: #2563eb !important; }
.gr-button.gr-button-primary { background: #2563eb !important; color: #fff !important; }
textarea, input, select { background: #0f1117 !important; color: #e2e8f0 !important; border: 1px solid #2d3148 !important; font-family: monospace !important; }
label { color: #94a3b8 !important; font-size: 11px !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; font-family: monospace !important; }
.gr-markdown h1, .gr-markdown h2, .gr-markdown h3 { color: #e2e8f0 !important; }
"""

def build_ui():
    with gr.Blocks(css=CSS, title="DharmaShield — Trust & Safety Ops") as demo:
        gr.Markdown("## DharmaShield ENV — Trust & Safety Compliance Agent Interface")
        gr.Markdown("_Interactive evaluation console for OpenEnv-compliant RL environment_")

        with gr.Row():
            # Left: Task Control
            with gr.Column(scale=1):
                gr.Markdown("### Task Control")
                task_selector = gr.Dropdown(
                    choices=TASK_ORDER,
                    value=TASK_ORDER[0],
                    label="Task",
                    interactive=True,
                )
                reset_btn = gr.Button("Reset Episode", variant="primary")
                status_bar = gr.Textbox(label="Session Status", interactive=False, lines=1)

                gr.Markdown("### Action")
                decision_input = gr.Dropdown(
                    choices=["remove", "approve", "label_sgi", "warn_user", "escalate", "request_human_review"],
                    value="request_human_review",
                    label="Decision",
                    interactive=True,
                )
                rule_input = gr.Textbox(
                    label="Rule Cited",
                    placeholder="IT_2021_3_1_b_iii",
                    value="UNKNOWN",
                )
                evidence_input = gr.Textbox(
                    label="Evidence Signals (comma-separated)",
                    placeholder="upi_pin_request, prize_scam",
                )
                confidence_input = gr.Slider(
                    minimum=0.0, maximum=1.0, step=0.05, value=0.8,
                    label="Confidence",
                )
                reason_input = gr.Textbox(
                    label="Reason",
                    placeholder="Brief policy rationale...",
                )
                notify_input = gr.Checkbox(label="Notify User", value=False)
                step_btn = gr.Button("Submit Step")

            # Middle: Current Observation
            with gr.Column(scale=2):
                gr.Markdown("### Current Observation")
                obs_display = gr.Textbox(
                    label="Content Item + Account Meta",
                    lines=28,
                    interactive=False,
                    value="Reset a task to begin.",
                )

            # Right: Reward Signal
            with gr.Column(scale=1):
                gr.Markdown("### Reward Signal")
                reward_display = gr.Textbox(
                    label="Step Reward Breakdown",
                    lines=16,
                    interactive=False,
                )

        gr.Markdown("""
---
**Policy Reference** — IT Act 2021/2026 Rules:
`IT_2021_3_1_b_iii` Financial fraud/UPI scam (3h window) |
`IT_2026_SGI_DEEPFAKE` Synthetic impersonation (3h window) |
`IT_2026_SGI_LABEL` Undisclosed AI content (24h window) |
`IT_2021_3_1_j` Child safety urgent (1h window) |
`IT_2021_3_1_d` Government notice (6h window) |
`IT_2021_3_1_b_i` National security (1h window)
""")

        reset_btn.click(
            fn=ui_reset,
            inputs=[task_selector],
            outputs=[obs_display, reward_display, status_bar],
        )
        step_btn.click(
            fn=ui_step,
            inputs=[decision_input, rule_input, evidence_input, confidence_input, reason_input, notify_input],
            outputs=[obs_display, reward_display, status_bar],
        )

    return demo
```

### File: dharma_shield/server.py — Mount Gradio UI

ADD these imports at top:
```python
import gradio as gr
from dharma_shield.ui import build_ui
```

ADD at end of server.py (after all route definitions):
```python
# Mount Gradio UI at /ui for interactive human evaluation
_gradio_demo = build_ui()
app = gr.mount_gradio_app(app, _gradio_demo, path="/ui")
```

ADD to requirements.txt:
```
gradio>=4.0.0
```

### Test the UI:
```bash
source .venv312/bin/activate
uvicorn dharma_shield.server:app --host 0.0.0.0 --port 7860
# Open http://localhost:7860/ui
```

---

## BLOCK 6 — TRL TRAINING EXAMPLE

### New file: examples/train_grpo.py

```python
"""
DharmaShield GRPO Training Example
===================================
Demonstrates how to train an LLM agent on DharmaShield using TRL GRPO.
This is a minimal reference implementation — production training would
require more episodes and hyperparameter tuning.

Usage:
    pip install trl>=0.8.0 transformers>=4.40.0
    # Start DharmaShield server first:
    uvicorn dharma_shield.server:app --host 0.0.0.0 --port 7860 &
    python examples/train_grpo.py

Research basis:
    Firooz et al. "Scaling Reinforcement Learning for Content Moderation
    with Large Language Models" (arXiv:2512.20061, Dec 2025)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import httpx

SERVER_URL = os.getenv("DHARMA_SERVER_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("TRAIN_MODEL", "Qwen/Qwen2.5-7B-Instruct")


def _parse_decision(text: str) -> Dict[str, Any]:
    """Parse LLM output to DharmaShieldAction-compatible dict."""
    try:
        data = json.loads(text)
        if "decision" in data:
            return data
    except Exception:
        pass
    decisions = ["remove", "approve", "label_sgi", "warn_user", "escalate"]
    decision = next((d for d in decisions if d in text.lower()), "request_human_review")
    rule_match = re.search(r"(IT_[A-Z0-9_]+)", text)
    return {
        "decision": decision,
        "rule_cited": rule_match.group(1) if rule_match else "UNKNOWN",
        "evidence_signals": [],
        "confidence": 0.5,
        "reason": "grpo_training_output",
        "notify_user": False,
    }


def dharma_reward_fn(completions: List[str], task_id: str = "upi-scam-triage") -> List[float]:
    """
    Reward function for TRL GRPO training.
    Connects LLM completions to DharmaShield environment reward signal.
    """
    rewards = []
    for completion in completions:
        try:
            # Reset environment for fresh episode
            r = httpx.post(f"{SERVER_URL}/reset", json={"task_id": task_id}, timeout=10)
            r.raise_for_status()
            action_payload = _parse_decision(completion)
            step_r = httpx.post(f"{SERVER_URL}/step", json=action_payload, timeout=10)
            step_r.raise_for_status()
            step_data = step_r.json()
            rewards.append(step_data["reward"]["step_reward"])
        except Exception:
            rewards.append(0.0)
    return rewards


def run_baseline_episode(task_id: str = "upi-scam-triage") -> float:
    """Run a single episode with a static policy to verify env connectivity."""
    r = httpx.post(f"{SERVER_URL}/reset", json={"task_id": task_id}, timeout=10)
    r.raise_for_status()

    total_reward = 0.0
    steps = 0
    done = False
    while not done:
        action = {
            "decision": "remove",
            "rule_cited": "IT_2021_3_1_b_iii",
            "evidence_signals": ["test_signal"],
            "confidence": 0.8,
            "reason": "baseline_policy",
            "notify_user": False,
        }
        step_r = httpx.post(f"{SERVER_URL}/step", json=action, timeout=10)
        step_r.raise_for_status()
        step_data = step_r.json()
        total_reward += step_data["reward"]["step_reward"]
        done = step_data["done"]
        steps += 1

    avg = total_reward / max(steps, 1)
    print(f"[BASELINE] task={task_id} steps={steps} avg_reward={avg:.4f}")
    return avg


if __name__ == "__main__":
    print("DharmaShield GRPO Training Example")
    print("=" * 40)
    print(f"Server: {SERVER_URL}")
    print(f"Model:  {MODEL_NAME}")
    print()

    # Step 1: Verify env connectivity
    print("Step 1: Verifying environment connectivity...")
    try:
        health = httpx.get(f"{SERVER_URL}/health", timeout=5)
        print(f"  Health: {health.json()}")
    except Exception as e:
        print(f"  ERROR: Cannot connect to server. Start it first: {e}")
        exit(1)

    # Step 2: Run baseline episode
    print("\nStep 2: Running baseline episodes...")
    for task_id in ["upi-scam-triage", "sgi-compliance-review"]:
        run_baseline_episode(task_id)

    # Step 3: GRPO training loop (reference implementation)
    print("\nStep 3: GRPO training loop (reference)")
    print("  Install dependencies: pip install trl>=0.8.0 transformers>=4.40.0")
    print("  Then uncomment the training block below.")
    print()
    print("  Reference training config:")
    print("    model:       Qwen/Qwen2.5-7B-Instruct")
    print("    reward_fn:   dharma_reward_fn(completions, task_id)")
    print("    episodes:    100 per task")
    print("    tasks:       upi-scam-triage → sgi-compliance-review → cib-graph-takedown")

    # Uncomment for actual GRPO training:
    # from trl import GRPOConfig, GRPOTrainer
    # from transformers import AutoModelForCausalLM, AutoTokenizer
    #
    # model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
    # tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    #
    # training_args = GRPOConfig(
    #     output_dir="./dharma-shield-grpo",
    #     num_train_epochs=1,
    #     per_device_train_batch_size=4,
    # )
    #
    # trainer = GRPOTrainer(
    #     model=model,
    #     args=training_args,
    #     reward_funcs=lambda completions, **kw: dharma_reward_fn(completions),
    #     tokenizer=tokenizer,
    # )
    # trainer.train()
```

---

## BLOCK 7 — NEW TESTS (Additive only)

### New file: tests/test_v4_grader.py

```python
"""V4 grader tests: weight sums, reason quality, calibration bounds."""
import pytest
from dharma_shield.grader import (
    TASK_REWARD_WEIGHTS,
    _DEFAULT_WEIGHTS,
    _reason_quality,
    _calibration_delta,
    clamp_01,
)


def test_all_task_weight_sums_equal_one():
    for task_id, weights in TASK_REWARD_WEIGHTS.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f"{task_id} weights sum={total}, expected 1.0"


def test_default_weights_sum_equal_one():
    total = sum(_DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"Default weights sum={total}"


def test_calibration_delta_always_bounded():
    for conf in [0.0, 0.1, 0.5, 0.9, 1.0]:
        for acc in [0.0, 1.0]:
            delta = _calibration_delta(conf, acc)
            assert -0.05 <= delta <= 0.05, f"Calibration out of bounds: conf={conf} acc={acc} delta={delta}"


def test_reason_quality_empty_returns_zero():
    assert _reason_quality("", "IT_2021_3_1_b_iii", "remove") == 0.0
    assert _reason_quality("absolute_fallback", "IT_2021_3_1_b_iii", "remove") == 0.0


def test_reason_quality_policy_keyword_boosts_score():
    score = _reason_quality("UPI fraud scam detected in payment", "IT_2021_3_1_b_iii", "remove")
    assert score > 0.5, f"Expected >0.5, got {score}"


def test_reason_quality_always_clamped():
    score = _reason_quality("upi fraud scam financial payment remove violates", "IT_2021_3_1_b_iii", "remove")
    assert 0.0 <= score <= 1.0


def test_cib_sequence_bonus_at_task_level_only():
    from dharma_shield.grader import compute_task_score
    actions_with_A_first = [
        {"decision": "remove", "target_account": "Account_A"},
        {"decision": "remove", "target_account": "Account_B"},
        {"decision": "remove", "target_account": "Account_C"},
    ]
    actions_without_A = [
        {"decision": "remove", "target_account": "Account_B"},
        {"decision": "remove", "target_account": "Account_C"},
        {"decision": "remove", "target_account": "Account_A"},
    ]
    rewards = [0.7, 0.7, 0.7]
    score_with = compute_task_score("cib-graph-takedown", rewards, actions_with_A_first)
    score_without = compute_task_score("cib-graph-takedown", rewards, actions_without_A)
    assert score_with > score_without, "CIB sequence bonus not applied correctly"
```

### New file: tests/test_v4_endpoints.py

```python
"""V4 endpoint tests: root, episodes, UI mount."""
from fastapi.testclient import TestClient
from dharma_shield.server import app


def test_root_endpoint_returns_200():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["openenv"] is True
    assert "tasks" in data
    assert len(data["tasks"]) >= 4


def test_episodes_endpoint_returns_200():
    client = TestClient(app)
    r = client.get("/episodes")
    assert r.status_code == 200
    data = r.json()
    assert "episodes" in data
    assert "total_logged" in data


def test_health_returns_correct_version():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["version"] == "3.1.0"
```

### Update: tests/test_openenv_schema.py

Find the assertion `len(data["tasks"]) >= 3` and change to `>= 4`.

---

## BLOCK 8 — VERSION BUMPS (Sync all metadata to 3.1.0)

### dharma_shield/__init__.py — add version:
```python
"""DharmaShield environment package."""
from .environment import DharmaShieldEnvironment

__version__ = "3.1.0"
__all__ = ["DharmaShieldEnvironment"]
```

### openenv.yaml — update version + tasks:
- version: 3.1.0
- description: updated with V4 capabilities
- tasks: update max_steps for upi (12) and sgi (10) and cib (8), add child-safety-escalation

Full updated openenv.yaml:
```yaml
name: dharma-shield-env
version: 3.1.0
description: >
  Policy-driven content moderation RL environment for India IT Act 2021/2026 compliance.
  Trains agents as trust-and-safety compliance officers with multi-signal reward shaping,
  safe-harbour legal tracking, exploit-resistant grading, and adversarial item difficulty.
  Grounded in: Firooz et al. arXiv:2512.20061 (Meta Platforms, 2025).
entrypoint: dharma_shield.environment:DharmaShieldEnvironment
framework: openenv
tags:
  - openenv
  - trust-safety
  - india-compliance
  - content-moderation
  - legal-compliance
  - rl-environment
reward_range:
  min: 0.0
  max: 1.0
observation_model: dharma_shield.models:DharmaShieldObservation
action_model: dharma_shield.models:DharmaShieldAction
reward_model: dharma_shield.models:DharmaShieldReward
api:
  base_path: /
  endpoints:
    reset: POST /reset
    step: POST /step
    state: GET /state
    health: GET /health
    episodes: GET /episodes
tasks:
  - id: upi-scam-triage
    difficulty: easy
    max_steps: 12
    description: "Triage UPI payment scam queue under IT Rule 3(1)(b)(iii). 3h window."
  - id: sgi-compliance-review
    difficulty: medium
    max_steps: 10
    description: "Review synthetic/AI-generated content under IT Rules SGI 2026. 3-24h window."
  - id: cib-graph-takedown
    difficulty: hard
    max_steps: 8
    description: "Coordinate inauthentic behaviour graph takedown. Sequence-dependent scoring."
  - id: child-safety-escalation
    difficulty: hard
    max_steps: 4
    description: "Child safety urgent escalation under IT Rule 3(1)(j). 1.5h window."
```

### pyproject.toml — version = "3.1.0"

---

## BLOCK 9 — README FINAL UPDATE

Update README.md with:

1. Baseline scores table — update to reflect V4 difficulty-calibrated scores after running inference
2. Architecture section — add /episodes endpoint
3. UI section — add "Interactive Console: /ui"
4. examples/train_grpo.py mention in Quick Start
5. Update test count to final number (expected: 30+)

IMPORTANT: Do NOT duplicate existing sections. Edit in-place.
Keep "Known evaluation constraints" note for multi-LLM n/a rows.

---

## VERIFICATION GATES

Run in this exact order:
```bash
source .venv312/bin/activate

# Gate 1: All tests pass
pytest tests/ -v --tb=short
# Expected: 30+ passed, 0 failed

# Gate 2: openenv validate
openenv validate
# Expected: [OK] Ready for multi-mode deployment

# Gate 3: API smoke
python -c "
from fastapi.testclient import TestClient
from dharma_shield.server import app
c = TestClient(app)
for path in ['/', '/health', '/episodes']:
    r = c.get(path)
    print(f'GET {path}: {r.status_code}')
r = c.post('/reset', json={})
print(f'POST /reset: {r.status_code}')
r = c.post('/step', json={'decision': 'remove'})
print(f'POST /step: {r.status_code}')
"

# Gate 4: Strict router run
REQUIRE_HF_ROUTER=true python inference.py > artifacts/router_qwen_v4.txt
grep "ROUTER_SUMMARY" artifacts/router_qwen_v4.txt
# Expected: fallbacks=0

# Gate 5: Final push
git add -A
git commit -m "feat: v4 — difficulty calibration, adversarial items, UI, training example, /episodes"
git push origin main && git push hf main
```

---

## EXPECTED OUTCOMES AFTER V4

| Metric | V3.1 | V4 (expected) | Why better |
|--------|------|----------------|------------|
| Tests | 25 | 30+ | v4 test files added |
| Tasks | 4 | 4 + adversarial items | harder items per task |
| Avg score (Qwen-72B) | 0.817 | ~0.65-0.72 | hints removed for medium/hard = ideal training range |
| Interactive UI | ❌ | ✅ /ui | Phase 3 human review |
| Training example | ❌ | ✅ examples/ | proves trainability |
| Episode logging | ❌ | ✅ /episodes | trajectory analysis |
| Reason quality | partial | ✅ full rubric | arXiv:2512.20061 |
| Calibration signal | bounded | ✅ strict ±0.05 | no dominant noise |

---

## PRIORITY ORDER IF TIME IS SHORT

If deadline is approaching, implement in this strict order:
1. BLOCK 0 — Bug fix (5 min, MUST DO)
2. BLOCK 1 — Hints removal (10 min, HIGH IMPACT)
3. BLOCK 2 — Grader upgrade (20 min, HIGH IMPACT)
4. BLOCK 4 — /episodes + GET / (15 min, MEDIUM IMPACT)
5. BLOCK 5 — Gradio UI (45 min, HIGH PHASE 3 IMPACT)
6. BLOCK 6 — TRL example (20 min, HIGH JUDGING IMPACT)
7. BLOCK 3 — Adversarial items (20 min, MEDIUM IMPACT)
8. BLOCK 7 — Tests (15 min)
9. BLOCK 8 — Version bumps (5 min)
10. BLOCK 9 — README (10 min)

Total estimated time: 2.5-3 hours
