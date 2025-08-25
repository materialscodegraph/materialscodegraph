#!/usr/bin/env python3
"""kALDo BTE example workflow for silicon thermal conductivity"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from datetime import datetime
from app.common.schema import Asset, Edge, Run
from app.common.ids import asset_id, run_id, generate_id
from app.interfaces_mcp.tools import InterfacesTools
from app.compute_mcp.runners.kaldo_bte import KALDoRunner
from app.memory_mcp.store import MemoryStore

def main():
    """Execute the kALDo BTE thermal conductivity workflow"""
    
    print("=" * 60)
    print("MaterialsCodeGraph - kALDo BTE Workflow")
    print("=" * 60)
    
    # Initialize components
    interfaces = InterfacesTools()
    memory = MemoryStore()
    
    # Step 1: Plan BTE task
    print("\n1. PLANNING BTE CALCULATION")
    print("-" * 40)
    
    task = "Calculate thermal conductivity using kALDo BTE for mp-149 silicon at 300-800K with 25x25x25 mesh"
    print(f"Task: {task}")
    
    plan = interfaces.plan(task)
    print(f"\nPlan created:")
    print(f"  Runner: {plan['runner_kind']}")
    print(f"  Workflow: {plan['workflow']}")
    print(f"  Mesh: {plan['params']['mesh']}")
    print(f"  Method: BTE (Boltzmann Transport Equation)")
    
    # Step 2: Prepare silicon structure
    print("\n2. PREPARING SILICON STRUCTURE")
    print("-" * 40)
    
    # Create silicon primitive cell
    silicon_system = Asset(
        type="System",
        id=generate_id("S"),
        payload={
            "atoms": [
                {"el": "Si", "pos": [0.0, 0.0, 0.0]},
                {"el": "Si", "pos": [1.3575, 1.3575, 1.3575]}  # Primitive cell
            ],
            "lattice": [
                [2.715, 2.715, 0.0],    # Primitive lattice vectors
                [2.715, 0.0, 2.715],
                [0.0, 2.715, 2.715]
            ],
            "pbc": [True, True, True]
        },
        units={"length": "angstrom"}
    )
    
    system_id = memory.put_asset(silicon_system)
    print(f"Silicon primitive cell created:")
    print(f"  2 atoms, diamond structure")
    print(f"  Lattice constant: 5.43 Å")
    print(f"  System asset ID: {system_id}")
    
    # Step 3: Create BTE method configuration
    print("\n3. CONFIGURING BTE METHOD")
    print("-" * 40)
    
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
    method_id = memory.put_asset(method)
    
    params = Asset(
        type="Params",
        id=generate_id("P"),
        payload={
            "T_K": [300, 400, 500, 600, 700, 800],
            "mesh": [25, 25, 25],
            "broadening_shape": "gauss",
            "broadening_width": 1.0,  # meV
            "include_isotopes": True
        }
    )
    params_id = memory.put_asset(params)
    
    print(f"BTE configuration:")
    print(f"  Mesh: 25×25×25 k-points")
    print(f"  Broadening: Gaussian, 1.0 meV")
    print(f"  Isotope scattering: Included")
    print(f"  Temperature range: 300-800 K")
    
    # Step 4: Run kALDo BTE calculation
    print("\n4. RUNNING kALDo BTE CALCULATION")
    print("-" * 40)
    
    run = Run(
        id=run_id(),
        kind="kALDo",
        status="queued"
    )
    
    runner = KALDoRunner()
    
    print(f"Run ID: {run.id}")
    print("Status: Computing force constants...")
    print("Status: Building dynamical matrix...")
    print("Status: Solving Boltzmann Transport Equation...")
    
    # Execute BTE calculation
    results = runner.run(
        run,
        [silicon_system, method, params],
        params.payload
    )
    
    print("Status: Complete")
    
    # Store results
    for asset in results["assets"]:
        memory.put_asset(asset)
    
    for edge in results["edges"]:
        memory.append_edge(edge)
    
    # Step 5: Display BTE results
    print("\n5. BTE RESULTS")
    print("-" * 40)
    
    # Find results asset
    results_asset = None
    for asset in results["assets"]:
        if asset.type == "Results":
            results_asset = asset
            break
    
    if results_asset:
        payload = results_asset.payload
        print("\nThermal Conductivity Tensor κ(T):")
        print("Temperature [K]  |  κ_avg [W/(m·K)]  |  κ_xx    κ_yy    κ_zz")
        print("-" * 65)
        
        for i, T in enumerate(payload["T_K"]):
            k_avg = payload["kappa_W_per_mK"][i]
            k_xx = payload["kappa_xx_W_per_mK"][i]
            k_yy = payload["kappa_yy_W_per_mK"][i]
            k_zz = payload["kappa_zz_W_per_mK"][i]
            print(f"     {T:3d}        |     {k_avg:6.2f}      | {k_xx:6.2f} {k_yy:6.2f} {k_zz:6.2f}")
        
        print(f"\nMethod: {payload['method']} via {payload['solver']}")
        print(f"Mesh: {payload['mesh']}")
        
        # Phonon analysis
        print(f"\n### Phonon Analysis")
        print(f"Frequency range: {min(payload['phonon_freq_THz']):.1f} - {max(payload['phonon_freq_THz']):.1f} THz")
        print(f"Lifetime range: {min(payload['lifetimes_ps']):.1f} - {max(payload['lifetimes_ps']):.1f} ps")
        print(f"Dominant contribution from acoustic modes (~2-8 THz)")
    
    # Step 6: Generate detailed explanation
    print("\n6. DETAILED EXPLANATION")
    print("-" * 40)
    
    # Get lineage for this run
    ledger = memory.query_edges(run_id=run.id)
    
    explanation = interfaces.explain(
        results["assets"],
        ledger
    )
    
    print(explanation)
    
    # Step 7: Compare with experimental data
    print("\n7. COMPARISON WITH EXPERIMENT")
    print("-" * 40)
    
    if results_asset:
        experimental_300K = 142.0  # W/(m·K) - experimental silicon at 300K
        computed_300K = payload["kappa_W_per_mK"][0]
        
        print(f"Experimental κ(300K): {experimental_300K:.1f} W/(m·K)")
        print(f"Computed κ(300K):     {computed_300K:.1f} W/(m·K)")
        print(f"Relative error:       {abs(computed_300K - experimental_300K)/experimental_300K*100:.1f}%")
        print("\nNote: BTE typically overestimates κ without grain boundary scattering")
    
    print("\n" + "=" * 60)
    print("kALDo BTE calculation complete!")
    print("Full phonon transport analysis with lineage tracking.")
    print("=" * 60)

if __name__ == "__main__":
    main()