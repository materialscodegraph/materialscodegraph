"""ID and hash helpers for MCG"""
import hashlib
import json
import uuid
from typing import Any, Dict

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    uid = str(uuid.uuid4())[:8]
    return f"{prefix}{uid}" if prefix else uid

def hash_dict(data: Dict[str, Any]) -> str:
    """Generate deterministic hash for a dictionary"""
    # Sort keys to ensure deterministic serialization
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]

def asset_id(asset_type: str, payload: Dict[str, Any]) -> str:
    """Generate deterministic ID for an asset based on type and payload"""
    prefix_map = {
        "System": "S",
        "Method": "M",
        "Params": "P",
        "Results": "R",
        "Artifact": "A"
    }
    prefix = prefix_map.get(asset_type, "X")
    hash_suffix = hash_dict(payload)[:6]
    return f"{prefix}{hash_suffix}"

def run_id() -> str:
    """Generate a unique run ID"""
    return f"R{uuid.uuid4().hex[:8]}"