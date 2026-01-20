"""
Authority handoff logic.

This module defines the forward-only authority transfer
from strap to engine.
"""

from .errors import AuthorityViolationError
from ice_strap.preboot.context import BootstrapContext


def handoff_to_engine(context: BootstrapContext) -> None:
    """
    Transfer authority to the engine.

    This function must:
    - be called exactly once
    - never return control to strap
    """
    # NOTE:
    # Real engine invocation happens in STRAP-05.
    # For now, this is a structural placeholder.

    raise NotImplementedError(
        "Engine handoff not implemented yet (STRAP-05)"
    )
