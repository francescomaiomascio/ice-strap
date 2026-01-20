from __future__ import annotations
from pathlib import Path
import atexit
import json
import os
import signal
import socket
import subprocess
import sys
import time

from ice_core.logging.router import get_logger
from engine.system.ai_runtime.launcher import spawn_llama_launcher

from .topology import load_decision
from .policy import RuntimePolicy
from .lifecycle import RuntimeLifecycle, RuntimeState
from .errors import LifecycleError, SpawnError


log = get_logger(
    domain="runtime",
    owner="controller",
    scope="runtime.controller",
)


class RuntimeController:
    def __init__(self, runtime_dir: Path):
        self.runtime_dir = runtime_dir
        self.lifecycle = RuntimeLifecycle()
        self.children: list[subprocess.Popen] = []
        self.backend_proc: subprocess.Popen | None = None
        self.ai_proc: subprocess.Popen | None = None
        self.backend_port = 7030

    def start(self):
        log.info("RuntimeController starting", data={"runtime_dir": str(self.runtime_dir)})

        signal.signal(signal.SIGINT, lambda *_: self.shutdown())
        signal.signal(signal.SIGTERM, lambda *_: self.shutdown())

        self._register_cleanup()
        if os.environ.get("ICE_PHASE") != "runtime":
            raise RuntimeError("ICE_PHASE is not runtime")
        launch_dir = os.environ.get("ICE_LAUNCH_DIR")
        if not launch_dir:
            raise RuntimeError("ICE_LAUNCH_DIR not set")
        decision_path = Path(launch_dir) / "runtime" / "decision.json"
        if not decision_path.exists():
            raise RuntimeError("decision.json missing in runtime directory")
        if not self.runtime_dir.exists():
            raise RuntimeError(
                "Runtime directory missing – preboot violation"
            )
        self._acquire_lock()

        decision = load_decision(self.runtime_dir)
        self.lifecycle.transition(RuntimeState.TOPOLOGY_LOADED)

        RuntimePolicy.validate(decision)
        self.lifecycle.transition(RuntimeState.POLICY_VALIDATED)

        if RuntimePolicy.can_start_backend(decision):
            self._start_backend()

        if RuntimePolicy.can_start_ai(decision):
            self._start_ai()

        if self.lifecycle.state not in (
            RuntimeState.BACKEND_STARTED,
            RuntimeState.AI_STARTED,
        ):
            raise LifecycleError("Runtime started with no active components")

        self.lifecycle.transition(RuntimeState.RUNNING)
        log.info("Runtime running")

    def _start_backend(self):
        log.info("Starting backend")
        try:
            if not self._port_free(self.backend_port):
                raise RuntimeError(
                    f"Backend port {self.backend_port} already in use"
                )
            env = {
                **os.environ,
                "ICE_RUNTIME_DIR": str(self.runtime_dir),
                "ICE_STUDIO_PHASE": "runtime",
                "ICE_PHASE": "runtime",
            }
            proc = subprocess.Popen(
                [sys.executable, "-m", "engine.backend.main"],
                env=env,
            )
            self.backend_proc = proc
            self.children.append(proc)
            self.lifecycle.transition(RuntimeState.BACKEND_STARTED)
        except Exception as e:
            raise SpawnError(f"Backend failed: {e}")

    def _start_ai(self):
        log.info("Starting AI Runtime")
        try:
            proc = spawn_llama_launcher(
                runtime_dir=self.runtime_dir,
                role="local",
                extra_env={},
            )
            self.ai_proc = proc
            self.children.append(proc)
            self.lifecycle.transition(RuntimeState.AI_STARTED)
        except Exception as e:
            raise SpawnError(f"AI Runtime failed: {e}")

    def stop(self):
        if self.backend_proc:
            try:
                self.backend_proc.terminate()
            except Exception:
                pass
        if self.ai_proc:
            try:
                self.ai_proc.terminate()
            except Exception:
                pass

    def shutdown(self):
        log.info("RuntimeController shutdown")
        self.stop()
        for p in self.children:
            try:
                p.terminate()
            except Exception:
                pass
        self._release_lock()
        self.lifecycle.transition(RuntimeState.SHUTDOWN)

    def _acquire_lock(self):
        lock_file = self.runtime_dir / "runtime.lock"

        if lock_file.exists():
            data = json.loads(lock_file.read_text())
            pid = data.get("pid")

            if pid and self._pid_alive(pid):
                raise RuntimeError(
                    f"Runtime already running (pid={pid})"
                )
            lock_file.unlink()

        lock_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "backend_port": self.backend_port,
                }
            )
        )

    def _release_lock(self):
        lock_file = self.runtime_dir / "runtime.lock"
        try:
            lock_file.unlink()
        except FileNotFoundError:
            pass

    def _pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _port_free(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(("127.0.0.1", port)) != 0

    def _register_cleanup(self):
        atexit.register(self._release_lock)
