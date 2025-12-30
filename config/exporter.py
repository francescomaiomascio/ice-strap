from typing import Dict, Any

def export_engine_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "storage": cfg.get("storage"),
        "vector": cfg.get("vector"),
        "embeddings": cfg.get("embeddings"),
        "llm": cfg.get("llm"),
        "codemodel": cfg.get("codemodel"),
        "logging": cfg.get("logging"),
        "performance": cfg.get("performance"),
        "features": cfg.get("features"),
    }

def export_protocols_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "network": cfg.get("network"),
        "security": cfg.get("network", {}).get("vpn", {}).get("security"),
    }

def export_ai_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return cfg.get("ai", {})
