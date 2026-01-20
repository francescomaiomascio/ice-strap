from __future__ import annotations
from pathlib import Path
from typing import Protocol
import subprocess


class BackendContract(Protocol):
    def start(self, runtime_dir: Path) -> subprocess.Popen: ...


class AIRuntimeContract(Protocol):
    def start(self, runtime_dir: Path) -> subprocess.Popen: ...
