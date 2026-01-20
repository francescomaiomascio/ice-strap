from __future__ import annotations

import os
import sys
from pathlib import Path

from ice_core.logging.router import get_logger
from engine.runtime_controller.controller import RuntimeController


log = get_logger(
    domain="runtime",
    owner="bootstrap",
    scope="runtime.bootstrap",
)


def main() -> None:
    launch_dir_env = os.environ.get("ICE_LAUNCH_DIR")
    if not launch_dir_env:
        raise RuntimeError("runtime_controller started without Launch context")
    if os.environ.get("ICE_PHASE") != "runtime":
        raise RuntimeError("runtime_controller started outside runtime phase")

    runtime_dir_env = os.environ.get("ICE_RUNTIME_DIR")
    if not runtime_dir_env:
        raise RuntimeError("ICE_RUNTIME_DIR not set")

    runtime_dir = Path(runtime_dir_env).resolve()
    log.info("Runtime bootstrap starting", data={"runtime_dir": str(runtime_dir)})

    controller = RuntimeController(runtime_dir)
    controller.start()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.exception("Runtime bootstrap failed", data={"error": str(e)})
        sys.exit(1)
