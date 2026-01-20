"""
Authority handoff from strap to engine.

This module enforces a forward-only, single-use transfer of control.
"""

from ice_strap.preboot.context import BootstrapContext
from .errors import AuthorityViolationError

_HANDOFF_DONE = False


def handoff_to_engine(context: BootstrapContext) -> None:
    """
    Transfer authority from strap to engine.

    This function may be called exactly once.
    After invocation, strap must exit permanently.
    """
    global _HANDOFF_DONE

    if _HANDOFF_DONE:
        raise AuthorityViolationError(
            "Authority handoff attempted more than once"
        )

    if not isinstance(context, BootstrapContext):
        raise AuthorityViolationError(
            "Invalid bootstrap context passed to engine"
        )

    _HANDOFF_DONE = True

    # Engine invocation is intentionally not implemented here.
    # This function marks the authority boundary only.
    raise NotImplementedError(
        "Engine handoff not implemented yet (STRAP-05)"
    )
