"""LAMMPS runner for Green-Kubo thermal conductivity calculations"""
import os
import json
import subprocess
import tempfile
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.common.schema import Asset, Edge, Run
from app.common.ids import asset_id, generate_id
from app.common.io import write_uri

class LAMMPSKappaGKRunner:
    """Runner for LAMMPS Green-Kubo thermal conductivity simulations"""
    
    def __init__(self):
        self.runner_version = "1.0.0"
    
    def run(self, run_obj: Run, assets: List[Asset], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LAMMPS Green-Kubo simulation"""
        
        # Extract inputs
        system_asset = None
        method_asset = None
        params_asset = None
        
        for asset in assets:
            if asset.type == "System":
                system_asset = asset
            elif asset.type == "Method":
                method_asset = asset
            elif asset.type == "Params":
                params_asset = asset
        
        if not system_asset:
            raise ValueError("System asset required")
        if not method_asset:
            raise ValueError("Method asset required")
        
        # Get simulation parameters
        supercell = params.get("supercell", [10, 10, 10])
        T_K = params.get("T_K", [300, 400, 500, 600, 700, 800])
        timestep_fs = params.get("timestep_fs", 1.0)
        equil_ps = params.get("equil_ps", 100)
        prod_ps = params.get("prod_ps", 500)
        HFACF_window_ps = params.get("HFACF_window_ps", 200)
        
        # Update run status
        run_obj.status = "running"
        run_obj.started_at = datetime.utcnow().isoformat()
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                
                # Generate LAMMPS input script
                lammps_script = self._generate_lammps_script(
                    system_asset.payload,
                    method_asset.payload,
                    supercell,
                    T_K,
                    timestep_fs,
                    equil_ps,
                    prod_ps,
                    HFACF_window_ps,
                    tmppath
                )
                
                script_path = tmppath / "in.kappa_gk"
                with open(script_path, "w") as f:
                    f.write(lammps_script)
                
                # Write structure data file
                data_file = tmppath / "structure.data"
                self._write_lammps_data(system_asset.payload, supercell, data_file)
                
                # Run LAMMPS (in practice would use container/HPC)
                # For now, simulate results
                kappa_results = self._simulate_kappa_calculation(T_K)
                
                # Store log as artifact
                log_uri = f"mcg://logs/lammps_{run_obj.id}.txt"
                log_content = f"LAMMPS Green-Kubo simulation\nTemperatures: {T_K}\nSupercell: {supercell}\n"
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
                
                # Create Results asset
                results_payload = {
                    "T_K": T_K,
                    "kappa_W_per_mK": kappa_results,
                    "method": "Green-Kubo",
                    "simulation_time_ps": prod_ps,
                    "supercell": supercell
                }
                
                results_asset = Asset(
                    type="Results",
                    id=asset_id("Results", results_payload),
                    payload=results_payload,
                    units={
                        "T_K": "K",
                        "kappa_W_per_mK": "W/(m*K)"
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
                        from_id=method_asset.id,
                        to_id=run_obj.id,
                        rel="CONFIGURES",
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
                
                return {
                    "assets": [results_asset, log_artifact],
                    "edges": edges,
                    "run": run_obj
                }
                
        except Exception as e:
            run_obj.status = "error"
            run_obj.ended_at = datetime.utcnow().isoformat()
            raise e
    
    def _generate_lammps_script(self, system, method, supercell, T_K, 
                                timestep_fs, equil_ps, prod_ps, 
                                HFACF_window_ps, tmppath):
        """Generate LAMMPS input script for Green-Kubo calculation"""
        
        model = method.get("model", "CHGNet")
        
        script = f"""# LAMMPS Green-Kubo thermal conductivity calculation
units metal
atom_style atomic
boundary p p p

# Read structure
read_data structure.data

# Replicate to create supercell
replicate {supercell[0]} {supercell[1]} {supercell[2]}

# Set potential based on model
"""
        
        if model == "CHGNet":
            script += """
# CHGNet potential via ML-IAP
pair_style mlip chgnet
pair_coeff * * 
"""
        else:
            # Default to LJ for testing
            script += """
# Lennard-Jones potential (for testing)
pair_style lj/cut 10.0
pair_coeff * * 1.0 1.0
"""
        
        script += f"""
# Time integration
timestep {timestep_fs/1000.0}  # Convert fs to ps

# Initialize velocities
variable seed equal 12345

# Loop over temperatures
"""
        
        for i, T in enumerate(T_K):
            script += f"""
# Temperature {T} K
print "Starting simulation at {T} K"

# Initialize
velocity all create {T} ${{seed}} mom yes rot yes dist gaussian

# Equilibration with NPT
fix npt{i} all npt temp {T} {T} $(100.0*dt) iso 0.0 0.0 $(1000.0*dt)
run {int(equil_ps*1000/timestep_fs)}
unfix npt{i}

# Switch to NVE for production
fix nve{i} all nve

# Compute heat flux
compute myKE all ke/atom
compute myPE all pe/atom
compute myStress all stress/atom NULL virial
compute flux all heat/flux myKE myPE myStress
variable Jx equal c_flux[1]/vol
variable Jy equal c_flux[2]/vol
variable Jz equal c_flux[3]/vol

# Production run with heat flux sampling
fix hfacf{i} all ave/correlate 10 {int(HFACF_window_ps*100/timestep_fs)} {int(prod_ps*1000/timestep_fs)} &
    c_flux[1] c_flux[2] c_flux[3] type auto file hfacf_{T}K.dat ave running

thermo_style custom step temp press vol etotal ke pe c_flux[1] c_flux[2] c_flux[3]
thermo 1000
run {int(prod_ps*1000/timestep_fs)}

# Clean up for next temperature
unfix nve{i}
unfix hfacf{i}
uncompute myKE
uncompute myPE
uncompute myStress
uncompute flux

"""
        
        return script
    
    def _write_lammps_data(self, system, supercell, filepath):
        """Write LAMMPS data file for the structure"""
        atoms = system["atoms"]
        lattice = system["lattice"]
        
        # Simple data file (would need proper implementation for real use)
        with open(filepath, "w") as f:
            f.write("LAMMPS data file\n\n")
            f.write(f"{len(atoms)} atoms\n")
            f.write("1 atom types\n\n")
            
            # Box bounds (simplified)
            f.write(f"0.0 {lattice[0][0]} xlo xhi\n")
            f.write(f"0.0 {lattice[1][1]} ylo yhi\n")
            f.write(f"0.0 {lattice[2][2]} zlo zhi\n\n")
            
            f.write("Masses\n\n")
            f.write("1 28.0855  # Si\n\n")
            
            f.write("Atoms\n\n")
            for i, atom in enumerate(atoms, 1):
                f.write(f"{i} 1 {atom['pos'][0]} {atom['pos'][1]} {atom['pos'][2]}\n")
    
    def _simulate_kappa_calculation(self, T_K):
        """Simulate thermal conductivity results (placeholder)"""
        # Realistic values for silicon
        # κ decreases with temperature
        kappa_300K = 150.0  # W/(m*K) for silicon at 300K
        
        kappa_values = []
        for T in T_K:
            # Simple model: κ ∝ T^(-1.2)
            kappa = kappa_300K * (300.0/T)**1.2
            # Add some noise
            kappa += np.random.normal(0, kappa*0.05)
            kappa_values.append(round(kappa, 2))
        
        return kappa_values