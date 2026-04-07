from pathlib import Path

import yaml


def test_openenv_yaml_has_required_fields():
    data = yaml.safe_load(Path("openenv.yaml").read_text())
    assert data["name"] == "dharma-shield-env"
    assert "tasks" in data and len(data["tasks"]) >= 3
    assert "reward_range" in data
    assert data["reward_range"]["min"] == 0.0
    assert data["reward_range"]["max"] == 1.0
