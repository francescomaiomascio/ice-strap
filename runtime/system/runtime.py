from __future__ import annotations
# src/ice_studio/system/runtime.py

import asyncio
import json
import os
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from engine.backend.ws_server import IceWSServer
from engine.agents.domain.system_agent import SystemAgent
from engine.preboot.state import DECISION, STATE
from engine.logging.api import set_phase
from engine.logging.router import get_logger
from engine.system.ai_runtime.manager import AIExecutionManager

logger = get_logger("backend", "core", "ice.system.runtime")


class SystemRuntime:
    """
    ICE Studio System Runtime

    Responsabilità:
    - backend server
    - system agent
    - llm runtime
    - stato osservabile

    NON:
    - workspace
    - UI
    - decisioni di topology
    """

    def __init__(self) -> None:
        self._started = False
        self._lock = threading.Lock()

        self.backend: Optional[IceWSServer] = None
        self.system_agent: Optional[SystemAgent] = None
        self.llm: Optional["LLMAdapter"] = None
        self.ai_manager: Optional[AIExecutionManager] = None
        self.code_model_agent = None

        self._started_at: Optional[float] = None

    # ------------------------------------------------------------------ #
    # PUBLIC API
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """
        Avvia il System Runtime.
        Idempotente.
        """
        with self._lock:
            if self._started:
                logger.info("SystemRuntime already started")
                return

            if not DECISION.decided:
                runtime_dir = os.environ.get("ICE_RUNTIME_DIR")
                if runtime_dir:
                    decision_path = Path(runtime_dir) / "decision.json"
                    try:
                        payload = json.loads(decision_path.read_text())
                        DECISION.mode = payload.get("mode")
                        DECISION.host = payload.get("host")
                        DECISION.resources = payload.get("resources", {})
                        DECISION.decided = True
                        logger.info("Loaded runtime decision from disk")
                    except Exception as err:
                        logger.warning(
                            "Failed to load runtime decision",
                            extra={"error": str(err)},
                        )

            if not DECISION.decided:
                raise RuntimeError("SystemRuntime cannot start: preboot not decided")

            logger.info(
                "Starting ICE System Runtime (mode=%s host=%s)",
                DECISION.mode,
                DECISION.host,
            )

            set_phase("dashboard")
            logger.info("Backend core started", data={"phase": "dashboard"})
            get_logger("backend", "dashboard", "backend.dashboard").info(
                "Dashboard runtime context ready",
                data={"phase": "dashboard"},
            )
            self._start_backend()
            runtime_dir_env = os.environ.get("ICE_RUNTIME_DIR")
            if runtime_dir_env:
                self.ai_manager = AIExecutionManager(
                    Path(runtime_dir_env)
                )
                self.ai_manager.start()
                logger.info(
                    "AI Runtime manager attached (external launcher expected)",
                    data={"mode": "node"},
                )
            else:
                logger.warn(
                    "AI Runtime skipped: ICE_RUNTIME_DIR not set"
                )

            self._started = True
            self._started_at = time.time()

            logger.info("Waiting for AI runtime readiness")
            if self.ai_manager and self.ai_manager.wait_until_ready(timeout=30):
                logger.info("AI runtime ready, bootstrapping agents")
                self._start_system_agent()
                self._start_code_model_agent()
            else:
                logger.error(
                    "AI runtime not ready, agent bootstrap deferred"
                )
                if self.ai_manager:
                    def _wait_for_ai() -> None:
                        if self.ai_manager.wait_until_ready(timeout=300):
                            logger.info(
                                "AI runtime ready (late), bootstrapping agents"
                            )
                            self._start_system_agent()
                            self._start_code_model_agent()

                    thread = threading.Thread(
                        target=_wait_for_ai,
                        name="ai-runtime-waiter",
                        daemon=True,
                    )
                    thread.start()

            logger.info("ICE System Runtime READY")

    def status(self) -> Dict[str, Any]:
        return {
            "started": self._started,
            "started_at": self._started_at,
            "mode": DECISION.mode,
            "host": DECISION.host,
            "components": {
                "backend": self.backend is not None,
                "llm": self.ai_manager.is_ready() if self.ai_manager else False,
                "system_agent": self.system_agent is not None,
                "code_model_agent": self.code_model_agent is not None,
            },
            "ai": self.ai_manager.status() if self.ai_manager else None,
        }

    # ------------------------------------------------------------------ #
    # INTERNALS
    # ------------------------------------------------------------------ #

    def _start_backend(self) -> None:
        logger.info("Starting backend WS server")

        self.backend = IceWSServer()

        def run_backend():
            try:
                asyncio.run(self.backend.start())
            except Exception as err:
                logger.error(
                    "Backend WS failed to start",
                    extra={"error": str(err)},
                )

        thread = threading.Thread(
            target=run_backend,
            name="ice-backend-thread",
            daemon=True,
        )
        thread.start()

    def _start_llm(self) -> None:
        logger.info("Starting LLM runtime")
        try:
            from engine.llm.adapter import LLMAdapter
        except Exception as err:
            logger.warn(
                "LLM runtime skipped: LLMAdapter not available",
                data={"error": str(err)},
            )
            return
        self.llm = LLMAdapter()
        self.llm.start()

    def _start_system_agent(self) -> None:
        logger.info("System Agent registered (legacy, async)")
        self.system_agent = SystemAgent()

    def _start_code_model_agent(self) -> None:
        logger.info("Starting CodeModelAgent")
        from engine.agents.llm_agents.code_model_agent import (
            CodeModelAgent,
        )
        self.code_model_agent = CodeModelAgent()
        self.code_model_agent.start()


# ----------------------------------------------------------------------
# GLOBAL INSTANCE
# ----------------------------------------------------------------------

_SYSTEM_RUNTIME: Optional[SystemRuntime] = None


def ensure_system_runtime() -> SystemRuntime:
    global _SYSTEM_RUNTIME

    if _SYSTEM_RUNTIME is None:
        _SYSTEM_RUNTIME = SystemRuntime()
        _SYSTEM_RUNTIME.start()

    return _SYSTEM_RUNTIME


def system_status() -> Dict[str, Any]:
    runtime = ensure_system_runtime()
    return runtime.status()
