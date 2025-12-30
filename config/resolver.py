from pathlib import Path
from typing import Dict, Any
import os

def resolve_paths(cfg: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """
    Normalizza tutti i path:
    - ~
    - path relativi
    """

    def _resolve(val):
        if isinstance(val, str):
            if val.startswith("~"):
                return os.path.expanduser(val)
            if val.startswith("./"):
                return str(project_root / val[2:])
        return val

    def walk(node):
        if isinstance(node, dict):
            return {k: walk(_resolve(v)) for k, v in node.items()}
        elif isinstance(node, list):
            return [walk(v) for v in node]
        else:
            return node

    return walk(cfg)
