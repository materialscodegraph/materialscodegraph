"""In-memory storage for assets and edges"""
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

from app.common.schema import Asset, Edge

class MemoryStore:
    """In-memory store with optional persistence"""
    
    def __init__(self, persist_path: Optional[Path] = None):
        self.assets: Dict[str, Asset] = {}
        self.edges: List[Edge] = []  # Append-only ledger
        self.persist_path = persist_path
        
        if persist_path and persist_path.exists():
            self._load()
    
    def put_asset(self, asset: Asset) -> str:
        """Store an asset and return its ID"""
        self.assets[asset.id] = asset
        self._save()
        return asset.id
    
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Retrieve an asset by ID"""
        return self.assets.get(asset_id)
    
    def get_assets(self, ids: List[str]) -> List[Asset]:
        """Retrieve multiple assets by IDs"""
        return [self.assets[aid] for aid in ids if aid in self.assets]
    
    def append_edge(self, edge: Edge) -> None:
        """Append an edge to the ledger (immutable)"""
        self.edges.append(edge)
        self._save()
    
    def append_edges(self, edges: List[Edge]) -> int:
        """Append multiple edges and return count"""
        for edge in edges:
            self.edges.append(edge)
        self._save()
        return len(edges)
    
    def query_edges(self, from_id: Optional[str] = None, 
                    to_id: Optional[str] = None,
                    run_id: Optional[str] = None) -> List[Edge]:
        """Query edges with optional filters"""
        result = self.edges.copy()
        
        if from_id:
            result = [e for e in result if e.from_id == from_id]
        if to_id:
            result = [e for e in result if e.to_id == to_id]
        if run_id:
            # Filter edges related to a specific run
            result = [e for e in result 
                     if e.from_id == run_id or e.to_id == run_id]
        
        return result
    
    def _save(self):
        """Persist state to disk if path configured"""
        if not self.persist_path:
            return
        
        data = {
            "assets": {aid: a.to_dict() for aid, a in self.assets.items()},
            "edges": [e.to_dict() for e in self.edges]
        }
        
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load(self):
        """Load state from disk"""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        with open(self.persist_path, "r") as f:
            data = json.load(f)
        
        self.assets = {
            aid: Asset.from_dict(adict) 
            for aid, adict in data.get("assets", {}).items()
        }
        
        self.edges = [
            Edge.from_dict(edict) 
            for edict in data.get("edges", [])
        ]