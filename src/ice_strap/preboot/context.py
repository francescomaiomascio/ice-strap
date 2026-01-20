"""
BootstrapContext definition.

This context is immutable after creation and is handed off
exactly once to the engine.
"""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class BootstrapContext:
    """
    Immutable bootstrap context.

    It contains all information required by the engine to
    continue execution after strap exits.
    """

    environment: Mapping[str, Any]
    workspace: Mapping[str, Any]
    topology: Mapping[str, Any]
