"""
Bootstrap-level error taxonomy.

These errors represent violations of the canonical bootstrap
sequence or illegal execution states.
"""


class BootstrapError(RuntimeError):
    """Base class for all bootstrap-related errors."""


class SequenceViolationError(BootstrapError):
    """Raised when the canonical bootstrap order is violated."""


class AuthorityViolationError(BootstrapError):
    """Raised when authority handoff rules are violated."""


class PrebootError(BootstrapError):
    """Raised when preboot checks or discovery fail."""
