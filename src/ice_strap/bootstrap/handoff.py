"""
Authority handoff from strap to engine.

This module enforces a forward-only, single-use transfer of authority.
After handoff, strap must permanently relinquish control.
"""

from ice_strap.preboot.context import BootstrapContext

from .errors import AuthorityViolationError

_AUTHORITY_TRANSFERRED = False


def handoff_to_engine(context: BootstrapContext) -> None:
    """
    Transfer authority from strap to engine.

    This function marks the irreversible boundary between
    bootstrap and execution.

    It may be called exactly once.
    After successful invocation, strap must exit permanently.
    """
    global _AUTHORITY_TRANSFERRED

    if _AUTHORITY_TRANSFERRED:
        raise AuthorityViolationError("Authority has already been transferred from strap")

    if not isinstance(context, BootstrapContext):
        raise AuthorityViolationError("Invalid bootstrap context passed to authority handoff")

    # Mark authority as irrevocably transferred
    _AUTHORITY_TRANSFERRED = True

    # Engine invocation is intentionally not implemented here.
    # This function defines the authority boundary only.
    raise NotImplementedError("Engine handoff not implemented yet (STRAP-05)")
