"""IO handlers for MCG URIs"""
import os
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

def parse_uri(uri: str) -> Dict[str, str]:
    """Parse MCG URI into components"""
    parsed = urlparse(uri)
    
    if parsed.scheme == "mcg":
        # mcg://bucket/key format
        return {
            "scheme": "mcg",
            "bucket": parsed.netloc,
            "key": parsed.path.lstrip("/")
        }
    elif parsed.scheme == "file":
        # file:///absolute/path format
        return {
            "scheme": "file",
            "path": parsed.path
        }
    else:
        raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")

def read_uri(uri: str) -> Any:
    """Read content from URI"""
    components = parse_uri(uri)
    
    if components["scheme"] == "file":
        path = components["path"]
        if path.endswith(".json"):
            with open(path, "r") as f:
                return json.load(f)
        else:
            with open(path, "r") as f:
                return f.read()
    elif components["scheme"] == "mcg":
        # For MCG scheme, use local file storage under .mcg directory
        mcg_dir = Path.home() / ".mcg" / components["bucket"]
        file_path = mcg_dir / components["key"]
        
        if not file_path.exists():
            raise FileNotFoundError(f"MCG resource not found: {uri}")
        
        if file_path.suffix == ".json":
            with open(file_path, "r") as f:
                return json.load(f)
        else:
            with open(file_path, "r") as f:
                return f.read()
    else:
        raise ValueError(f"Unsupported URI scheme: {components['scheme']}")

def write_uri(uri: str, content: Any) -> str:
    """Write content to URI and return hash"""
    components = parse_uri(uri)
    
    # Calculate hash
    if isinstance(content, dict):
        content_str = json.dumps(content, sort_keys=True)
    else:
        content_str = str(content)
    
    content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
    
    if components["scheme"] == "file":
        path = components["path"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        if path.endswith(".json"):
            with open(path, "w") as f:
                json.dump(content, f, indent=2)
        else:
            with open(path, "w") as f:
                f.write(content_str)
    elif components["scheme"] == "mcg":
        # For MCG scheme, use local file storage under .mcg directory
        mcg_dir = Path.home() / ".mcg" / components["bucket"]
        mcg_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = mcg_dir / components["key"]
        
        if file_path.suffix == ".json":
            with open(file_path, "w") as f:
                json.dump(content, f, indent=2)
        else:
            with open(file_path, "w") as f:
                f.write(content_str)
    else:
        raise ValueError(f"Unsupported URI scheme: {components['scheme']}")
    
    return content_hash

def ensure_mcg_storage() -> Path:
    """Ensure MCG storage directory exists and return path"""
    mcg_dir = Path.home() / ".mcg"
    mcg_dir.mkdir(exist_ok=True)
    return mcg_dir