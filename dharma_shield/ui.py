from __future__ import annotations

import random
import time
from collections import Counter
from typing import Any, Dict, List

import gradio as gr

from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.exporter import export_episode_to_csv
from dharma_shield.models import DharmaShieldAction
from dharma_shield.runtime_config import SAFE_MODE, allow_experimental_features
from dharma_shield.task_data import TASK_DATA, TASK_ORDER

_ui_env = DharmaShieldEnvironment()
_ui_obs: Dict[str, Any] | None = None
_ui_done = False
_ui_step_logs: List[Dict[str, Any]] = []
_ui_episode_history: List[Dict[str, Any]] = []
_MAX_HISTORY = 20

_VALID_DECISIONS = ["remove", "approve", "label_sgi", "warn_user", "escalate", "request_human_review"]


def _format_observation(obs_dict: Dict[str, Any]) -> str:
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


def _format_reward(reward_dict: Dict[str, Any], done: bool, info_dict: Dict[str, Any]) -> str:
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


def _format_timeline(logs: List[Dict[str, Any]]) -> str:
    if not logs:
        return "No steps yet."
    lines = []
    for row in logs:
        lines.append(
            f"Step {row['step']:02d} | {row['decision']:<20} | reward={row['reward']:.2f} | latency={row['latency_ms']:.0f}ms"
        )
    return "\n".join(lines)


def _behavior_summary(logs: List[Dict[str, Any]]) -> str:
    if not logs:
        return "No behavior data yet."
    counts = Counter(row["decision"] for row in logs)
    total = max(len(logs), 1)
    lines = ["Action Distribution", "-------------------"]
    for decision in _VALID_DECISIONS:
        rate = counts.get(decision, 0) / total
        if counts.get(decision, 0) > 0:
            lines.append(f"{decision:<20} {rate:.2f}")
    return "\n".join(lines)


def _final_metrics(logs: List[Dict[str, Any]]) -> str:
    if not logs:
        return "Final Score: 0.000\nAverage Step Reward: 0.000\nTotal Steps: 0"
    rewards = [row["reward"] for row in logs]
    final_score = sum(rewards) / len(rewards)
    avg_step = final_score
    return (
        f"Final Score: {final_score:.3f}\n"
        f"Average Step Reward: {avg_step:.3f}\n"
        f"Total Steps: {len(logs)}"
    )


def _safe_status_banner() -> str:
    status = _ui_env.state_data.safe_harbour_status.upper()
    compliance = _ui_env.state_data.compliance_health
    missed = _ui_env.state_data.missed_deadlines
    return (
        f"Safe Harbour: {status}\n"
        f"Compliance Health: {compliance:.2f}\n"
        f"Missed Deadlines: {missed}"
    )


def _episode_options() -> List[str]:
    opts = []
    for idx, ep in enumerate(_ui_episode_history[-_MAX_HISTORY:], start=1):
        opts.append(f"{idx}. {ep['task_id']} | score={ep['score']:.3f} | steps={len(ep['logs'])}")
    return opts


def ui_reset(task_id: str):
    global _ui_obs, _ui_done, _ui_step_logs
    obs = _ui_env.reset(task_id)
    _ui_obs = obs.model_dump()
    _ui_done = False
    _ui_step_logs = []
    status = f"Task: {task_id} | Items: {len(_ui_env.current_queue)} | Max Steps: {TASK_DATA[task_id]['max_steps']}"
    return (
        _format_observation(_ui_obs),
        "Reset complete. Ready for first step.",
        status,
        "No steps yet.",
        "No behavior data yet.",
        _final_metrics([]),
        _safe_status_banner(),
        gr.Dropdown(choices=_episode_options(), value=None),
    )


def ui_step(
    decision: str,
    rule_cited: str,
    evidence_input: str,
    confidence: float,
    reason: str,
    notify_user: bool,
    stress_mode: bool,
):
    global _ui_obs, _ui_done, _ui_step_logs
    if _ui_done:
        return (
            _format_observation(_ui_obs or {}),
            "Episode complete. Reset to start a new task.",
            "",
            _format_timeline(_ui_step_logs),
            _behavior_summary(_ui_step_logs),
            _final_metrics(_ui_step_logs),
            _safe_status_banner(),
            gr.Dropdown(choices=_episode_options(), value=None),
        )
    if not _ui_obs:
        return (
            "No active episode. Reset first.",
            "No active episode.",
            "",
            "No steps yet.",
            "No behavior data yet.",
            _final_metrics([]),
            _safe_status_banner(),
            gr.Dropdown(choices=_episode_options(), value=None),
        )

    signals = [s.strip() for s in evidence_input.split(",") if s.strip()]
    final_decision = decision
    if stress_mode and allow_experimental_features():
        final_decision = random.choice(_VALID_DECISIONS)

    try:
        action = DharmaShieldAction(
            decision=final_decision,
            rule_cited=rule_cited if rule_cited else "UNKNOWN",
            evidence_signals=signals,
            confidence=float(confidence),
            reason=reason if reason else "manual_ui_action",
            notify_user=notify_user,
        )
        start = time.time()
        obs_model, reward_model, done, info = _ui_env.step(action)
        latency_ms = (time.time() - start) * 1000.0

        _ui_obs = obs_model.model_dump()
        _ui_done = done

        _ui_step_logs.append(
            {
                "step": _ui_env.state_data.current_step,
                "decision": action.decision,
                "rule": action.rule_cited,
                "reward": reward_model.step_reward,
                "latency_ms": latency_ms,
                "safe_harbour_status": _ui_env.state_data.safe_harbour_status,
                "compliance_health": _ui_env.state_data.compliance_health,
            }
        )

        if done:
            score = reward_model.cumulative_episode_score
            _ui_episode_history.append(
                {
                    "task_id": _ui_env.state_data.task_id,
                    "score": score,
                    "logs": list(_ui_step_logs),
                }
            )
            del _ui_episode_history[:-_MAX_HISTORY]

        return (
            _format_observation(_ui_obs),
            _format_reward(reward_model.model_dump(), done, info.model_dump()),
            f"Step {_ui_env.state_data.current_step} | Cumulative: {reward_model.cumulative_episode_score:.4f}",
            _format_timeline(_ui_step_logs),
            _behavior_summary(_ui_step_logs),
            _final_metrics(_ui_step_logs),
            _safe_status_banner(),
            gr.Dropdown(choices=_episode_options(), value=None),
        )
    except Exception as exc:
        return (
            _format_observation(_ui_obs),
            f"Error: {str(exc)}",
            "",
            _format_timeline(_ui_step_logs),
            _behavior_summary(_ui_step_logs),
            _final_metrics(_ui_step_logs),
            _safe_status_banner(),
            gr.Dropdown(choices=_episode_options(), value=None),
        )


def ui_export_csv():
    if not _ui_step_logs:
        return "No episode logs available for export."
    path = export_episode_to_csv(_ui_step_logs)
    return f"Exported: {path}"


def ui_replay(selection: str):
    if not selection:
        return "Select an episode to replay.", "No behavior data yet."
    try:
        idx = int(selection.split(".", 1)[0]) - 1
        if idx < 0 or idx >= len(_ui_episode_history):
            return "Invalid replay selection.", "No behavior data yet."
        logs = _ui_episode_history[idx]["logs"]
        return _format_timeline(logs), _behavior_summary(logs)
    except Exception:
        return "Invalid replay selection.", "No behavior data yet."


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
.panel-card { background:#111827; border:1px solid #2d3148; border-radius:8px; padding:10px; }
"""


def build_ui():
    with gr.Blocks(css=CSS, title="DharmaShield - Trust and Safety Ops") as demo:
        gr.Markdown("## DharmaShield Operations Dashboard")
        gr.Markdown("_Trust & Safety simulation console (non-blocking UI over live environment state)_")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Task Control")
                task_selector = gr.Dropdown(choices=TASK_ORDER, value=TASK_ORDER[0], label="Task", interactive=True)
                reset_btn = gr.Button("Reset Episode", variant="primary")
                status_bar = gr.Textbox(label="Session Status", interactive=False, lines=1)

                gr.Markdown("### Action")
                decision_input = gr.Dropdown(
                    choices=_VALID_DECISIONS,
                    value="request_human_review",
                    label="Decision",
                    interactive=True,
                )
                rule_input = gr.Textbox(label="Rule Cited", placeholder="IT_2021_3_1_b_iii", value="UNKNOWN")
                evidence_input = gr.Textbox(label="Evidence Signals (comma-separated)", placeholder="upi_pin_request, prize_scam")
                confidence_input = gr.Slider(minimum=0.0, maximum=1.0, step=0.05, value=0.8, label="Confidence")
                reason_input = gr.Textbox(label="Reason", placeholder="Brief policy rationale...")
                notify_input = gr.Checkbox(label="Notify User", value=False)
                stress_input = gr.Checkbox(label="Stress Mode", value=False, interactive=allow_experimental_features())
                step_btn = gr.Button("Submit Step")
                export_btn = gr.Button("Export CSV")
                export_status = gr.Textbox(label="Export Status", interactive=False, lines=1)
                final_metrics = gr.Textbox(label="Episode Metrics", lines=4, interactive=False, value=_final_metrics([]))
                safe_banner = gr.Textbox(label="Compliance Status", lines=4, interactive=False, value=_safe_status_banner())

            with gr.Column(scale=2):
                gr.Markdown("### Current Observation")
                obs_display = gr.Textbox(
                    label="Content Item + Account Meta",
                    lines=24,
                    interactive=False,
                    value="Reset a task to begin.",
                )
                timeline_display = gr.Textbox(label="Timeline", lines=8, interactive=False, value="No steps yet.")

            with gr.Column(scale=1):
                gr.Markdown("### Reward Signal")
                reward_display = gr.Textbox(label="Step Reward Breakdown", lines=12, interactive=False)
                behavior_display = gr.Textbox(label="Behavior Analytics", lines=8, interactive=False, value="No behavior data yet.")
                replay_dropdown = gr.Dropdown(choices=[], label="Replay Episode", interactive=True)
                replay_btn = gr.Button("Replay Selected")

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

        reset_btn.click(
            fn=ui_reset,
            inputs=[task_selector],
            outputs=[obs_display, reward_display, status_bar, timeline_display, behavior_display, final_metrics, safe_banner, replay_dropdown],
        )
        step_btn.click(
            fn=ui_step,
            inputs=[decision_input, rule_input, evidence_input, confidence_input, reason_input, notify_input, stress_input],
            outputs=[obs_display, reward_display, status_bar, timeline_display, behavior_display, final_metrics, safe_banner, replay_dropdown],
        )
        replay_btn.click(
            fn=ui_replay,
            inputs=[replay_dropdown],
            outputs=[timeline_display, behavior_display],
        )
        export_btn.click(fn=ui_export_csv, outputs=[export_status])

    return demo
