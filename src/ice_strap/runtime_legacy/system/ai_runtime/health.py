from __future__ import annotations

import time
import requests
from typing import Dict, Optional

from ice_core.logging.router import get_logger

logger = get_logger("llm", "health", "ai_runtime.health")


class AIServerHealth:
    def __init__(self, role: str, base_url: str, model: Optional[str] = None):
        self.role = role  # "llm" | "embeddings"
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.state = "starting"
        self._logged_ready = False

    def check(self, timeout: float = 0.5) -> bool:
        """
        Ritorna True se il server è READY.
        Usa /v1/models come probe standard OpenAI-compat.
        """
        try:
            resp = requests.get(
                f"{self.base_url}/v1/models",
                timeout=timeout,
            )
            if resp.status_code != 200:
                return False

            payload = resp.json()
            models = payload.get("data") or payload.get("models") or []
            if not models:
                return False

            # READY
            self._set_ready()
            return True

        except Exception:
            return False

    def _set_ready(self) -> None:
        if self.state == "ready":
            return

        self.state = "ready"

        if not self._logged_ready:
            logger.info(
                f"{self.role} server ready",
                data={
                    "role": self.role,
                    "url": f"{self.base_url}/v1",
                    "model": self.model,
                },
            )
            self._logged_ready = True

    def as_status(self) -> Dict:
        return {
            "state": self.state,
            "url": f"{self.base_url}/v1",
            "model": self.model,
        }


def wait_until_ready(
    server: AIServerHealth,
    retries: int = 20,
    interval: float = 0.5,
) -> bool:
    """
    Polling bloccante leggero.
    """
    for _ in range(retries):
        if server.check():
            return True
        time.sleep(interval)
    return False
