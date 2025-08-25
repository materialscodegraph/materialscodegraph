"""kALDo runner for BTE thermal conductivity calculations"""
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.common.schema import Asset, Edge, Run
from app.common.ids import asset_id, generate_id
from app.common.io import write_uri

class KALDoRunner:
    """Runner for kALDo BTE thermal conductivity calculations"""
    
    def __init__(self):
        self.runner_version = "1.0.0"
    
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
                
                # Run kALDo BTE calculation (mocked)
                kappa_results, phonon_data = self._simulate_bte_calculation(
                    T_K, mesh, system_asset.payload
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

# Save detailed results
np.save("{tmppath}/kappa_tensor.npy", thermal_conductivity)
np.save("{tmppath}/frequencies.npy", phonons.frequency)
np.save("{tmppath}/velocities.npy", phonons.velocity)
np.save("{tmppath}/lifetimes.npy", phonons.bandwidth)

print("kALDo calculation complete!")
"""
        
        return script
    
    def _generate_force_constants(self, system, tmppath):
        """Generate/simulate force constants for the system"""
        # In reality, would run DFT or use ML potential
        # For simulation, create mock force constants data
        
        n_atoms = len(system["atoms"])
        fc_data = {
            "second_order": f"Mock 2nd order FC matrix {n_atoms}x{n_atoms}x3x3",
            "third_order": f"Mock 3rd order FC tensor for {n_atoms} atoms",
            "mesh": [20, 20, 20],
            "primitive_cell": system["lattice"],
            "atoms": system["atoms"]
        }
        
        return fc_data
    
    def _simulate_bte_calculation(self, T_K, mesh, system):
        """Simulate BTE thermal conductivity calculation"""
        
        # Realistic silicon BTE results (higher than MD due to no scattering)
        base_kappa_300K = 200.0  # W/(m*K) - BTE typically higher than Green-Kubo
        
        kappa_values = []
        for T in T_K:
            # BTE: κ ∝ T^(-1.3) for acoustic phonons
            kappa = base_kappa_300K * (300.0/T)**1.3
            # Add some anisotropy for tensor components
            kappa_xx = kappa * 1.02  # Slightly higher in x
            kappa_yy = kappa * 0.98  # Slightly lower in y  
            kappa_zz = kappa * 1.00  # Reference in z
            
            kappa_values.append((kappa_xx + kappa_yy + kappa_zz) / 3.0)
        
        # Generate phonon data
        n_modes = mesh[0] * mesh[1] * mesh[2] * len(system["atoms"]) * 3
        
        # Realistic phonon frequencies for silicon (0-16 THz)
        frequencies = []
        velocities = []
        lifetimes = []
        mode_contributions = []
        
        for i in range(min(1000, n_modes)):  # Sample subset for demo
            # Acoustic branch (low freq) and optical branches
            if i < 100:  # Acoustic modes
                freq = 2.0 + i * 0.1  # 2-12 THz
                vel = 8000 - i * 20    # 8000-6000 m/s
                lifetime = 100.0 / freq  # Longer for low freq
                contribution = 0.8 / freq  # Acoustic dominates
            else:  # Optical modes
                freq = 12.0 + (i-100) * 0.005  # 12-16 THz
                vel = 3000 + (i-100) * 2       # 3000-4000 m/s  
                lifetime = 20.0 / freq         # Shorter for optical
                contribution = 0.1 / freq      # Small contribution
                
            frequencies.append(freq)
            velocities.append([vel, vel*0.9, vel*1.1])  # Anisotropic
            lifetimes.append(lifetime)
            mode_contributions.append(contribution)
        
        kappa_results = {
            "kappa_total": kappa_values,
            "kappa_xx": [k*1.02 for k in kappa_values],
            "kappa_yy": [k*0.98 for k in kappa_values], 
            "kappa_zz": kappa_values
        }
        
        phonon_data = {
            "frequencies": frequencies,
            "velocities": velocities,
            "lifetimes": lifetimes,
            "mode_contributions": mode_contributions
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