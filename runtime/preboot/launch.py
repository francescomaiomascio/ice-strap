from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import secrets


def generate_launch_id() -> str:
    return f"launch-{secrets.token_hex(4)}"


def create_launch_dir(project_root: Path) -> Path:
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
    launch_id = generate_launch_id()
    launch_dir = (
        project_root
        / "logs"
        / "launches"
        / f"{ts}__{launch_id}"
    )
    launch_dir.mkdir(parents=True, exist_ok=False)
    return launch_dir
