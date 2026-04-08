from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def export_episode_to_csv(logs: List[Dict[str, object]], out_dir: str = "artifacts") -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = Path(out_dir) / f"episode_log_{stamp}.csv"
    fieldnames = [
        "step",
        "decision",
        "rule",
        "reward",
        "latency_ms",
        "safe_harbour_status",
        "compliance_health",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in logs:
            writer.writerow({k: row.get(k) for k in fieldnames})
    return str(path)
