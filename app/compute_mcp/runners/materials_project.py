"""Materials Project runner for fetching structures"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from mp_api.client import MPRester

from app.common.schema import Asset, Edge, Run
from app.common.ids import asset_id, generate_id
from app.common.io import write_uri

class MaterialsProjectRunner:
    """Runner for fetching structures from Materials Project"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("MP_API_KEY")
        if not self.api_key:
            raise ValueError("MP_API_KEY environment variable required")
        self.runner_version = "1.0.0"
    
    def run(self, run_obj: Run, assets: List[Asset], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Materials Project fetch"""
        material_id = params.get("material_id")
        if not material_id:
            raise ValueError("material_id required in params")
        
        # Update run status
        run_obj.status = "running"
        run_obj.started_at = datetime.utcnow().isoformat()
        
        try:
            # Fetch from Materials Project
            with MPRester(self.api_key) as mpr:
                # Get structure and basic properties
                docs = mpr.materials.summary.search(
                    material_ids=[material_id],
                    fields=["structure", "formula_pretty", "band_gap", 
                           "energy_per_atom", "formation_energy_per_atom"]
                )
                
                if not docs:
                    raise ValueError(f"Material {material_id} not found")
                
                doc = docs[0]
                structure = doc.structure
            
            # Convert to MCG System format
            atoms = []
            for site in structure:
                atoms.append({
                    "el": site.specie.symbol,
                    "pos": site.coords.tolist()
                })
            
            system_payload = {
                "atoms": atoms,
                "lattice": structure.lattice.matrix.tolist(),
                "pbc": [True, True, True]  # Materials Project structures are periodic
            }
            
            # Create System asset
            system_asset = Asset(
                type="System",
                id=asset_id("System", system_payload),
                payload=system_payload,
                units={"length": "angstrom"}
            )
            
            # Store raw MP response as Artifact
            artifact_uri = f"mcg://artifacts/{material_id}_{run_obj.id}.json"
            artifact_hash = write_uri(artifact_uri, {
                "material_id": material_id,
                "formula": doc.formula_pretty,
                "band_gap": doc.band_gap,
                "energy_per_atom": doc.energy_per_atom,
                "formation_energy_per_atom": doc.formation_energy_per_atom,
                "structure": structure.as_dict()
            })
            
            artifact_asset = Asset(
                type="Artifact",
                id=generate_id("A"),
                payload={
                    "uri": artifact_uri,
                    "kind": "output",
                    "media_type": "application/json",
                    "description": f"Raw Materials Project data for {material_id}"
                },
                uri=artifact_uri,
                hash=artifact_hash
            )
            
            # Create lineage edges
            edges = [
                Edge(
                    from_id=run_obj.id,
                    to_id=system_asset.id,
                    rel="PRODUCES",
                    t=datetime.utcnow().isoformat()
                ),
                Edge(
                    from_id=run_obj.id,
                    to_id=artifact_asset.id,
                    rel="LOGS",
                    t=datetime.utcnow().isoformat()
                )
            ]
            
            # Add edge from params if params was an asset
            for asset in assets:
                if asset.type == "Params":
                    edges.append(Edge(
                        from_id=asset.id,
                        to_id=run_obj.id,
                        rel="CONFIGURES",
                        t=datetime.utcnow().isoformat()
                    ))
            
            # Update run status
            run_obj.status = "done"
            run_obj.ended_at = datetime.utcnow().isoformat()
            
            return {
                "assets": [system_asset, artifact_asset],
                "edges": edges,
                "run": run_obj
            }
            
        except Exception as e:
            run_obj.status = "error"
            run_obj.ended_at = datetime.utcnow().isoformat()
            raise e