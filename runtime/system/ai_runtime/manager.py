from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ice_core.logging.router import get_logger
from engine.preboot.state import DECISION

from .health import AIServerHealth, wait_until_ready

log = get_logger("runtime", "llm", "ai_runtime.manager")
health_log = get_logger("llm", "health", "ai_runtime.health")

DEFAULT_LLM_PORT = 8000
DEFAULT_EMB_PORT = 8100
DEFAULT_LLM_MODEL = "qwen2.5-coder-7b-instruct"
DEFAULT_EMB_MODEL = "bge-small-en-v1.5"


class AIExecutionManager:
    """
    Manages LLM + embeddings runtime (local / remote).
    """

    def __init__(self, runtime_dir: Path):
        self.runtime_dir = runtime_dir
        self.mode = DECISION.mode
        self.llm_health: Optional[AIServerHealth] = None
        self.emb_health: Optional[AIServerHealth] = None

        log.info(
            "AIExecutionManager initialized",
            data={"mode": self.mode, "runtime_dir": str(runtime_dir)},
        )

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    def start(self) -> None:
        log.info("AIExecutionManager.start")

        if self.mode == "remote":
            log.info("Remote mode -> local AI servers NOT started")
            return

        self._init_llm_health()
        self._init_embeddings_health()

    def wait_until_ready(self, timeout: float = 30.0) -> bool:
        if self.mode == "remote":
            return True
        ready_llm = True
        ready_emb = True
        if self.llm_health:
            retries = max(1, int(timeout / 0.5))
            ready_llm = wait_until_ready(
                self.llm_health,
                retries=retries,
                interval=0.5,
            )
        if self.emb_health:
            retries = max(1, int(timeout / 0.5))
            ready_emb = wait_until_ready(
                self.emb_health,
                retries=retries,
                interval=0.5,
            )
        return ready_llm and ready_emb

    def is_ready(self) -> bool:
        if self.mode == "remote":
            return True
        llm_ready = (
            self.llm_health is not None
            and self.llm_health.state == "ready"
        )
        emb_ready = (
            self.emb_health is not None
            and self.emb_health.state == "ready"
        )
        return llm_ready and emb_ready

    def status(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {
            "llm": {"state": "off"},
            "embeddings": {"state": "off"},
        }

        if self.llm_health:
            status["llm"] = self.llm_health.as_status()
        if self.emb_health:
            status["embeddings"] = self.emb_health.as_status()

        for name in ("llm", "embeddings"):
            status[name]["running"] = status[name].get("state") == "ready"
        return status

    def stop(self) -> None:
        return

    # --------------------------------------------------
    # INTERNALS
    # --------------------------------------------------

    def _init_llm_health(self) -> None:
        log.info("Initializing local LLM health")

        llm_url = os.environ.get("ICE_STUDIO_LLM_BASE_URL")
        if not llm_url:
            llm_url = f"http://127.0.0.1:{DEFAULT_LLM_PORT}/v1"
            os.environ["ICE_STUDIO_LLM_BASE_URL"] = llm_url

        model = os.environ.get("ICE_STUDIO_LLM_MODEL_ID") or DEFAULT_LLM_MODEL

        self.llm_health = AIServerHealth(
            role="llm",
            base_url=llm_url.replace("/v1", ""),
            model=model,
        )
        self._start_health_monitor(self.llm_health)

    def _init_embeddings_health(self) -> None:
        log.info("Initializing local Embeddings health")

        emb_url = os.environ.get("ICE_STUDIO_EMBEDDINGS_LOCAL_URL")
        if not emb_url:
            emb_url = f"http://127.0.0.1:{DEFAULT_EMB_PORT}/v1"
            os.environ["ICE_STUDIO_EMBEDDINGS_LOCAL_URL"] = emb_url
        model = (
            os.environ.get("ICE_STUDIO_EMBED_MODEL_ID") or DEFAULT_EMB_MODEL
        )
        self.emb_health = AIServerHealth(
            role="embeddings",
            base_url=emb_url.replace("/v1", ""),
            model=model,
        )
        self._start_health_monitor(self.emb_health)

    def _start_health_monitor(
        self,
        server: AIServerHealth,
        interval: float = 1.0,
    ) -> None:
        def _poll() -> None:
            while True:
                if server.check():
                    return
                time.sleep(interval)

        thread = threading.Thread(
            target=_poll,
            name=f"ai-health-{server.role}",
            daemon=True,
        )
        thread.start()
