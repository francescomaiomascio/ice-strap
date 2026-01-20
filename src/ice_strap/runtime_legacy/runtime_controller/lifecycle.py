from __future__ import annotations
from enum import Enum, auto

from .errors import LifecycleError


class RuntimeState(Enum):
    INIT = auto()
    TOPOLOGY_LOADED = auto()
    POLICY_VALIDATED = auto()
    BACKEND_STARTED = auto()
    AI_STARTED = auto()
    RUNNING = auto()
    SHUTDOWN = auto()


class RuntimeLifecycle:
    def __init__(self):
        self.state = RuntimeState.INIT

    def transition(self, next_state: RuntimeState):
        if not self._allowed(self.state, next_state):
            raise LifecycleError(f"Invalid transition {self.state} → {next_state}")
        self.state = next_state

    @staticmethod
    def _allowed(a: RuntimeState, b: RuntimeState) -> bool:
        allowed = {
            RuntimeState.INIT: {RuntimeState.TOPOLOGY_LOADED},
            RuntimeState.TOPOLOGY_LOADED: {RuntimeState.POLICY_VALIDATED},
            RuntimeState.POLICY_VALIDATED: {
                RuntimeState.BACKEND_STARTED,
                RuntimeState.RUNNING,
            },
            RuntimeState.BACKEND_STARTED: {
                RuntimeState.AI_STARTED,
                RuntimeState.RUNNING,
            },
            RuntimeState.AI_STARTED: {RuntimeState.RUNNING},
            RuntimeState.RUNNING: {RuntimeState.SHUTDOWN},
        }
        return b in allowed.get(a, set())
