from pathlib import Path
from typing import Dict, Any
import yaml

from .merger import deep_merge
from .validator import validate_config
from .resolver import resolve_paths

BASE_DIR = Path(__file__).resolve().parents[1]

DEFAULT_PATH = BASE_DIR / "config" / "defaults" / "default.yaml"
USER_PATH = Path.home() / ".config" / "ice_studio" / "settings.yaml"
WORKSPACE_PATH = Path.cwd() / ".ice_studio" / "settings.yaml"


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config() -> Dict[str, Any]:
    cfg = load_yaml(DEFAULT_PATH)
    cfg = deep_merge(cfg, load_yaml(USER_PATH))
    cfg = deep_merge(cfg, load_yaml(WORKSPACE_PATH))

    cfg = resolve_paths(cfg)
    validate_config(cfg)
    return cfg
