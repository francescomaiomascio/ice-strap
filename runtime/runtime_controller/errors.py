class RuntimeControllerError(Exception):
    """Errore base Runtime Controller"""


class InvalidDecisionError(RuntimeControllerError):
    pass


class PolicyViolationError(RuntimeControllerError):
    pass


class LifecycleError(RuntimeControllerError):
    pass


class SpawnError(RuntimeControllerError):
    pass
