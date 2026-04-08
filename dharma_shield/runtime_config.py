from __future__ import annotations

import os


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Submission-safe defaults.
SAFE_MODE: bool = _as_bool("SAFE_MODE", True)
VERBOSE: bool = _as_bool("VERBOSE", False)


def allow_experimental_features() -> bool:
    return not SAFE_MODE
