"""Materials Project runner for fetching structures"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from mp_api.client import MPRester
    MP_API_AVAILABLE = True
except ImportError:
    MPRester = None
    MP_API_AVAILABLE = False

from common.schema import Asset, Edge, Run
from common.ids import asset_id, generate_id
from common.io import write_uri

class MaterialsProjectRunner:
    """Runner for fetching structures from Materials Project"""
    
    def __init__(self):
        self.runner_version = "1.0.0"
        
        # Check if MP API is available
        if not MP_API_AVAILABLE:
            raise ImportError(
                "Materials Project API not available. Please install: pip install mp-api"
            )
        
        # Get API key from environment
        self.api_key = os.environ.get("MP_API_KEY")
        if not self.api_key:
            raise ValueError(
                "MP_API_KEY environment variable required. "
                "Get your API key from https://materialsproject.org/api"
            )
    
    def run(self, run_obj: Run, assets: List[Asset], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Materials Project fetch"""
        material_id = params.get("material_id")
        if not material_id:
            raise ValueError("material_id required in params")
        
        # Update run status
        run_obj.status = "running"
        run_obj.started_at = datetime.utcnow().isoformat()
        
        try:
            print("=== Materials Project API Request ===")
            print(f"Fetching material: {material_id}")
            
            # Fetch from Materials Project
            with MPRester(self.api_key) as mpr:
                print("Connected to Materials Project API")
                
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
                
                print(f"Successfully fetched: {doc.formula_pretty}")
                print(f"Space group: {structure.get_space_group_info()}")
                print(f"Lattice: {structure.lattice}")
                print(f"Number of atoms: {len(structure)}")
                print(f"Band gap: {doc.band_gap} eV")
                print(f"Energy per atom: {doc.energy_per_atom} eV/atom")
            
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
            for asset_data in assets:
                # Ensure we have Asset objects, not dictionaries
                if isinstance(asset_data, dict):
                    asset = Asset.from_dict(asset_data)
                else:
                    asset = asset_data
                    
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
                "run": run_obj.to_dict(),
                "assets": [system_asset.to_dict(), artifact_asset.to_dict()],
                "edges": [e.to_dict() for e in edges]
            }
            
        except Exception as e:
            run_obj.status = "error"
            run_obj.ended_at = datetime.utcnow().isoformat()
            run_obj.error_message = str(e)
            
            print(f"Materials Project API Error: {e}")
            raise