from __future__ import annotations
# src/ice_studio/preboot/adapters/snowball_adapter.py

from engine.snowball.api import SnowballAPI
from engine.snowball.agent import SnowballAgent


class SnowballAdapter:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.api = SnowballAPI(SnowballAgent())

    def start_pairing(self):
        self.orchestrator.dispatch("pair_required")

    def on_paired(self):
        self.orchestrator.dispatch("paired")

    def on_reject(self):
        self.orchestrator.dispatch("reject")
