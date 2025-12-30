from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict

from engine.logging.router import get_logger

log = get_logger("runtime", "llm", "ai_runtime.launcher")


def spawn_llama_launcher(
    runtime_dir: Path,
    role: str,
    extra_env: Dict[str, str],
) -> subprocess.Popen:
    """
    Spawn llama_launcher.js as a child process.
    """
    launcher = Path("tools/ai_runtime/llama_launcher.js").resolve()

    llm_dir = runtime_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("ICE_STUDIO_LLAMA_SERVER_BIN", "llama-server")
    env.setdefault(
        "ICE_STUDIO_LLM_MODEL_PATH",
        "/home/mothx/Codes/ice-studio/models/qwen/qwen2.5-coder-7b-instruct-q4_k_m-00001-of-00002.gguf",
    )
    env.setdefault(
        "ICE_STUDIO_EMBED_MODEL_PATH",
        "/home/mothx/Codes/ice-studio/models/embeddings/bge-small-en-v1.5.Q4_K_M.gguf",
    )
    env.update(extra_env)

    log_file = llm_dir / f"{role}-lifecycle.log"

    log.info(
        "Spawning AI launcher",
        data={
            "role": role,
            "launcher": str(launcher),
            "log_file": str(log_file),
        },
    )

    return subprocess.Popen(
        ["node", str(launcher)],
        env=env,
        stdout=open(log_file, "a"),
        stderr=open(log_file, "a"),
    )
