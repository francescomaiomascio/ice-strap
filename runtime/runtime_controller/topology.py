from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

from .errors import InvalidDecisionError


@dataclass(frozen=True)
class TopologyDecision:
    mode: str               # local | remote
    host: str | None = None


def load_decision(runtime_dir: Path) -> TopologyDecision:
    decision_file = runtime_dir / "decision.json"
    if not decision_file.exists():
        raise InvalidDecisionError("decision.json missing")

    try:
        data = json.loads(decision_file.read_text())
    except Exception as e:
        raise InvalidDecisionError(f"decision.json invalid: {e}")

    mode = data.get("mode")
    host = data.get("host")

    if mode not in ("local", "remote"):
        raise InvalidDecisionError(f"Invalid mode: {mode}")

    if mode == "remote" and not host:
        raise InvalidDecisionError("Remote mode requires host")

    return TopologyDecision(mode=mode, host=host)
