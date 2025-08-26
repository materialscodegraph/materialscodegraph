#!/usr/bin/env python3
"""Scripted example of the silicon thermal conductivity workflow"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from datetime import datetime
from common.schema import Asset, Edge, Run
from common.ids import asset_id, run_id, generate_id
from interfaces_mcp.tools import InterfacesTools
from compute_mcp.runners.lammps_kappa_gk import LAMMPSKappaGKRunner
from memory_mcp.store import MemoryStore

def main():
    """Execute the silicon thermal conductivity workflow"""
    
    print("=" * 60)
    print("MaterialsCodeGraph - Silicon Thermal Conductivity Workflow")
    print("=" * 60)
    
    # Initialize components
    interfaces = InterfacesTools()
    memory = MemoryStore()
    
    # Step 1: Plan the task
    print("\n1. PLANNING THE TASK")
    print("-" * 40)
    
    task = "Pull mp-149 silicon and simulate thermal conductivity 300-800 K with a 20x20x20 supercell using CHGNet on GPU"
    print(f"Task: {task}")
    
    plan = interfaces.plan(task)
    print(f"\nPlan created:")
    print(f"  Runner: {plan['runner_kind']}")
    print(f"  Workflow: {plan['workflow']}")
    print(f"  Parameters: {json.dumps(plan['params'], indent=4)}")
    
    if plan['missing']:
        print(f"  Missing: {plan['missing']}")
    
    # Step 2: Simulate Materials Project fetch
    print("\n2. FETCHING STRUCTURE FROM MATERIALS PROJECT")
    print("-" * 40)
    
    # Create mock silicon structure
    silicon_system = Asset(
        type="System",
        id=generate_id("S"),
        payload={
            "atoms": [
                {"el": "Si", "pos": [0.0, 0.0, 0.0]},
                {"el": "Si", "pos": [1.3575, 1.3575, 1.3575]},
                {"el": "Si", "pos": [2.715, 0.0, 2.715]},
                {"el": "Si", "pos": [0.0, 2.715, 2.715]},
                {"el": "Si", "pos": [2.715, 2.715, 0.0]},
                {"el": "Si", "pos": [4.0725, 1.3575, 4.0725]},
                {"el": "Si", "pos": [1.3575, 4.0725, 4.0725]},
                {"el": "Si", "pos": [4.0725, 4.0725, 1.3575]}
            ],
            "lattice": [
                [5.43, 0.0, 0.0],
                [0.0, 5.43, 0.0],
                [0.0, 0.0, 5.43]
            ],
            "pbc": [True, True, True]
        },
        units={"length": "angstrom"}
    )
    
    system_id = memory.put_asset(silicon_system)
    print(f"Silicon structure fetched: mp-149")
    print(f"  Lattice parameter: 5.43 Å")
    print(f"  Space group: Fd-3m (diamond cubic)")
    print(f"  System asset ID: {system_id}")
    
    # Step 3: Run LAMMPS simulation
    print("\n3. RUNNING LAMMPS GREEN-KUBO SIMULATION")
    print("-" * 40)
    
    # Create method asset
    method = Asset(
        type="Method",
        id=generate_id("M"),
        payload={
            "family": "MD",
            "code": "LAMMPS",
            "model": "CHGNet",
            "device": "GPU"
        }
    )
    method_id = memory.put_asset(method)
    
    # Create params asset
    params = Asset(
        type="Params",
        id=generate_id("P"),
        payload={
            "supercell": [20, 20, 20],
            "T_K": [300, 400, 500, 600, 700, 800],
            "timestep_fs": 1.0,
            "equil_ps": 100,
            "prod_ps": 500,
            "HFACF_window_ps": 200
        }
    )
    params_id = memory.put_asset(params)
    
    print(f"Simulation parameters:")
    print(f"  Supercell: 20x20x20 (8000 atoms)")
    print(f"  Temperatures: 300-800 K")
    print(f"  Equilibration: 100 ps")
    print(f"  Production: 500 ps")
    print(f"  Model: CHGNet on GPU")
    
    # Create and execute run
    run = Run(
        id=run_id(),
        kind="LAMMPS",
        status="queued"
    )
    
    runner = LAMMPSKappaGKRunner()
    
    print(f"\nRun ID: {run.id}")
    print("Status: Running...")
    
    # Execute simulation (mocked)
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
    
    # Step 4: Display results
    print("\n4. RESULTS")
    print("-" * 40)
    
    # Find results asset
    results_asset = None
    for asset in results["assets"]:
        if asset.type == "Results":
            results_asset = asset
            break
    
    if results_asset:
        payload = results_asset.payload
        print("\nThermal Conductivity κ(T):")
        print("Temperature [K]  |  κ [W/(m·K)]")
        print("-" * 32)
        for T, k in zip(payload["T_K"], payload["kappa_W_per_mK"]):
            print(f"     {T:3d}        |   {k:6.2f}")
        
        print(f"\nMethod: {payload['method']}")
        print(f"Supercell: {payload['supercell']}")
    
    # Step 5: Generate explanation
    print("\n5. EXPLANATION")
    print("-" * 40)
    
    # Get lineage for this run
    ledger = memory.query_edges(run_id=run.id)
    
    explanation = interfaces.explain(
        results["assets"],
        ledger
    )
    
    print(explanation)
    
    # Step 6: Show lineage
    print("\n6. LINEAGE GRAPH")
    print("-" * 40)
    
    print("Edges in provenance graph:")
    for edge in ledger:
        print(f"  {edge.from_id} --[{edge.rel}]--> {edge.to_id}")
    
    print("\n" + "=" * 60)
    print("Workflow complete! Full lineage tracked.")
    print("=" * 60)

if __name__ == "__main__":
    main()