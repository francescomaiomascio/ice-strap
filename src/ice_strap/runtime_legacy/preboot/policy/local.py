from typing import Any, Dict, List
from ice_core.logging.router import get_logger

MIN_RAM_SAFE_GB = 6
MIN_RAM_CPU_ONLY_GB = 12
MIN_CPU_CORES_CPU_ONLY = 8
MIN_VRAM_GB = 6

logger = get_logger("preboot", "policy", "ice.preboot.policy.local")


def evaluate_local_policy(facts: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("LOCAL_FACTS_RAW", extra={"facts": facts})
    reasons: List[str] = []
    warnings: List[str] = []

    memory = facts.get("memory") or {}
    ram_free = memory.get("free_gb") or 0

    cpu = facts.get("cpu") or {}
    cpu_cores = cpu.get("cores") or 0

    gpu = facts.get("gpu") or {}
    has_cuda = gpu.get("present") is True
    vram_free_gb = gpu.get("vram_free_gb") or 0

    platform_os = (facts.get("platform") or {}).get("os")

    # 1️⃣ Safety hard-stop (vale per TUTTI)
    if ram_free < MIN_RAM_SAFE_GB:
        return {
            "status": "BLOCKED",
            "execution": None,
            "reasons": ["Insufficient free system RAM"],
            "warnings": [],
        }

    # 2️⃣ GPU path (preferred, APPROVED)
    if has_cuda and vram_free_gb >= MIN_VRAM_GB:
        return {
            "status": "APPROVED",
            "execution": {
                "preferred": "gpu",
                "fallback": "cpu",
            },
            "reasons": [],
            "warnings": [],
        }

    # 2b) GPU present but VRAM insufficient
    if has_cuda:
        warnings.append(
            "GPU detected but insufficient free VRAM "
            f"({vram_free_gb} GB available, {MIN_VRAM_GB} GB required)."
        )

    # 2c) macOS: trusted CPU-only platform (soft metrics)
    if platform_os == "darwin":
        warnings.append(
            "macOS detected: memory and GPU metrics are approximate."
        )
        warnings.append(
            "CPU-only execution enabled. Performance may be limited."
        )
        return {
            "status": "LIMITED",
            "execution": {
                "preferred": "cpu",
                "fallback": None,
            },
            "reasons": [],
            "warnings": warnings,
        }

    # 3️⃣ CPU-only viable (LIMITED ma ammesso)
    if cpu_cores >= MIN_CPU_CORES_CPU_ONLY and ram_free >= MIN_RAM_CPU_ONLY_GB:
        warnings.append(
            "CPU-only execution enabled. Performance will be limited."
        )
        if platform_os == "darwin":
            warnings.append(
                "Apple Silicon detected: CPU-only execution may be unstable under heavy load."
            )

        return {
            "status": "LIMITED",
            "execution": {
                "preferred": "cpu",
                "fallback": None,
            },
            "reasons": [],
            "warnings": warnings,
        }

    # 4️⃣ Tutto il resto → BLOCKED
    reasons.append("System does not meet minimum requirements for safe execution.")
    return {
        "status": "BLOCKED",
        "execution": None,
        "reasons": reasons,
        "warnings": [],
    }
