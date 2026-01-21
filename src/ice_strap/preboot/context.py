"""
BootstrapContext definition.

This context is immutable after creation and contains
all information gathered during the preboot phase.
"""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class BootstrapContext:
    """
    Immutable preboot context.

    It contains validated facts about the environment
    and workspace, to be consumed by bootstrap logic.
    """

    environment: Mapping[str, Any]
    workspace: Mapping[str, Any]
    topology: Mapping[str, Any]
