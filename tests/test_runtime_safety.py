from __future__ import annotations

import io
from contextlib import redirect_stdout

import inference
from dharma_shield.environment import DharmaShieldEnvironment
from dharma_shield.runtime_config import allow_experimental_features


def test_safe_mode_default_enabled():
    assert inference.SAFE_MODE is True


def test_verbose_default_disabled():
    assert inference.VERBOSE is False


def test_experimental_features_disabled_in_safe_mode():
    assert allow_experimental_features() is False


def test_router_log_suppressed_when_not_verbose(capsys):
    inference._log_router("ok", "detail")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_run_task_still_prints_end_on_model_exception():
    env = DharmaShieldEnvironment()
    original_call_model = inference._call_model
    try:
        def _boom(_obs):
            raise RuntimeError("forced")

        inference._call_model = _boom
        stream = io.StringIO()
        with redirect_stdout(stream):
            rewards, actions, error = inference.run_task(env, "upi-scam-triage")
        out = stream.getvalue()
        assert "[START]" in out
        assert "[END] success=false" in out
        assert rewards == []
        assert actions == []
        assert error is not None
    finally:
        inference._call_model = original_call_model


def test_benchmark_script_has_artifact_integrity_guard():
    with open("scripts/run_leaderboard_strict.sh", "r", encoding="utf-8") as handle:
        script = handle.read()
    assert 'grep -q "fallbacks=0" "$log_file"' in script


def test_server_has_ui_failsafe_mount():
    with open("dharma_shield/server.py", "r", encoding="utf-8") as handle:
        code = handle.read()
    assert "Mount Gradio UI at /ui with non-fatal fallback." in code
    assert "except Exception as exc" in code
