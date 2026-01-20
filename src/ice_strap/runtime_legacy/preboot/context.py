from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RemoteDiscoveryState:
    """
    Stato minimo lato backend per la discovery remota.

    NOTA: è indipendente dal PrebootContext JS, ma segue la stessa idea:
    - scope: 'lan' | 'wan'
    - scanning: true/false
    - discovered_hosts: lista di host visti nell'ultima scansione
    - seen_ips: set per dedup
    - scan_started_at: timestamp (epoch) della scansione corrente
    """
    scope: Optional[str] = None
    scanning: bool = False
    discovered_hosts: list[dict] = field(default_factory=list)
    seen_ips: set[str] = field(default_factory=set)
    scan_started_at: float | None = None


class PrebootContext:
    """
    Contesto backend di preboot.

    - mode: 'local' | 'remote' | 'cloud'
    - per_mode: stato specifico per modalità (remote/local).
    """

    def __init__(self, runtime_dir: str) -> None:
        self.runtime_dir = runtime_dir
        self.decision: dict | None = None
        self.state: str = "INIT"
        self.mode: Optional[str] = None
        self.per_mode: Dict[str, Any] = {
            "remote": RemoteDiscoveryState(),
            "local": {},
        }

    def update(self, payload: Dict[str, Any]) -> None:
        """
        Merge shallow del payload sul contesto corrente.
        """
        if not isinstance(payload, dict):
            return

        self.mode = payload.get("mode", self.mode)

        per_mode = payload.get("per_mode")
        if isinstance(per_mode, dict):
            # merge shallow per compatibilità
            self.per_mode.update(per_mode)

        decision = payload.get("decision")
        if isinstance(decision, dict):
            self.decision = decision
        elif "mode" in payload and self.mode:
            resources = payload.get("resources")
            if not isinstance(resources, dict):
                resources = {
                    "backend": {"type": "local"},
                    "ai_runtime": {
                        "type": "local",
                        "llm": True,
                        "embeddings": True,
                    },
                }
            policy = payload.get("policy")
            if not isinstance(policy, dict):
                policy = {
                    "auto_restart": False,
                    "shutdown_on_ui_exit": True,
                }
            self.decision = {
                "mode": self.mode,
                "host": payload.get("host"),
                "resources": resources,
                "policy": policy,
            }

    @property
    def data(self) -> Dict[str, Any]:
        """
        Snapshot serializzabile del contesto.
        """
        return {
            "mode": self.mode,
            "per_mode": self.per_mode,
        }

    def add_discovered_host(self, host: dict) -> None:
        """
        Aggiunge un host scoperto in LAN nel ramo 'remote',
        deduplicando per IP.
        """
        if not isinstance(host, dict):
            return

        ip = host.get("ip")
        if not ip:
            return

        rd: RemoteDiscoveryState = self.per_mode.get("remote")  # type: ignore[assignment]
        if not isinstance(rd, RemoteDiscoveryState):
            rd = RemoteDiscoveryState()
            self.per_mode["remote"] = rd

        if ip not in rd.seen_ips:
            rd.seen_ips.add(ip)
            rd.discovered_hosts.append(host)


_PREBOOT_CONTEXT: Optional[PrebootContext] = None


def get_preboot_context() -> PrebootContext:
    global _PREBOOT_CONTEXT
    if _PREBOOT_CONTEXT is None:
        runtime_dir = os.environ.get("ICE_RUNTIME_DIR", "")
        _PREBOOT_CONTEXT = PrebootContext(runtime_dir)
    return _PREBOOT_CONTEXT
