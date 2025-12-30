from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AIServerStatus:
    name: str
    running: bool
    pid: Optional[int] = None
    url: Optional[str] = None
