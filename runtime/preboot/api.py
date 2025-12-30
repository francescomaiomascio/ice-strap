from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from engine.logging.router import get_logger
from engine.preboot.context import get_preboot_context
from engine.preboot.discovery_v2 import discover_lan
from engine.preboot.runtime import init_runtime_commit
from engine.security.identity import get_local_identity, NodeRole

router = APIRouter()
log = get_logger(
    domain="preboot",
    owner="commit",
    scope="preboot.commit",
)


@router.get("/preboot/network/scan")
def scan_lan() -> JSONResponse:
    """
    REST wrapper FastAPI per la LAN discovery del preboot.

    - Usa discover_lan() v2 (UDP only, pairing-aware).
    - Esclude l'host locale (stesso comportamento di main.py).
    - Torna un payload compatibile con il preboot HTTP server:
      { scope, count, duration_ms, hosts, devices }.
    """
    # Escludiamo loopback + host locale
    ident = get_local_identity(NodeRole.HOST)
    local_ip = getattr(ident, "ip", None)
    local_id = getattr(ident, "host_id", None) or getattr(ident, "node_id", None)

    exclude_ips: Set[str] = {"127.0.0.1", "::1"}
    if local_ip:
        exclude_ips.add(local_ip)

    exclude_ids: Set[str] = set()
    if local_id:
        exclude_ids.add(local_id)

    start = time.time()
    hosts: List[Dict[str, Any]] = discover_lan(
        timeout=1.2,
        exclude_ips=exclude_ips,
        exclude_ids=exclude_ids,
    )
    duration_ms = int((time.time() - start) * 1000)

    payload: Dict[str, Any] = {
        "scope": "lan",
        "count": len(hosts),
        "duration_ms": duration_ms,
        "hosts": hosts,
        # per retro–compatibilità con vecchia UI
        "devices": hosts,
    }
    return JSONResponse(payload)


@router.post("/preboot/commit")
def commit_preboot_decision() -> Dict[str, Any]:
    ctx = get_preboot_context()

    if os.environ.get("ICE_RUNTIME_DIR") or os.environ.get("ICE_RUNTIME_ID"):
        raise HTTPException(
            status_code=409,
            detail="Runtime already initialized",
        )

    if ctx.decision is None:
        raise HTTPException(
            status_code=400,
            detail="No decision available to commit",
        )

    try:
        runtime_dir = init_runtime_commit()
    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail="Runtime directory collision",
        )
    ctx.runtime_dir = str(runtime_dir)

    decision = ctx.decision.copy()
    decision["version"] = 1
    decision["decided_at"] = datetime.now(timezone.utc).isoformat()

    decision_path = runtime_dir / "decision.json"
    if decision_path.exists():
        raise HTTPException(
            status_code=409,
            detail="Decision already committed",
        )

    decision_path.write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )

    log.info(
        "Preboot decision committed",
        data={
            "runtime_dir": str(runtime_dir),
            "mode": decision.get("mode"),
        },
    )

    ctx.state = "COMMITTED"

    env = os.environ.copy()
    env["ICE_RUNTIME_DIR"] = str(runtime_dir)
    env["ICE_STUDIO_PHASE"] = "runtime"
    subprocess.Popen(
        [sys.executable, "-m", "engine.runtime_controller"],
        env=env,
        stdout=None,
        stderr=None,
    )

    return {
        "status": "committed",
        "runtime_dir": str(runtime_dir),
        "decision": decision,
    }
