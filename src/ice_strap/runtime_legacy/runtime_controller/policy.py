from __future__ import annotations
from .topology import TopologyDecision
from .errors import PolicyViolationError


class RuntimePolicy:
    """
    Regole di avvio runtime.
    Qui si decide COSA può partire.
    """

    @staticmethod
    def can_start_backend(decision: TopologyDecision) -> bool:
        return decision.mode == "local"

    @staticmethod
    def can_start_ai(decision: TopologyDecision) -> bool:
        return decision.mode == "local"

    @staticmethod
    def validate(decision: TopologyDecision) -> None:
        if decision.mode == "remote":
            # In remoto nulla parte localmente
            return

        if decision.mode == "local":
            return

        raise PolicyViolationError(f"Unhandled policy for mode {decision.mode}")
