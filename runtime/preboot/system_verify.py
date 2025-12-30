from __future__ import annotations

import os
import platform
import subprocess
from typing import Any, Dict, Optional
from ice_core.logging.router import get_logger

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None

logger = get_logger("preboot", "system_verify", "ice.preboot.system_verify")


def _get_memory_info() -> Dict[str, Any]:
    if not psutil:
        logger.warning("psutil not available; memory info unavailable")
        return {
            "total_gb": None,
            "free_gb": None,
            "used_gb": None,
            "util_pct": None,
            "source": "unavailable",
        }
    try:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024 ** 3), 1),
            "free_gb": round(mem.available / (1024 ** 3), 1),
            "used_gb": round((mem.total - mem.available) / (1024 ** 3), 1),
            "util_pct": round(mem.percent, 1),
            "source": "psutil",
        }
    except Exception:
        return {
            "total_gb": None,
            "free_gb": None,
            "used_gb": None,
            "util_pct": None,
            "source": "unavailable",
        }


def _get_cpu_model(system: str) -> Optional[str]:
    if system == "linux":
        try:
            out = subprocess.check_output(["lscpu"], text=True)
            for line in out.splitlines():
                if "Model name:" in line:
                    return line.split(":", 1)[1].strip()
        except Exception:
            return None
    try:
        return platform.processor() or None
    except Exception:
        return None


def _get_cpu_usage_pct() -> Optional[float]:
    if not psutil:
        return None
    try:
        return round(psutil.cpu_percent(interval=None), 2)
    except Exception:
        return None


def _detect_nvidia_gpu() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "present": False,
        "name": None,
        "vram_total_gb": None,
        "vram_free_gb": None,
        "load_pct": None,
    }
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return info

        first_line = result.stdout.strip().splitlines()[0]
        name, total, used, free, util = [
            part.strip() for part in first_line.split(",", 4)
        ]

        total_mb = float(total)
        free_mb = float(free)
        info.update(
            {
                "present": True,
                "name": name,
                "vram_total_gb": round(total_mb / 1024, 2),
                "vram_free_gb": round(free_mb / 1024, 2),
                "load_pct": int(util),
            }
        )
        return info
    except Exception:
        return info


def verify_local_runtime() -> Dict[str, Any]:
    logger.info("[PREBOOT] system verify start")
    system = platform.system().lower()
    arch = platform.machine()
    cpu_cores = os.cpu_count()
    memory = _get_memory_info()
    cpu_model = _get_cpu_model(system)
    cpu_usage_pct = _get_cpu_usage_pct()

    if system == "linux":
        gpu_info = _detect_nvidia_gpu()
    elif system == "darwin":
        gpu_info = {
            "present": False,
            "name": "Apple Silicon GPU",
            "vram_total_gb": None,
            "vram_free_gb": None,
            "load_pct": None,
        }
    else:
        gpu_info = {
            "present": False,
            "name": None,
            "vram_total_gb": None,
            "vram_free_gb": None,
            "load_pct": None,
        }

    result = {
        "platform": {
            "os": system,
            "arch": arch,
        },
        "cpu": {
            "cores": cpu_cores,
            "model": cpu_model,
            "load_pct": cpu_usage_pct,
        },
        "memory": {
            "total_gb": memory.get("total_gb"),
            "free_gb": memory.get("free_gb"),
            "used_pct": memory.get("util_pct"),
        },
        "gpu": gpu_info,
        "capabilities": {
            "cuda": bool(gpu_info.get("present")),
            "cpu_only_possible": True,  # decisione demandata alla policy
        },
    }

    logger.info(
        "[PREBOOT] system verify OK",
        extra={
            "status": "facts",
            "cpu_cores": cpu_cores,
            "cpu_model": cpu_model,
            "gpu_name": gpu_info.get("name"),
            "vram_free_gb": gpu_info.get("vram_free_gb"),
            "vram_total_gb": gpu_info.get("vram_total_gb"),
            "ram_free_gb": memory.get("free_gb"),
            "ram_total_gb": memory.get("total_gb"),
        },
    )
    logger.info("[PREBOOT] runtime state: READY")
    logger.info("[PREBOOT] runtime mode: local")
    return result
