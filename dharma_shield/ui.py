from __future__ import annotations

import gradio as gr

from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.models import DharmaShieldAction
from dharma_shield.task_data import TASK_DATA, TASK_ORDER

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
    with gr.Blocks(css=CSS, title="DharmaShield - Trust and Safety Ops") as demo:
        gr.Markdown("## DharmaShield ENV - Trust and Safety Compliance Agent Interface")
        gr.Markdown("_Interactive evaluation console for OpenEnv-compliant RL environment_")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Task Control")
                task_selector = gr.Dropdown(choices=TASK_ORDER, value=TASK_ORDER[0], label="Task", interactive=True)
                reset_btn = gr.Button("Reset Episode", variant="primary")
                status_bar = gr.Textbox(label="Session Status", interactive=False, lines=1)

                gr.Markdown("### Action")
                decision_input = gr.Dropdown(
                    choices=["remove", "approve", "label_sgi", "warn_user", "escalate", "request_human_review"],
                    value="request_human_review",
                    label="Decision",
                    interactive=True,
                )
                rule_input = gr.Textbox(label="Rule Cited", placeholder="IT_2021_3_1_b_iii", value="UNKNOWN")
                evidence_input = gr.Textbox(label="Evidence Signals (comma-separated)", placeholder="upi_pin_request, prize_scam")
                confidence_input = gr.Slider(minimum=0.0, maximum=1.0, step=0.05, value=0.8, label="Confidence")
                reason_input = gr.Textbox(label="Reason", placeholder="Brief policy rationale...")
                notify_input = gr.Checkbox(label="Notify User", value=False)
                step_btn = gr.Button("Submit Step")

            with gr.Column(scale=2):
                gr.Markdown("### Current Observation")
                obs_display = gr.Textbox(
                    label="Content Item + Account Meta",
                    lines=28,
                    interactive=False,
                    value="Reset a task to begin.",
                )

            with gr.Column(scale=1):
                gr.Markdown("### Reward Signal")
                reward_display = gr.Textbox(label="Step Reward Breakdown", lines=16, interactive=False)

        gr.Markdown(
            """
---
**Policy Reference** - IT Act 2021/2026 Rules:
`IT_2021_3_1_b_iii` Financial fraud/UPI scam (3h window) |
`IT_2026_SGI_DEEPFAKE` Synthetic impersonation (3h window) |
`IT_2026_SGI_LABEL` Undisclosed AI content (24h window) |
`IT_2021_3_1_j` Child safety urgent (1h window) |
`IT_2021_3_1_d` Government notice (6h window) |
`IT_2021_3_1_b_i` National security (1h window)
"""
        )

        reset_btn.click(fn=ui_reset, inputs=[task_selector], outputs=[obs_display, reward_display, status_bar])
        step_btn.click(
            fn=ui_step,
            inputs=[decision_input, rule_input, evidence_input, confidence_input, reason_input, notify_input],
            outputs=[obs_display, reward_display, status_bar],
        )

    return demo
