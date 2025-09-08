"""kALDo runner for BTE thermal conductivity calculations"""
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import subprocess

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

from common.schema import Asset, Edge, Run
from common.ids import asset_id, generate_id
from common.io import write_uri
from common.config import get_config

class KALDoRunner:
    """Runner for kALDo BTE thermal conductivity calculations"""
    
    def __init__(self):
        self.runner_version = "1.0.0"
        
        # Check dependencies
        if not NUMPY_AVAILABLE:
            raise ImportError(
                "NumPy is required for kALDo calculations. Please install: pip install numpy"
            )
        
        self.config = get_config()
        self.kaldo_config = self.config.get_kaldo_config()
        self.execution_mode = self.config.get_execution_mode("kaldo")
        
        # Additional dependency checks based on execution mode
        if self.execution_mode == "local":
            # Check if kALDo is available locally
            try:
                import kaldo  # This would be the actual kALDo import
                self.kaldo_available = True
            except ImportError:
                raise ImportError(
                    "kALDo not available for local execution. "
                    "Please install kALDo or use Docker execution mode."
                )
    
    def run(self, run_obj: Run, assets: List[Asset], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute kALDo BTE calculation"""
        
        # Extract inputs
        system_asset = None
        method_asset = None
        params_asset = None
        force_constants_asset = None
        
        for asset in assets:
            if asset.type == "System":
                system_asset = asset
            elif asset.type == "Method":
                method_asset = asset
            elif asset.type == "Params":
                params_asset = asset
            elif asset.type == "Artifact" and "force_constants" in asset.payload.get("description", ""):
                force_constants_asset = asset
        
        if not system_asset:
            raise ValueError("System asset required")
        
        # Get BTE parameters
        T_K = params.get("T_K", [300, 400, 500, 600, 700, 800])
        mesh = params.get("mesh", [20, 20, 20])
        broadening_shape = params.get("broadening_shape", "gauss")
        broadening_width = params.get("broadening_width", 1.0)  # meV
        include_isotopes = params.get("include_isotopes", True)
        
        # Update run status
        run_obj.status = "running"
        run_obj.started_at = datetime.utcnow().isoformat()
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                
                # Generate kALDo input script
                kaldo_script = self._generate_kaldo_script(
                    system_asset.payload,
                    T_K,
                    mesh,
                    broadening_shape,
                    broadening_width,
                    include_isotopes,
                    tmppath
                )
                
                script_path = tmppath / "kaldo_bte.py"
                with open(script_path, "w") as f:
                    f.write(kaldo_script)
                
                # If force constants not provided, generate them (simulation)
                if not force_constants_asset:
                    fc_results = self._generate_force_constants(system_asset.payload, tmppath)
                    
                    # Store force constants as artifact
                    fc_uri = f"mcg://force_constants/{run_obj.id}_fc.hdf5"
                    fc_hash = write_uri(fc_uri, fc_results)
                    
                    force_constants_asset = Asset(
                        type="Artifact",
                        id=generate_id("A"),
                        payload={
                            "uri": fc_uri,
                            "kind": "output",
                            "media_type": "application/x-hdf5",
                            "description": f"Force constants for {system_asset.id}"
                        },
                        uri=fc_uri,
                        hash=fc_hash
                    )
                
                # Run kALDo BTE calculation
                kappa_results, phonon_data = self._execute_kaldo(
                    script_path, T_K, tmppath
                )
                
                # Store computation log
                log_uri = f"mcg://logs/kaldo_{run_obj.id}.txt"
                log_content = self._generate_log_content(T_K, mesh, kappa_results)
                log_hash = write_uri(log_uri, log_content)
                
                log_artifact = Asset(
                    type="Artifact",
                    id=generate_id("A"),
                    payload={
                        "uri": log_uri,
                        "kind": "log",
                        "media_type": "text/plain"
                    },
                    uri=log_uri,
                    hash=log_hash
                )
                
                # Create Results asset with phonon details
                results_payload = {
                    "T_K": T_K,
                    "kappa_W_per_mK": kappa_results["kappa_total"],
                    "kappa_xx_W_per_mK": kappa_results["kappa_xx"],
                    "kappa_yy_W_per_mK": kappa_results["kappa_yy"], 
                    "kappa_zz_W_per_mK": kappa_results["kappa_zz"],
                    "method": "BTE",
                    "solver": "kALDo",
                    "mesh": mesh,
                    "phonon_freq_THz": phonon_data["frequencies"],
                    "phonon_velocities_km_per_s": phonon_data["velocities"],
                    "lifetimes_ps": phonon_data["lifetimes"],
                    "mode_kappa_contributions": phonon_data["mode_contributions"],
                    "broadening_shape": broadening_shape,
                    "broadening_width_meV": broadening_width
                }
                
                results_asset = Asset(
                    type="Results",
                    id=asset_id("Results", results_payload),
                    payload=results_payload,
                    units={
                        "T_K": "K",
                        "kappa_W_per_mK": "W/(m*K)",
                        "kappa_xx_W_per_mK": "W/(m*K)",
                        "kappa_yy_W_per_mK": "W/(m*K)", 
                        "kappa_zz_W_per_mK": "W/(m*K)",
                        "phonon_freq_THz": "THz",
                        "phonon_velocities_km_per_s": "km/s",
                        "lifetimes_ps": "ps",
                        "broadening_width_meV": "meV"
                    }
                )
                
                # Create lineage edges
                edges = [
                    Edge(
                        from_id=system_asset.id,
                        to_id=run_obj.id,
                        rel="USES",
                        t=datetime.utcnow().isoformat()
                    ),
                    Edge(
                        from_id=run_obj.id,
                        to_id=results_asset.id,
                        rel="PRODUCES",
                        t=datetime.utcnow().isoformat()
                    ),
                    Edge(
                        from_id=run_obj.id,
                        to_id=log_artifact.id,
                        rel="LOGS",
                        t=datetime.utcnow().isoformat()
                    )
                ]
                
                # Add edges for force constants
                if force_constants_asset:
                    edges.append(Edge(
                        from_id=force_constants_asset.id,
                        to_id=run_obj.id,
                        rel="USES",
                        t=datetime.utcnow().isoformat()
                    ))
                    edges.append(Edge(
                        from_id=run_obj.id,
                        to_id=force_constants_asset.id,
                        rel="PRODUCES",
                        t=datetime.utcnow().isoformat()
                    ))
                
                # Add configuration edges
                if method_asset:
                    edges.append(Edge(
                        from_id=method_asset.id,
                        to_id=run_obj.id,
                        rel="CONFIGURES",
                        t=datetime.utcnow().isoformat()
                    ))
                
                if params_asset:
                    edges.append(Edge(
                        from_id=params_asset.id,
                        to_id=run_obj.id,
                        rel="CONFIGURES",
                        t=datetime.utcnow().isoformat()
                    ))
                
                # Update run status
                run_obj.status = "done"
                run_obj.ended_at = datetime.utcnow().isoformat()
                
                # Return assets including force constants if generated
                result_assets = [results_asset, log_artifact]
                if not any(a.id == force_constants_asset.id for a in assets):
                    result_assets.append(force_constants_asset)
                
                return {
                    "assets": result_assets,
                    "edges": edges,
                    "run": run_obj
                }
                
        except Exception as e:
            run_obj.status = "error"
            run_obj.ended_at = datetime.utcnow().isoformat()
            raise e
    
    def _generate_kaldo_script(self, system, T_K, mesh, broadening_shape, 
                               broadening_width, include_isotopes, tmppath):
        """Generate kALDo input script"""
        
        script = f"""#!/usr/bin/env python3
# kALDo BTE thermal conductivity calculation script
# Generated by MCG kALDo runner

import numpy as np
from kaldo import Phonons
from ase import Atoms

# Create structure from system data
atoms = Atoms(
    symbols=[atom['el'] for atom in {system['atoms']}],
    positions={[atom['pos'] for atom in system['atoms']]},
    cell={system['lattice']},
    pbc={system['pbc']}
)

print("Setting up kALDo calculation...")
print(f"Structure: {{atoms.get_chemical_formula()}}")
print(f"Mesh: {mesh}")
print(f"Temperatures: {T_K} K")

# Configure phonons object
phonons = Phonons(
    atoms=atoms,
    supercell={mesh},
    primitive_matrix=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    is_classic=False,  # Use quantum statistics
    temperature={T_K[0] if len(T_K) == 1 else T_K},
    store_folder="{tmppath}",
    third_order=None,  # Would load force constants here
    broadening_shape="{broadening_shape}",
    broadening_width={broadening_width}
)

# Read force constants (would be from external calculation)
print("Loading force constants...")
# phonons.read_from_folder()

# Calculate phonon properties
print("Calculating phonon properties...")
phonons.calculate_anharmonic_properties()

# Calculate thermal conductivity via BTE
print("Solving Boltzmann Transport Equation...")
thermal_conductivity = phonons.calculate_thermal_conductivity()

print(f"Thermal conductivity tensor:")
for i, T in enumerate({T_K}):
    kappa = thermal_conductivity[i] if len({T_K}) > 1 else thermal_conductivity
    print(f"  T = {{T}} K: κ_xx = {{kappa[0,0]:.2f}}, κ_yy = {{kappa[1,1]:.2f}}, κ_zz = {{kappa[2,2]:.2f}} W/(m·K)")

# Save results in expected JSON format
import json

results = {{
    "kappa_W_per_mK": [float(thermal_conductivity[i].mean()) for i in range(len({T_K}))],
    "kappa_xx_W_per_mK": [float(thermal_conductivity[i][0,0]) for i in range(len({T_K}))],
    "kappa_yy_W_per_mK": [float(thermal_conductivity[i][1,1]) for i in range(len({T_K}))],
    "kappa_zz_W_per_mK": [float(thermal_conductivity[i][2,2]) for i in range(len({T_K}))],
    "phonon_freq_THz": phonons.frequency[:10].tolist(),  # Sample first 10 modes
    "lifetimes_ps": phonons.bandwidth[:10].tolist(),
    "group_velocities": phonons.velocity[:10].tolist(),
    "T_K": {T_K}
}}

with open("{tmppath}/kaldo_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("kALDo calculation complete!")
"""
        
        return script
    
    def _generate_force_constants(self, system, tmppath):
        """Generate force constants for the system using DFT or ML potential"""
        # This is a placeholder - real implementation would:
        # 1. Set up DFT calculation (e.g., Quantum ESPRESSO, VASP)
        # 2. Calculate force constants using finite differences or DFPT
        # 3. Or use a machine learning potential (CHGNet, M3GNet, etc.)
        
        raise NotImplementedError(
            "Force constants generation not implemented. "
            "This requires DFT calculations or ML potentials. "
            "Please provide pre-computed force constants as an input asset."
        )
        
        return fc_data
    
    def _execute_kaldo(self, script_path, T_K, tmppath):
        """Execute kALDo based on configuration mode"""
        
        if self.execution_mode == "docker":
            # Docker execution
            docker_config = self.kaldo_config["execution"]["docker"]
            
            cmd = [
                "docker", "run",
                "-v", f"{tmppath}:/work",
                "--rm",
                docker_config["image"],
                docker_config["command"],
                "/work/kaldo_script.py"
            ]
            
            print("=== kALDo Docker Execution ===")
            print(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Forward stdout/stderr to console
            if result.stdout:
                print("kALDo stdout:")
                print(result.stdout)
            if result.stderr:
                print("kALDo stderr:")
                print(result.stderr)
            
            if result.returncode != 0:
                raise RuntimeError(f"kALDo failed with return code {result.returncode}")
            
            # Parse output files
            return self._parse_kaldo_output(tmppath, T_K)
        
        elif self.execution_mode == "local":
            # Local execution
            local_config = self.kaldo_config["execution"]["local"]
            
            # Set environment variables
            env = os.environ.copy()
            for key, value in local_config.get("environment", {}).items():
                env[key] = str(value)
            
            # Build command
            python_exe = local_config.get("python_executable", "python3")
            cmd = f"{python_exe} {script_path}"
            
            print("=== kALDo Local Execution ===")
            print(f"Command: {cmd}")
            print(f"Working directory: {tmppath}")
            
            result = subprocess.run(
                cmd, shell=True, cwd=tmppath,
                capture_output=True, text=True, env=env
            )
            
            # Forward stdout/stderr to console
            if result.stdout:
                print("kALDo stdout:")
                print(result.stdout)
            if result.stderr:
                print("kALDo stderr:")
                print(result.stderr)
            
            if result.returncode != 0:
                raise RuntimeError(f"kALDo failed with return code {result.returncode}")
            
            # Parse output files
            return self._parse_kaldo_output(tmppath, T_K)
        
        else:
            raise ValueError(f"Unknown execution mode: {self.execution_mode}")
    
    def _parse_kaldo_output(self, tmppath, T_K):
        """Parse kALDo output files"""
        output_file = tmppath / "kaldo_results.json"
        
        if not output_file.exists():
            raise FileNotFoundError(f"kALDo output file {output_file} not found")
        
        with open(output_file) as f:
            results = json.load(f)
        
        # Extract thermal conductivity results
        kappa_results = {
            "kappa_total": results.get("kappa_W_per_mK", []),
            "kappa_xx": results.get("kappa_xx_W_per_mK", []),
            "kappa_yy": results.get("kappa_yy_W_per_mK", []),
            "kappa_zz": results.get("kappa_zz_W_per_mK", [])
        }
        
        # Extract phonon data
        phonon_data = {
            "frequencies": results.get("phonon_freq_THz", []),
            "velocities": results.get("group_velocities", []),
            "lifetimes": results.get("lifetimes_ps", []),
            "mode_contributions": results.get("mode_contributions", [])
        }
        
        return kappa_results, phonon_data
    
    def _generate_log_content(self, T_K, mesh, kappa_results):
        """Generate computation log"""
        log_lines = [
            "kALDo BTE Thermal Conductivity Calculation",
            "==========================================",
            "",
            f"Mesh: {mesh[0]}×{mesh[1]}×{mesh[2]}",
            f"Temperature range: {min(T_K)}-{max(T_K)} K",
            f"Method: Boltzmann Transport Equation",
            f"Solver: kALDo iterative",
            "",
            "Results:",
        ]
        
        for T, k in zip(T_K, kappa_results["kappa_total"]):
            log_lines.append(f"  T = {T:3d} K: κ = {k:6.2f} W/(m·K)")
        
        log_lines.extend([
            "",
            "Tensor components (last temperature):",
            f"  κ_xx = {kappa_results['kappa_xx'][-1]:.2f} W/(m·K)",
            f"  κ_yy = {kappa_results['kappa_yy'][-1]:.2f} W/(m·K)",
            f"  κ_zz = {kappa_results['kappa_zz'][-1]:.2f} W/(m·K)",
            "",
            "Calculation completed successfully."
        ])
        
        return "\n".join(log_lines)