from __future__ import annotations

import time
from typing import Dict, List, Set

from engine.network.udp_discovery import udp_discovery
from engine.security.pairing import load_trusted_hosts, list_pairings
from engine.logging.router import get_logger

log = get_logger("icenet", "discovery", "ice.preboot.discovery")


def discover_lan(
    on_host=None,
    *,
    timeout: float = 1.2,
    exclude_ips: Set[str] | None = None,
    exclude_ids: Set[str] | None = None,
) -> List[Dict]:
    """
    Discovery LAN ICE — SOLO via UDP.
    - Usa udp_discovery() per trovare i nodi ICE sulla LAN.
    - Marca i nodi già pairati come "paired".
    - Permette di escludere IP/ID noti (macchina locale, ecc.).
    """
    exclude_ips = set(exclude_ips or ())
    exclude_ids = set(exclude_ids or ())

    start = time.time()
    log.info("[DISCOVERY] UDP discovery started")

    devices = udp_discovery(timeout=timeout)

    # trusted_hosts: mapping host_id -> TrustedHost (per fingerprint / metadata)
    trusted_hosts = load_trusted_hosts()

    # pairings: lista di host_id/ip persistenti (pairings.json)
    pairings = list_pairings() or []
    trusted_ids = {
        getattr(p, "host_id", None) or (p.get("host_id") if isinstance(p, dict) else None)
        for p in pairings
    }
    trusted_ips = {
        getattr(p, "ip", None) or (p.get("ip") if isinstance(p, dict) else None)
        for p in pairings
    }
    trusted_ids = {tid for tid in trusted_ids if tid}
    trusted_ips = {tip for tip in trusted_ips if tip}

    results: List[Dict] = []

    for d in devices:
        ip = d.get("ip")
        host_id = d.get("node_id") or d.get("hostname") or ip

        if not ip:
            continue

        # Escludi host locali / già noti
        if ip in exclude_ips or host_id in exclude_ids:
            continue

        pairing_state = {"paired": False, "pending": False}
        fingerprint = None

        # Host considerato "paired" se:
        # - presente nello store legacy trusted_hosts
        # - o incluso in pairings.json (host_id o ip)
        if host_id in trusted_hosts or host_id in trusted_ids or ip in trusted_ips:
            pairing_state = {"paired": True, "pending": False}
            trusted_entry = trusted_hosts.get(host_id)
            if trusted_entry:
                fingerprint = getattr(trusted_entry, "fingerprint", None)

        payload = {
            "ip": ip,
            "hostname": d.get("hostname"),
            "host_id": host_id or ip,
            "ice": True,
            "status": "paired" if pairing_state["paired"] else "available",
            "fingerprint": fingerprint,
            "pairing": pairing_state,
            "raw": d,
        }

        results.append(payload)

        if on_host:
            on_host(payload)

        log.info("[DISCOVERY] ICE node found", extra={"ip": payload["ip"]})

    duration_ms = int((time.time() - start) * 1000)
    log.info(
        "[DISCOVERY] UDP discovery finished",
        extra={"count": len(results), "duration_ms": duration_ms},
    )

    return results
