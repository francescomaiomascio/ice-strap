"""
Canonical ICE bootstrap sequence.

strap → engine → runtime
"""

from ice_strap.preboot.checks import run_checks
from ice_strap.preboot.discovery import (
    discover_environment,
    discover_workspace,
)
from ice_strap.preboot.context import BootstrapContext
from .handoff import handoff_to_engine
from .errors import SequenceViolationError


def run() -> None:
    """
    Execute the canonical bootstrap sequence.

    Order is STRICT and NON-NEGOTIABLE.
    """

    # 1. Preboot checks
    run_checks()

    # 2. Discovery
    environment = discover_environment()
    workspace = discover_workspace()

    # 3. Topology decision (stub)
    topology = {}

    # 4. Context creation (IMMUTABLE)
    context = BootstrapContext(
        environment=environment,
        workspace=workspace,
        topology=topology,
    )

    # 5. Authority handoff
    handoff_to_engine(context)

    # 6. Strap must NEVER continue after handoff
    raise SequenceViolationError(
        "Strap execution continued after authority handoff"
    )
