"""
DharmaShield GRPO Training Example
===================================
Minimal reference implementation for training against DharmaShield endpoints.
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
    rewards = []
    for completion in completions:
        try:
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

    print("Step 1: Verifying environment connectivity...")
    try:
        health = httpx.get(f"{SERVER_URL}/health", timeout=5)
        print(f"  Health: {health.json()}")
    except Exception as e:
        print(f"  ERROR: Cannot connect to server. Start it first: {e}")
        raise SystemExit(1)

    print("\nStep 2: Running baseline episodes...")
    for task_id in ["upi-scam-triage", "sgi-compliance-review"]:
        run_baseline_episode(task_id)

    print("\nStep 3: GRPO training loop (reference)")
    print("  Install dependencies: pip install trl>=0.8.0 transformers>=4.40.0")
    print("  Then adapt the commented training block to your infra.")
