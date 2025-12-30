from __future__ import annotations

import os
from pathlib import Path

from ice_core.logging.bootstrap import init_logging_pipeline


def init_runtime_commit() -> Path:
    launch_dir = os.environ.get("ICE_LAUNCH_DIR")
    if not launch_dir:
        raise RuntimeError("ICE_LAUNCH_DIR not set")
    runtime_dir = Path(launch_dir) / "runtime"
    runtime_dir.mkdir(exist_ok=False)
    (runtime_dir / "ui").mkdir(parents=True, exist_ok=True)
    os.environ["ICE_RUNTIME_DIR"] = str(runtime_dir)
    os.environ["ICE_PHASE"] = "runtime"
    init_logging_pipeline("runtime")
    return runtime_dir
