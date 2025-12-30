from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from engine.logging.bootstrap import init_logging_pipeline
from engine.logging.router import get_logger
from engine.preboot.launch import create_launch_dir
from engine.preboot.runtime import init_runtime_commit

from engine.backend.logging import HttpLogger  # noqa: E402
from engine.preboot.state import (  # noqa: E402
    STATE,
    DECISION,
    SESSION_ID,
    current_status,
    get_session_info,
)
from engine.preboot.discovery_v2 import discover_lan  # noqa: E402
from engine.security.identity import get_local_identity, NodeRole  # noqa: E402
from engine.security.network import identity_payload  # noqa: E402
from engine.security.pairing import (  # noqa: E402
    approve_pairing,
    create_pairing_request,
    pairing_status,
    list_pairings,
)
from engine.preboot.system_verify import verify_local_runtime  # noqa: E402
from engine.network.udp_responder import start_udp_responder  # noqa: E402

logger = get_logger("preboot", "preboot", "ice.preboot")

HOST = "0.0.0.0"
PORT = 7040

# Stato VPN stub (verrà sostituito in ICENET futuri)
VPN_STATUS: Dict[str, Any] = {
    "configured": False,
    "connected": False,
    "tunnel_ip": None,
    "latency_ms": None,
}

HTTP_LOGGER = HttpLogger(SESSION_ID)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _tcp_ping(ip: str, port: int, timeout: float = 0.25) -> bool:
    """
    Tiny TCP probe usato solo per capire se un host trusted è online.
    Non fa discovery, solo best-effort reachability.
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def _trusted_hosts_online() -> List[Dict[str, Any]]:
    """
    Ritorna l’elenco dei flake già pairati (pairings.json) con un flag di reachability
    sui port 7040/7030. Nessuna UDP discovery qui.
    """
    out: List[Dict[str, Any]] = []
    pairings = list_pairings() or []

    for p in pairings:
        # Supportiamo sia dataclass che dict per compatibilità
        ip = getattr(p, "ip", None) or (p.get("ip") if isinstance(p, dict) else None)
        host_id = (
            getattr(p, "host_id", None)
            or (p.get("host_id") if isinstance(p, dict) else None)
            or ip
        )
        if not ip:
            continue

        online_7040 = _tcp_ping(ip, 7040)
        online_7030 = _tcp_ping(ip, 7030)

        out.append(
            {
                "host_id": host_id,
                "ip": ip,
                "online": bool(online_7040 or online_7030),
                "ports": {"7040": online_7040, "7030": online_7030},
            }
        )

    return out


# ---------------------------------------------------------------------------
# HTTP HANDLER
# ---------------------------------------------------------------------------

class PrebootHandler(BaseHTTPRequestHandler):
    """
    HTTP controller del preboot.

    Espone:
    - /preboot/network, /preboot/network/scan
    - /preboot/pairing/* (request / approve / status / list / online)
    - /preboot/decide (commit finale delle scelte runtime)
    """

    # --------------------- low-level helpers ------------------------------

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, payload: Dict[str, Any]) -> None:
        try:
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(_json_bytes(payload))
        except BrokenPipeError:
            logger.info("Client closed connection before response could be sent")
        finally:
            self._log_http_event(code)

    # --------------------- HTTP verbs -------------------------------------

    def do_OPTIONS(self) -> None:
        self._request_start = time.time()
        self.send_response(204)
        self._cors()
        self.end_headers()
        self._log_http_event(204)

    def do_GET(self) -> None:
        self._request_start = time.time()
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # ---- small probe to know preboot is alive ------------------------
        if path == "/preboot/hello":
            self._json(
                200,
                {
                    "ice": True,
                    "service": "preboot",
                    "ts": int(time.time()),
                },
            )
            return

        # ---- pairing status / list / online ------------------------------
        if path == "/preboot/pairing/status":
            host_id = params.get("host_id", [""])[0].strip()
            self._json(200, pairing_status(host_id))
            return

        if path == "/preboot/pairing/list":
            self._json(200, {"pairings": list_pairings()})
            return

        if path == "/preboot/pairing/online":
            hosts = _trusted_hosts_online()
            self._json(200, {"hosts": hosts})
            return

        # ---- network info ------------------------------------------------
        if path == "/preboot/network":
            # Info sulla macchina locale (NODE_ID, hostname, ip, ecc.)
            self._json(200, identity_payload())
            return

        if path == "/preboot/network/scan":
            logger.info("[PREBOOT] LAN scan requested")
            try:
                ident = get_local_identity(NodeRole.HOST)
                local_ip = getattr(ident, "ip", None)
                local_id = getattr(ident, "host_id", None) or getattr(
                    ident, "node_id", None
                )

                exclude_ips = {"127.0.0.1", "::1"}
                if local_ip:
                    exclude_ips.add(local_ip)

                exclude_ids = set()
                if local_id:
                    exclude_ids.add(local_id)

                start = time.time()
                hosts = discover_lan(
                    timeout=1.2,
                    exclude_ips=exclude_ips,
                    exclude_ids=exclude_ids,
                )
                duration_ms = int((time.time() - start) * 1000)

                self._json(
                    200,
                    {
                        "hosts": hosts,
                        "count": len(hosts),
                        "duration_ms": duration_ms,
                        "scope": "lan",
                    },
                )
            except Exception as err:
                logger.exception("LAN scan failed: %s", err)
                self._json(500, {"error": "scan_failed", "detail": str(err)})
            return

        if path == "/preboot/network/scan/stream":
            # vecchio endpoint SSE, mantenuto solo per compatibilità
            logger.info("[PREBOOT] LAN scan stream endpoint deprecated")
            self._json(410, {"error": "scan_stream_deprecated"})
            return

        # ---- preboot and system status ----------------------------------
        if path == "/preboot/status":
            self._json(200, asdict(current_status()))
            return

        if path == "/preboot/system/verify":
            logger.info("[PREBOOT] system verify requested")
            result = verify_local_runtime()
            self._json(200, result)
            return

        if path == "/preboot/session":
            self._json(200, get_session_info())
            return

        # ---- VPN stub ----------------------------------------------------
        if path == "/vpn/status":
            self._json(200, VPN_STATUS)
            return

        # ---- manual host probe (WAN / manual IP) ------------------------
        if path == "/host/probe":
            target = params.get("target", [""])[0].strip()
            if not target:
                self._json(400, {"error": "missing_target"})
            else:
                ip = target
                online = _tcp_ping(ip, 7040) or _tcp_ping(ip, 7030)
                self._json(
                    200,
                    {
                        "host": {
                            "host_id": ip,
                            "ip": ip,
                            "hostname": "manual_host",
                            "ice": True,
                            "status": "available" if online else "offline",
                        }
                    },
                )
            return

        # ---- not found ---------------------------------------------------
        self._json(404, {"error": "not_found", "path": path})
        return

    def do_POST(self) -> None:
        self._request_start = time.time()
        parsed = urlparse(self.path)
        path = parsed.path

        def read_json() -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                return json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return {}

        # ---- pairing: request (client → preboot) -------------------------
        if path == "/preboot/pairing/request":
            data = read_json()
            pairing = create_pairing_request(data)
            self._json(200, pairing.__dict__)
            return

        # ---- pairing: approve (daemon → preboot) -------------------------
        if path == "/preboot/pairing/approve":
            data = read_json()
            req_id = data.get("request_id")
            if not req_id:
                self._json(400, {"ok": False, "error": "missing_request_id"})
                return
            ok = approve_pairing(req_id)
            self._json(200, {"ok": ok})
            return

        # ---- host pairing notify (preboot → daemon) ----------------------
        if path == "/host/pairing/notify":
            data = read_json()
            ip = data.get("ip")
            host_id = data.get("host_id") or ip
            request_id = data.get("request_id")

            if not ip:
                self._json(400, {"error": "missing_ip"})
                return
            if not request_id:
                self._json(400, {"error": "missing_request_id"})
                return

            try:
                import urllib.request

                payload = {
                    "host_id": host_id,
                    "request_id": request_id,
                    "message": "Pairing request pending approval",
                    "client_ip": self.client_address[0],
                }

                req = urllib.request.Request(
                    f"http://{ip}:7030/daemon/ui/pairing",
                    data=_json_bytes(payload),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    ok = resp.status == 200

                self._json(200, {"ok": ok})
            except Exception as err:
                logger.error("host pairing notify failed: %s", err)
                self._json(200, {"ok": False, "detail": str(err)})
            return

        # ---- preboot final decision (mode / host / resources) ------------
        if path == "/preboot/decide":
            data = read_json()

            DECISION.mode = data.get("mode")
            DECISION.host = data.get("host")
            DECISION.resources = data.get("resources", {})
            if DECISION.mode == "local":
                backend = DECISION.resources.get("backend") or {}
                if not backend:
                    DECISION.resources["backend"] = {
                        "type": "local",
                        "host": "localhost",
                        "mode": "embedded",
                    }
            DECISION.decided = True

            logger.info("Preboot decided: %s", DECISION)
            self._json(
                200,
                {
                    "ok": True,
                    "decision": {
                        "mode": DECISION.mode,
                        "host": DECISION.host,
                        "resources": DECISION.resources,
                    },
                },
            )
            return

        if path == "/preboot/commit":
            data = read_json()

            logger.info(
                "[DEBUG] commit check",
                extra={
                    "decided": DECISION.decided,
                    "committed": DECISION.committed,
                    "mode": DECISION.mode,
                    "host": DECISION.host,
                    "env_runtime": os.environ.get("ICE_RUNTIME_DIR"),
                },
            )

            if DECISION.committed:
                self._json(409, {"error": "Decision already committed"})
                return

            if os.environ.get("ICE_RUNTIME_DIR") or os.environ.get("ICE_RUNTIME_ID"):
                self._json(409, {"error": "Runtime already initialized"})
                return

            if DECISION.mode is None:
                DECISION.mode = data.get("mode")
                DECISION.host = data.get("host")
                DECISION.resources = data.get("resources", {})
                if DECISION.mode == "local":
                    backend = DECISION.resources.get("backend") or {}
                    if not backend:
                        DECISION.resources["backend"] = {
                            "type": "local",
                            "host": "localhost",
                            "mode": "embedded",
                        }
                DECISION.decided = True

            try:
                runtime_dir = init_runtime_commit()
            except FileExistsError:
                self._json(409, {"error": "Runtime directory collision"})
                return
            decision_path = runtime_dir / "decision.json"

            policy = data.get("policy")
            if not isinstance(policy, dict):
                policy = {
                    "auto_restart": False,
                    "shutdown_on_ui_exit": True,
                }

            decision_payload = {
                "version": 1,
                "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "mode": DECISION.mode,
                "host": DECISION.host,
                "resources": DECISION.resources,
                "policy": policy,
            }

            try:
                decision_path.write_text(
                    json.dumps(decision_payload, indent=2),
                    encoding="utf-8",
                )
            except Exception as err:
                logger.error(
                    "Failed to persist runtime decision",
                    extra={"error": str(err)},
                )
                self._json(500, {"error": "Failed to write decision.json"})
                return

            logger.info(
                "Preboot decision committed",
                extra={"mode": DECISION.mode, "runtime_dir": str(runtime_dir)},
            )
            DECISION.committed = True
            env = os.environ.copy()
            env["ICE_RUNTIME_DIR"] = str(runtime_dir)
            env["ICE_STUDIO_PHASE"] = "runtime"
            env["ICE_PHASE"] = "runtime"
            subprocess.Popen(
                [sys.executable, "-m", "engine.runtime_controller"],
                env=env,
                stdout=None,
                stderr=None,
            )
            self._json(
                200,
                {
                    "status": "committed",
                    "runtime_dir": str(runtime_dir),
                    "decision": decision_payload,
                },
            )
            return

        # ---- VPN stub endpoints -----------------------------------------
        if path == "/vpn/setup":
            VPN_STATUS["configured"] = True
            self._json(
                200,
                {
                    **VPN_STATUS,
                    "message": "VPN configuration saved (stub)",
                },
            )
            return

        if path == "/vpn/connect":
            VPN_STATUS.update(
                {
                    "configured": True,
                    "connected": True,
                    "tunnel_ip": "10.42.0.2",
                    "latency_ms": 27,
                }
            )
            self._json(200, VPN_STATUS)
            return

        if path == "/vpn/disconnect":
            VPN_STATUS.update(
                {
                    "connected": False,
                    "tunnel_ip": None,
                    "latency_ms": None,
                }
            )
            self._json(200, VPN_STATUS)
            return

        # ---- not found ---------------------------------------------------
        self._json(404, {"error": "not_found", "path": path})
        return

    def log_message(self, format: str, *args: Any) -> None:
        # silence default HTTP logging
        return

    def _log_http_event(
        self,
        status: int,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        duration_ms: Optional[int] = None
        if hasattr(self, "_request_start"):
            duration_ms = int((time.time() - getattr(self, "_request_start")) * 1000)
        HTTP_LOGGER.log(
            method=getattr(self, "command", None),
            path=getattr(self, "path", None),
            status=status,
            duration_ms=duration_ms,
            transport="rest",
            extra=extra,
        )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    lock_path = Path("/tmp/ice-preboot.lock")
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
            os.kill(pid, 0)
            raise RuntimeError(f"Preboot already running (pid={pid})")
        except ProcessLookupError:
            lock_path.unlink()
        except ValueError:
            lock_path.unlink()
    lock_path.write_text(str(os.getpid()))

    project_root = Path(
        os.environ.get("ICE_STUDIO_PROJECT_ROOT") or Path.cwd()
    )
    os.environ.pop("ICE_RUNTIME_DIR", None)
    os.environ.pop("ICE_RUNTIME_ID", None)
    if "ICE_LAUNCH_DIR" in os.environ:
        launch_dir = Path(os.environ["ICE_LAUNCH_DIR"])
    else:
        launch_dir = create_launch_dir(project_root)
    (launch_dir / "preboot" / "ui").mkdir(parents=True, exist_ok=True)
    os.environ["ICE_LAUNCH_DIR"] = str(launch_dir)
    os.environ["ICE_LAUNCH_ID"] = launch_dir.name
    os.environ["ICE_PHASE"] = "preboot"

    init_logging_pipeline("preboot")

    logger.info("ICE Studio PREBOOT starting on %s:%s", HOST, PORT)

    # UDP responder per discovery LAN (broadcast identità host locale)
    try:
        identity = get_local_identity(NodeRole.HOST)
        start_udp_responder(identity.__dict__)
    except Exception as err:
        logger.error("Failed to start UDP responder: %s", err)

    server = HTTPServer((HOST, PORT), PrebootHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Preboot server interrupted, shutting down")
    finally:
        server.server_close()
        logger.info("Preboot server stopped")
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
