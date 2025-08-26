#!/usr/bin/env python3
"""Simple test runner for MCG without external dependencies"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.schema import Asset, Edge, Run, validate_asset
from common.ids import generate_id, asset_id, run_id, hash_dict
from memory_mcp.store import MemoryStore
from interfaces_mcp.tools import InterfacesTools

def test_schema():
    """Test schema validation"""
    print("Testing schema...")
    
    # Valid System asset
    system = Asset(
        type="System",
        id="S123",
        payload={
            "atoms": [{"el": "Si", "pos": [0, 0, 0]}],
            "lattice": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
            "pbc": [True, True, True]
        }
    )
    assert validate_asset(system), "System validation failed"
    
    # Valid Method asset  
    method = Asset(
        type="Method",
        id="M123",
        payload={"family": "MD", "code": "LAMMPS"}
    )
    assert validate_asset(method), "Method validation failed"
    
    # Test serialization
    asset_dict = system.to_dict()
    restored = Asset.from_dict(asset_dict)
    assert restored.type == system.type, "Serialization failed"
    
    print("✓ Schema tests passed")

def test_ids():
    """Test ID generation"""
    print("Testing ID generation...")
    
    # Test deterministic hashing
    data = {"key": "value", "num": 42}
    hash1 = hash_dict(data)
    hash2 = hash_dict(data)
    assert hash1 == hash2, "Hash not deterministic"
    
    # Test asset IDs
    aid = asset_id("System", {"atoms": []})
    assert aid.startswith("S"), f"Asset ID should start with S, got {aid}"
    
    # Test run IDs
    rid = run_id()
    assert rid.startswith("R"), f"Run ID should start with R, got {rid}"
    assert len(rid) == 9, f"Run ID should be 9 chars, got {len(rid)}"
    
    print("✓ ID tests passed")

def test_memory():
    """Test memory store"""
    print("Testing memory store...")
    
    store = MemoryStore()
    
    # Test asset storage
    asset = Asset(type="Results", id="R123", payload={"data": [1, 2, 3]})
    aid = store.put_asset(asset)
    retrieved = store.get_asset(aid)
    assert retrieved.payload == asset.payload, "Asset retrieval failed"
    
    # Test edge tracking
    edge = Edge("S1", "R1", "USES", "2024-01-01T00:00:00Z")
    store.append_edge(edge)
    edges = store.query_edges(from_id="S1")
    assert len(edges) == 1, f"Expected 1 edge, got {len(edges)}"
    
    print("✓ Memory tests passed")

def test_interfaces():
    """Test planning and explanation"""
    print("Testing interfaces...")
    
    tools = InterfacesTools()
    
    # Test LAMMPS planning
    task = "Pull mp-149 and simulate thermal conductivity 300-800 K with 20x20x20 supercell"
    plan = tools.plan(task)
    assert plan['params']['material_id'] == 'mp149', f"Material ID wrong: {plan['params']}"
    assert plan['params']['T_K'] == [300, 400, 500, 600, 700, 800], "Temperature range wrong"
    
    # Test kALDo BTE planning
    bte_task = "Calculate thermal conductivity using kALDo BTE for silicon at 300-500K with 20x20x20 mesh"
    bte_plan = tools.plan(bte_task)
    assert bte_plan['runner_kind'] == 'kALDo', f"BTE runner wrong: {bte_plan['runner_kind']}"
    assert bte_plan['params']['mesh'] == [20, 20, 20], "BTE mesh wrong"
    assert bte_plan['workflow'] == 'bte_calculation', "BTE workflow wrong"
    
    # Test LAMMPS explanation
    lammps_results = Asset(
        type="Results",
        id="R_lammps",
        payload={
            "T_K": [300, 400],
            "kappa_W_per_mK": [150.0, 100.0],
            "method": "Green-Kubo"
        }
    )
    
    edges = [Edge("S1", "R1", "USES", "2024-01-01T00:00:00Z")]
    explanation = tools.explain([lammps_results], edges)
    assert "Thermal Conductivity Results" in explanation, "LAMMPS explanation missing"
    
    # Test BTE explanation
    bte_results = Asset(
        type="Results", 
        id="R_bte",
        payload={
            "T_K": [300, 400],
            "kappa_W_per_mK": [180.0, 120.0],
            "kappa_xx_W_per_mK": [182.0, 121.0],
            "kappa_yy_W_per_mK": [178.0, 119.0], 
            "kappa_zz_W_per_mK": [180.0, 120.0],
            "method": "BTE",
            "solver": "kALDo",
            "mesh": [20, 20, 20],
            "phonon_freq_THz": [2.1, 8.5, 14.2],
            "lifetimes_ps": [45.2, 15.8, 8.1]
        }
    )
    
    bte_explanation = tools.explain([bte_results], edges)
    assert "BTE" in bte_explanation, "BTE explanation missing method"
    assert "Tensor Components" in bte_explanation, "BTE tensor components missing"
    assert "Phonon Summary" in bte_explanation, "Phonon analysis missing"
    
    print("✓ Interface tests passed (LAMMPS + kALDo)")

def test_cli_flow():
    """Test CLI workflow simulation"""
    print("Testing CLI flow...")
    
    # Import CLI components
    from cli.mcg import MCGClient
    
    client = MCGClient()
    
    # Test planning
    task = "Pull mp-149 silicon and simulate thermal conductivity 300-400 K with 10x10x10 supercell"
    plan = client.plan(task)
    assert plan['runner_kind'] is not None, "No runner kind in plan"
    
    # Test execution simulation
    plan_simple = {
        "runner_kind": "LAMMPS",
        "assets": [],
        "params": {"T_K": [300, 400], "supercell": [10, 10, 10]}
    }
    
    run_id = client.start(plan_simple)
    assert run_id.startswith("R"), f"Run ID should start with R, got {run_id}"
    
    # Test status
    status = client.status(run_id)
    assert status['status'] == 'done', f"Status should be done, got {status['status']}"
    
    # Test results
    results = client.results(run_id)
    assert 'assets' in results, "Results missing assets"
    
    print("✓ CLI flow tests passed")

def main():
    """Run all tests"""
    print("=" * 50)
    print("Running MCG Test Suite")
    print("=" * 50)
    
    try:
        test_schema()
        test_ids() 
        test_memory()
        test_interfaces()
        test_cli_flow()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("MCG-lite is fully functional")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()