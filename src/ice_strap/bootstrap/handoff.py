"""
Authority handoff from strap to engine.

This module defines the forward-only transfer of control.
"""

from ice_strap.preboot.context import BootstrapContext


def handoff_to_engine(context: BootstrapContext) -> None:
    raise NotImplementedError("Engine handoff not implemented yet (STRAP-05)")
