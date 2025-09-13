"""MCG-lite schema validators and models"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import json

AssetType = Literal["System", "Method", "Params", "Results", "Artifact"]
RunStatus = Literal["queued", "running", "done", "error"]
EdgeRelation = Literal["USES", "PRODUCES", "DERIVES", "CONFIGURES", "LOGS"]

@dataclass
class Asset:
    """MCG-lite Asset"""
    type: AssetType
    id: str
    payload: Dict[str, Any]
    units: Optional[Dict[str, str]] = None
    uri: Optional[str] = None
    hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "type": self.type,
            "id": self.id,
            "payload": self.payload
        }
        if self.units:
            d["units"] = self.units
        if self.uri:
            d["uri"] = self.uri
        if self.hash:
            d["hash"] = self.hash
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Asset":
        return cls(**data)

@dataclass
class Run:
    """Run record for compute operations"""
    id: str
    kind: str
    status: RunStatus
    runner_version: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "kind": self.kind,
            "status": self.status
        }
        if self.runner_version:
            d["runner_version"] = self.runner_version
        if self.started_at:
            d["started_at"] = self.started_at
        if self.ended_at:
            d["ended_at"] = self.ended_at
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Run":
        return cls(**data)

@dataclass
class Edge:
    """Lineage edge in the provenance graph"""
    from_id: str  # Asset.id or Run.id (renamed from 'from' to avoid keyword conflict)
    to_id: str    # Asset.id or Run.id (renamed from 'to' to avoid keyword conflict)
    rel: EdgeRelation
    t: str  # ISO8601 timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "rel": self.rel,
            "t": self.t
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        return cls(
            from_id=data["from"],
            to_id=data["to"],
            rel=data["rel"],
            t=data["t"]
        )

def validate_system(payload: Dict[str, Any]) -> bool:
    """Validate System payload schema"""
    required = {"atoms", "lattice", "pbc"}
    if not required.issubset(payload.keys()):
        return False
    
    # Check atoms structure
    if not isinstance(payload["atoms"], list):
        return False
    for atom in payload["atoms"]:
        if not isinstance(atom, dict) or "el" not in atom or "pos" not in atom:
            return False
        if not isinstance(atom["pos"], list) or len(atom["pos"]) != 3:
            return False
    
    # Check lattice
    if not isinstance(payload["lattice"], list) or len(payload["lattice"]) != 3:
        return False
    for vec in payload["lattice"]:
        if not isinstance(vec, list) or len(vec) != 3:
            return False
    
    # Check pbc
    if not isinstance(payload["pbc"], list) or len(payload["pbc"]) != 3:
        return False
    for b in payload["pbc"]:
        if not isinstance(b, bool):
            return False
    
    return True

def validate_method(payload: Dict[str, Any]) -> bool:
    """Validate Method payload schema"""
    if "family" not in payload or "code" not in payload:
        return False
    
    valid_families = {"DFT", "MD", "LD", "ML", "QM"}
    valid_devices = {"CPU", "GPU", "TPU"}

    if payload["family"] not in valid_families:
        return False
    if "device" in payload and payload["device"] not in valid_devices:
        return False
    
    return True

def validate_asset(asset: Asset) -> bool:
    """Validate an asset based on its type"""
    if asset.type == "System":
        return validate_system(asset.payload)
    elif asset.type == "Method":
        return validate_method(asset.payload)
    # Params, Results, and Artifacts have free-form payloads
    return True