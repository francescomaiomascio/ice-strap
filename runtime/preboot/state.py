from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Session bootstrap
# ---------------------------------------------------------------------------

SESSION_ID = f"preboot-{secrets.token_hex(4)}"


def get_session_info() -> Dict[str, str]:
    return {
        "session_id": SESSION_ID,
        "launch_dir": os.environ.get("ICE_LAUNCH_DIR", ""),
        "launch_id": os.environ.get("ICE_LAUNCH_ID", ""),
    }


# ---------------------------------------------------------------------------
# In-memory preboot state
# ---------------------------------------------------------------------------

@dataclass
class PrebootState:
    # local | remote | cloud
    mode: Optional[str] = None
    # idle | discovering | done (solo per UI di discovery)
    discovery: Optional[str] = None
    # ultimo host selezionato dalla UI
    selected_host: Optional[Dict[str, Any]] = None
    # errore di preboot (se presente)
    error: Optional[str] = None


@dataclass
class PrebootDecision:
    decided: bool = False
    committed: bool = False
    mode: Optional[str] = None
    host: Optional[Dict[str, Any]] = None
    resources: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrebootStatus:
    state: PrebootState
    decision: PrebootDecision


STATE = PrebootState()
DECISION = PrebootDecision()


def current_status() -> PrebootStatus:
    """
    Snapshot corrente della macchina di stato di preboot
    (usato da /preboot/status per la UI).
    """
    return PrebootStatus(state=STATE, decision=DECISION)
