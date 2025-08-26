"""Integration test for the MCG workflow"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.schema import Asset, Edge, Run
from common.ids import generate_id, run_id
from interfaces_mcp.tools import InterfacesTools
from memory_mcp.store import MemoryStore

def test_silicon_workflow():
    """Test the silicon thermal conductivity workflow"""
    
    print("Testing MCG Silicon Workflow...")
    
    # Initialize components
    interfaces = InterfacesTools()
    memory = MemoryStore()
    
    # Step 1: Test planning
    task = "Pull mp-149 silicon and simulate thermal conductivity 300-800 K with a 20x20x20 supercell using CHGNet on GPU"
    plan = interfaces.plan(task)
    
    assert plan['runner_kind'] is not None
    assert plan['workflow'] == 'fetch_then_kappa'
    assert plan['params']['material_id'] == 'mp149'  # Fixed: mp-149 becomes mp149
    assert plan['params']['T_K'] == [300, 400, 500, 600, 700, 800]
    assert plan['params']['supercell'] == [20, 20, 20]
    print("✓ Planning successful")
    
    # Step 2: Test asset storage
    silicon_system = Asset(
        type="System",
        id=generate_id("S"),
        payload={
            "atoms": [{"el": "Si", "pos": [0, 0, 0]}],
            "lattice": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
            "pbc": [True, True, True]
        }
    )
    
    system_id = memory.put_asset(silicon_system)
    retrieved = memory.get_asset(system_id)
    assert retrieved is not None
    assert retrieved.type == "System"
    print("✓ Asset storage successful")
    
    # Step 3: Test lineage tracking
    test_run_id = run_id()
    edges = [
        Edge(system_id, test_run_id, "USES", "2024-01-01T00:00:00Z"),
        Edge(test_run_id, "R_results", "PRODUCES", "2024-01-01T00:01:00Z"),
    ]
    
    count = memory.append_edges(edges)
    assert count == 2
    
    ledger = memory.query_edges(run_id=test_run_id)
    assert len(ledger) == 2
    print("✓ Lineage tracking successful")
    
    # Step 4: Test explanation
    results_asset = Asset(
        type="Results",
        id="R_results",
        payload={
            "T_K": [300, 400, 500],
            "kappa_W_per_mK": [150.0, 100.0, 75.0],
            "method": "Green-Kubo",
            "supercell": [20, 20, 20]
        }
    )
    
    explanation = interfaces.explain([results_asset], ledger)
    assert "Thermal Conductivity Results" in explanation
    assert "300 K: 150.00 W/(m·K)" in explanation
    assert "decreasing with temperature" in explanation
    print("✓ Explanation generation successful")
    
    print("\n✅ All integration tests passed!")

if __name__ == "__main__":
    test_silicon_workflow()