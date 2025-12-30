import yaml
from pathlib import Path
from typing import Dict, Any

from .merger import deep_merge
from .validator import validate_config

def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_config(
    default_path: Path,
    user_path: Path | None = None,
    workspace_path: Path | None = None,
) -> Dict[str, Any]:

    cfg = load_yaml(default_path)

    if user_path:
        cfg = deep_merge(cfg, load_yaml(user_path))

    if workspace_path:
        cfg = deep_merge(cfg, load_yaml(workspace_path))

    validate_config(cfg)
    return cfg
