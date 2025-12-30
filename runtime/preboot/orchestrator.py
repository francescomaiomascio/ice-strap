from __future__ import annotations
# src/ice_studio/preboot/orchestrator.py

import secrets
from typing import Dict

SESSION_ID = f"preboot-{secrets.token_hex(4)}"

from .state_graph import StateGraph
from .adapter.snowball_adapter import SnowballAdapter
from .context import get_preboot_context


class PrebootOrchestrator:
    def __init__(self) -> None:
        self.ctx = get_preboot_context()
        self.graph = self._build_graph()
        self.state = self.graph.initial

        self.snowball = SnowballAdapter(self)

    def _build_graph(self) -> StateGraph:
        g = StateGraph(initial="INIT")

        for s in [
            "INIT",
            "VERIFY_LOCAL",
            "SELECT_MODE",
            "HOST_CONFIG",
            "PAIRING",
            "RESOURCES",
            "CONFIRM",
            "READY",
            "ERROR",
        ]:
            g.add_state(s)

        g.add_transition("INIT", "start", "VERIFY_LOCAL")
        g.add_transition("VERIFY_LOCAL", "ok", "SELECT_MODE")
        g.add_transition("VERIFY_LOCAL", "fail", "ERROR")

        g.add_transition("SELECT_MODE", "local", "RESOURCES")
        g.add_transition("SELECT_MODE", "remote", "HOST_CONFIG")
        g.add_transition("SELECT_MODE", "cloud", "HOST_CONFIG")

        g.add_transition("HOST_CONFIG", "pair_required", "PAIRING")
        g.add_transition("HOST_CONFIG", "host_ready", "RESOURCES")
        g.add_transition("HOST_CONFIG", "host_found", "HOST_CONFIG")

        g.add_transition("PAIRING", "paired", "RESOURCES")
        g.add_transition("PAIRING", "reject", "ERROR")

        g.add_transition("RESOURCES", "done", "CONFIRM")
        g.add_transition("CONFIRM", "apply", "READY")

        return g

    def dispatch(self, event: str, payload: Dict | None = None) -> str:
        payload = payload or {}
        self.ctx.update(payload)

        prev_state = self.state
        next_state = self.graph.next_state(self.state, event, self.ctx.data)
        self.state = next_state
        return self.state

    def handle_discovered_host(self, host: Dict):
        self.ctx.add_discovered_host(host)
        self.dispatch("host_found", {"host": host})
