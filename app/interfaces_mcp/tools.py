"""Planning and explanation tools for natural language interactions"""
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.common.schema import Asset, Edge
from app.common.ids import asset_id, generate_id

class InterfacesTools:
    """Tools for planning and explaining computational workflows"""
    
    def plan(self, nl_task: str, context_assets: Optional[List[Asset]] = None) -> Dict[str, Any]:
        """Parse natural language task and create execution plan"""
        
        # Parse the natural language task
        task_lower = nl_task.lower()
        
        # Initialize plan components
        runner_kind = None
        assets = []
        params = {}
        workflow = None
        missing = []
        
        # Detect Materials Project fetch
        mp_pattern = r'mp-?\d+|material.*project|pull.*(?:mp-?\d+)'
        if re.search(mp_pattern, task_lower):
            # Extract material ID
            mp_id_match = re.search(r'mp-?\d+', task_lower)
            if mp_id_match:
                material_id = mp_id_match.group().replace('-', '')
                params["material_id"] = material_id
                runner_kind = "MaterialsProject"
                workflow = "fetch_structure"
            else:
                missing.append("material_id")
        
        # Detect thermal conductivity calculation
        kappa_pattern = r'thermal conductivity|kappa|κ|\bk\b|heat transport'
        if re.search(kappa_pattern, task_lower):
            if not runner_kind:
                runner_kind = "LAMMPS"
            workflow = "kappa_calculation"
            
            # Look for temperature range
            temp_pattern = r'(\d+)\s*(?:-|to|–)\s*(\d+)\s*k'
            temp_match = re.search(temp_pattern, task_lower)
            if temp_match:
                T_start = int(temp_match.group(1))
                T_end = int(temp_match.group(2))
                # Generate temperature grid
                T_K = list(range(T_start, T_end + 1, 100))
                params["T_K"] = T_K
            else:
                # Check for explicit temperature list
                temps = re.findall(r'(\d+)\s*k(?:elvin)?', task_lower)
                if temps:
                    params["T_K"] = [int(t) for t in temps]
                else:
                    missing.append("temperature_grid")
            
            # Look for supercell
            supercell_pattern = r'(\d+)\s*x\s*(\d+)\s*x\s*(\d+)|supercell'
            supercell_match = re.search(supercell_pattern, task_lower)
            if supercell_match and supercell_match.group(1):
                params["supercell"] = [
                    int(supercell_match.group(1)),
                    int(supercell_match.group(2)),
                    int(supercell_match.group(3))
                ]
            else:
                missing.append("supercell")
            
            # Check for method specification
            if 'chgnet' in task_lower:
                method = Asset(
                    type="Method",
                    id=generate_id("M"),
                    payload={
                        "family": "MD",
                        "code": "LAMMPS",
                        "model": "CHGNet",
                        "device": "GPU" if "gpu" in task_lower or "a100" in task_lower else "CPU"
                    }
                )
                assets.append(method)
            elif 'green-kubo' in task_lower or 'gk' in task_lower:
                method = Asset(
                    type="Method",
                    id=generate_id("M"),
                    payload={
                        "family": "MD",
                        "code": "LAMMPS",
                        "model": "CHGNet",
                        "device": "GPU" if "gpu" in task_lower else "CPU"
                    }
                )
                assets.append(method)
                params["method"] = "Green-Kubo"
            
            # Set default MD parameters if not specified
            if "timestep_fs" not in params:
                params["timestep_fs"] = 1.0
            if "equil_ps" not in params:
                params["equil_ps"] = 100
            if "prod_ps" not in params:
                params["prod_ps"] = 500
            if "HFACF_window_ps" not in params:
                params["HFACF_window_ps"] = 200
        
        # Detect BTE/kALDo request
        if 'bte' in task_lower or 'kaldo' in task_lower or 'boltzmann' in task_lower:
            runner_kind = "kALDo"
            workflow = "bte_calculation"
            
            # Look for mesh parameters
            mesh_pattern = r'(\d+)\s*x\s*(\d+)\s*x\s*(\d+)\s*mesh|mesh\s*(\d+)'
            mesh_match = re.search(mesh_pattern, task_lower)
            if mesh_match:
                if mesh_match.group(1):  # Full mesh specification
                    params["mesh"] = [
                        int(mesh_match.group(1)),
                        int(mesh_match.group(2)),
                        int(mesh_match.group(3))
                    ]
                else:  # Single number mesh
                    n = int(mesh_match.group(4))
                    params["mesh"] = [n, n, n]
            else:
                params["mesh"] = [20, 20, 20]  # Default
            
            # BTE-specific parameters
            if "broadening" in task_lower:
                # Look for broadening width
                broad_match = re.search(r'(\d+\.?\d*)\s*mev', task_lower)
                if broad_match:
                    params["broadening_width"] = float(broad_match.group(1))
                else:
                    params["broadening_width"] = 1.0
            
            if "lorentz" in task_lower:
                params["broadening_shape"] = "lorentz"
            else:
                params["broadening_shape"] = "gauss"
            
            # Include isotope scattering by default for BTE
            params["include_isotopes"] = True
            
            # Create BTE method asset
            if not any(a.type == "Method" for a in assets):
                method = Asset(
                    type="Method",
                    id=generate_id("M"),
                    payload={
                        "family": "LD",  # Lattice Dynamics
                        "code": "kALDo",
                        "model": "BTE",
                        "version": "3.0+"
                    }
                )
                assets.append(method)
        
        # Handle silicon specifically
        if 'silicon' in task_lower or 'si' in task_lower:
            if not params.get("material_id"):
                params["material_id"] = "mp-149"  # Silicon material ID
        
        # Create workflow plan
        if workflow == "kappa_calculation" and "material_id" in params:
            # Two-step workflow: fetch then calculate
            workflow = "fetch_then_kappa"
        
        # Create params asset if we have params
        if params:
            params_asset = Asset(
                type="Params",
                id=asset_id("Params", params),
                payload=params
            )
            assets.append(params_asset)
        
        return {
            "runner_kind": runner_kind,
            "assets": assets,
            "params": params,
            "workflow": workflow,
            "missing": missing
        }
    
    def explain(self, results_assets: List[Asset], ledger_slice: List[Edge]) -> str:
        """Generate human-readable explanation of results"""
        
        explanation = []
        
        # Find results assets
        for asset in results_assets:
            if asset.type == "Results":
                payload = asset.payload
                
                # Check for thermal conductivity results
                if "kappa_W_per_mK" in payload and "T_K" in payload:
                    temps = payload["T_K"]
                    kappas = payload["kappa_W_per_mK"]
                    
                    explanation.append("## Thermal Conductivity Results\n")
                    method = payload.get('method', 'Unknown')
                    explanation.append(f"Method: {method}")
                    
                    if method == "BTE":
                        explanation.append(f"Solver: {payload.get('solver', 'kALDo')}")
                        explanation.append(f"Mesh: {payload.get('mesh', 'Not specified')}")
                        explanation.append(f"Broadening: {payload.get('broadening_shape', 'gauss')} "
                                         f"({payload.get('broadening_width_meV', 1.0)} meV)")
                    else:
                        explanation.append(f"Supercell: {payload.get('supercell', 'Not specified')}")
                    
                    explanation.append("\n### κ(T) values:")
                    
                    for T, k in zip(temps, kappas):
                        explanation.append(f"  - {T} K: {k:.2f} W/(m·K)")
                    
                    # Add tensor components if available (BTE)
                    if "kappa_xx_W_per_mK" in payload:
                        explanation.append("\n### Tensor Components (last T):")
                        explanation.append(f"  - κ_xx: {payload['kappa_xx_W_per_mK'][-1]:.2f} W/(m·K)")
                        explanation.append(f"  - κ_yy: {payload['kappa_yy_W_per_mK'][-1]:.2f} W/(m·K)")
                        explanation.append(f"  - κ_zz: {payload['kappa_zz_W_per_mK'][-1]:.2f} W/(m·K)")
                    
                    # Add trend analysis
                    if len(kappas) > 1:
                        trend = "decreasing" if kappas[-1] < kappas[0] else "increasing"
                        explanation.append(f"\nTrend: Thermal conductivity {trend} with temperature")
                        explanation.append(f"Range: {min(kappas):.2f} - {max(kappas):.2f} W/(m·K)")
                
                # Check for phonon information
                if "phonon_freq_THz" in payload:
                    explanation.append("\n### Phonon Summary")
                    freqs = payload["phonon_freq_THz"]
                    explanation.append(f"Frequency range: {min(freqs):.2f} - {max(freqs):.2f} THz")
                
                if "lifetimes_ps" in payload:
                    lifetimes = payload["lifetimes_ps"]
                    explanation.append(f"Lifetime range: {min(lifetimes):.2f} - {max(lifetimes):.2f} ps")
        
        # Add reproducibility information from ledger
        if ledger_slice:
            explanation.append("\n## Reproducibility")
            
            # Find run IDs
            runs = set()
            for edge in ledger_slice:
                if edge.rel in ["PRODUCES", "USES"] and edge.from_id.startswith("R"):
                    runs.add(edge.from_id)
            
            if runs:
                explanation.append(f"Run IDs: {', '.join(sorted(runs))}")
            
            # Find input assets
            inputs = []
            for edge in ledger_slice:
                if edge.rel == "USES":
                    inputs.append(edge.from_id)
            
            if inputs:
                explanation.append(f"Input assets: {', '.join(inputs)}")
            
            explanation.append("\nTo reproduce:")
            explanation.append("1. Retrieve input assets from Memory MCP")
            explanation.append("2. Execute same runner with identical parameters")
            explanation.append("3. Results should match within numerical tolerance")
        
        return "\n".join(explanation)