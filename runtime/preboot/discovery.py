from __future__ import annotations
from ice_core.logging.router import get_logger
# src/ice_studio/preboot/discovery.py

import platform
import re
import socket
import subprocess
import time
from dataclasses import dataclass, asdict
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from engine.security.pairing import load_trusted_hosts

log = get_logger("icenet", "discovery", "ice.preboot.discovery")
log.debug("[DISCOVERY] module loaded")

# ---------------------------------------------------------------------
# TIMING / LIMITS
# ---------------------------------------------------------------------
ARP_ONLY_MAX_SEC = 3.0
HELLO_PHASE_MAX_SEC = 12.0
FALLBACK_SWEEP_MAX_SEC = 30.0
HARD_STOP_SEC = 60.0

PING_TIMEOUT_SEC = 0.35
HELLO_TIMEOUT_SEC = 0.9

CONCURRENCY = 128
BATCH_SIZE = 64
MAX_IPS_PER_SCAN = 256

socket.setdefaulttimeout(PING_TIMEOUT_SEC)

# ---------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------
@dataclass
class Device:
    ip: str
    hostname: str | None = None
    host_id: str | None = None
    ice: bool = False
    status: str = "generic"
    latency_ms: int | None = None
    fingerprint: str | None = None
    pairing: dict | None = None
    raw: dict | None = None


# ---------------------------------------------------------------------
# LOW LEVEL UTILS
# ---------------------------------------------------------------------
def _run(cmd: list[str], timeout: float) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        return p.returncode, out.strip()
    except Exception as e:
        return 99, str(e)


def _ping(ip: str) -> tuple[bool, int | None]:
    sys = platform.system().lower()
    if "windows" in sys:
        cmd = ["ping", "-n", "1", "-w", str(int(PING_TIMEOUT_SEC * 1000)), ip]
    else:
        cmd = ["ping", "-c", "1", ip]

    t0 = time.time()
    code, _ = _run(cmd, timeout=PING_TIMEOUT_SEC + 0.4)
    dt = int((time.time() - t0) * 1000)
    return (code == 0), dt if code == 0 else None


def _guess_lan_prefix() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ".".join(ip.split(".")[:3])
    except Exception:
        return "192.168.1"


def probe_ice(ip: str, port: int = 7040) -> bool:
    url = f"http://{ip}:{port}/preboot/hello"
    req = Request(url, headers={"User-Agent": "ICE-Studio-Preboot/1.0"})
    try:
        with urlopen(req, timeout=HELLO_TIMEOUT_SEC) as r:
            body = r.read().decode("utf-8", errors="ignore")
            return ("ice" in body.lower()) or (r.status == 200)
    except (URLError, HTTPError):
        return False
    except Exception:
        return False


def _is_valid_ip(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _extract_ips(text: str) -> list[str]:
    if not text:
        return []
    out = []
    for m in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text):
        if _is_valid_ip(m):
            out.append(m)
    return out


def is_router_ip(ip: str) -> bool:
    return ip.endswith(".1") or ip.endswith(".254")


def get_arp_hosts() -> list[str]:
    hosts: list[str] = []
    cmds = [["arp", "-a"]]
    if platform.system().lower().startswith("linux"):
        cmds.insert(0, ["ip", "neigh"])

    for cmd in cmds:
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
            hosts.extend(_extract_ips(output))
        except Exception:
            pass

    uniq = []
    seen = set()
    for ip in hosts:
        if ip not in seen and not is_router_ip(ip):
            uniq.append(ip)
            seen.add(ip)
    return uniq


# ---------------------------------------------------------------------
# DISCOVERY CORE
# ---------------------------------------------------------------------
def scan_lan(max_hosts: int = 254, probe: bool = True, on_host=None) -> list[dict]:
    raise RuntimeError("Legacy LAN discovery disabled. Use discovery_v2 (UDP-based).")

    trusted_hosts = load_trusted_hosts()
    max_hosts = min(max_hosts, MAX_IPS_PER_SCAN)

    candidate_ips: set[str] = set()
    scanned_ips: set[str] = set()
    devices: list[dict] = []
    ice_found = False

    # self ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self_ip = s.getsockname()[0]
        s.close()
    except Exception:
        self_ip = None

    def is_candidate(ip: str) -> bool:
        if not _is_valid_ip(ip):
            return False
        if is_router_ip(ip):
            return False
        if ip == self_ip:
            return False
        if ip.split(".")[-1] in {"0", "255"}:
            return False
        return True

    # --------------------------------------------------
    # COLLECT INITIAL CANDIDATES
    # --------------------------------------------------
    for item in trusted_hosts.values():
        ip = item.get("ip") if isinstance(item, dict) else getattr(item, "ip", None)
        if ip and is_candidate(ip):
            candidate_ips.add(ip)

    arp_hosts = [ip for ip in get_arp_hosts() if not is_router_ip(ip)]

    for ip in arp_hosts:
        if is_candidate(ip):
            candidate_ips.add(ip)

    log.debug(
        "[DISCOVERY] initial candidates",
        extra={"count": len(candidate_ips)},
    )

    # --------------------------------------------------
    # SCAN FUNCTION
    # --------------------------------------------------
    def scan_ip(ip: str):
        if ip in scanned_ips:
            return None

        scanned_ips.add(ip)

        ok, latency = _ping(ip)
        if not ok:
            return None

        d = Device(ip=ip, latency_ms=latency, status="available")

        try:
            d.hostname = socket.gethostbyaddr(ip)[0]
        except Exception:
            d.hostname = None

        d.host_id = d.hostname or ip

        trusted = trusted_hosts.get(d.host_id)
        if not trusted:
            for t in trusted_hosts.values():
                if getattr(t, "ip", None) == ip:
                    trusted = t
                    break

        if probe:
            d.ice = probe_ice(ip)

        if trusted:
            d.status = "paired"
            d.pairing = {"paired": True, "pending": False}
            d.fingerprint = getattr(trusted, "fingerprint", None)
        else:
            d.pairing = {"paired": False, "pending": False}

        payload = asdict(d)
        return payload

    # --------------------------------------------------
    # RUN BATCH
    # --------------------------------------------------
    def run_batch(batch: list[str]):
        if not batch:
            return
        nonlocal ice_found
        with ThreadPoolExecutor(max_workers=min(CONCURRENCY, len(batch))) as ex:
            futures = [ex.submit(scan_ip, ip) for ip in batch]
            for f in as_completed(futures):
                if ice_found:
                    break
                try:
                    payload = f.result()
                except Exception:
                    continue
                if not payload:
                    continue
                devices.append(payload)
                if on_host:
                    try:
                        on_host(payload)
                    except Exception:
                        log.exception("on_host callback failed")
                log.info("[DISCOVERY] Host up", extra={"ip": payload["ip"]})
                if payload.get("ice"):
                    ice_found = True
                    log.info("[DISCOVERY] ICE host detected, stopping further scan", extra={"ip": payload["ip"]})
                    break

    # --------------------------------------------------
    # PHASE 1 — INITIAL (trusted + ARP)
    # --------------------------------------------------
    initial = list(candidate_ips)
    log.debug("[DISCOVERY] phase=initial batch", extra={"count": len(initial)})
    run_batch(initial)
    if ice_found:
        log.debug("[DISCOVERY] ICE host found during initial phase, skipping fallback")
        duration_ms = int((time.time() - start_ts) * 1000)
        log.info(
            "[DISCOVERY] LAN scan complete",
            extra={
                "count": len(devices),
                "duration_ms": duration_ms,
                "scanned_ips": len(scanned_ips),
                "phase": "initial",
            },
        )
        return devices

    # --------------------------------------------------
    # PHASE 2 — FALLBACK (time-bound, only if no ICE)
    # --------------------------------------------------
    fallback_deadline = min(hard_deadline, start_ts + FALLBACK_SWEEP_MAX_SEC)
    log.debug("[DISCOVERY] entering fallback loop", extra={"deadline_sec": FALLBACK_SWEEP_MAX_SEC})

    i = 1
    while (
        not ice_found
        and time.time() < fallback_deadline
        and len(scanned_ips) < max_hosts
        and i <= max_hosts
    ):
        batch: list[str] = []

        while (
            len(batch) < BATCH_SIZE
            and i <= max_hosts
            and time.time() < fallback_deadline
            and not ice_found
        ):
            ip = f"{prefix}.{i}"
            i += 1
            if ip in candidate_ips or ip in scanned_ips:
                continue
            if not is_candidate(ip):
                continue
            candidate_ips.add(ip)
            batch.append(ip)

        if not batch:
            time.sleep(0.05)
            continue

        log.debug(
            "[DISCOVERY] phase=fallback batch",
            extra={"count": len(batch), "i": i},
        )
        run_batch(batch)

    duration_ms = int((time.time() - start_ts) * 1000)
    log.info(
        "[DISCOVERY] LAN scan complete",
        extra={
            "count": len(devices),
            "duration_ms": duration_ms,
            "scanned_ips": len(scanned_ips),
        },
    )

    return devices


# ---------------------------------------------------------------------
# REMOTE PROBE
# ---------------------------------------------------------------------
def probe_remote_target(target: str) -> dict:
    if not target or not target.strip():
        raise ValueError("invalid_target")

    raw = target.strip()
    if not re.match(r"^https?://", raw):
        raw = f"http://{raw}"

    parsed = urlparse(raw)
    host = parsed.hostname
    port = parsed.port or 7040

    try:
        ip = socket.gethostbyname(host)
    except Exception:
        ip = host

    log.info("[DISCOVERY] Probing remote host", extra={"host": host, "port": port})

    device = Device(ip=ip, hostname=host, host_id=host, status="generic")

    if probe_ice(ip, port):
        device.ice = True
        device.status = "available"

    trusted_hosts = load_trusted_hosts()
    trusted = trusted_hosts.get(host)

    if trusted:
        device.status = "paired"
        device.pairing = {"paired": True, "pending": False}
        device.fingerprint = getattr(trusted, "fingerprint", None)
    else:
        device.pairing = {"paired": False, "pending": False}

    payload = asdict(device)
    payload["host_id"] = host
    return payload
