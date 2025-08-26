#!/usr/bin/env python3
"""MaterialsCodeGraph CLI for orchestrating MCP operations"""

import json
import sys
import argparse
from typing import Dict, Any
from pathlib import Path

# For demonstration, simulate MCP calls
# In production, would use proper MCP client library

class MCGClient:
    """Client for interacting with MCPs"""
    
    def __init__(self):
        # In production, would initialize MCP connections
        self.interfaces = InterfacesMCP()
        self.compute = ComputeMCP()
        self.memory = MemoryMCP()
    
    def plan(self, task: str) -> Dict[str, Any]:
        """Create execution plan from natural language task"""
        return self.interfaces.plan(task)
    
    def start(self, plan: Dict[str, Any]) -> str:
        """Start computation from plan"""
        # First, store any assets in memory
        if plan.get("assets"):
            asset_ids = self.memory.put_assets(plan["assets"])
        else:
            asset_ids = []
        
        # Start the computation
        run = self.compute.start(
            runner_kind=plan["runner_kind"],
            asset_ids=asset_ids,
            params=plan.get("params", {})
        )
        
        return run["id"]
    
    def status(self, run_id: str) -> Dict[str, Any]:
        """Check run status"""
        return self.compute.status(run_id)
    
    def results(self, run_id: str) -> Dict[str, Any]:
        """Get run results"""
        # Get results from compute
        results = self.compute.results(run_id)
        
        # Store results in memory
        if results.get("assets"):
            self.memory.put_assets(results["assets"])
        
        if results.get("edges"):
            self.memory.link(results["edges"])
        
        return results
    
    def explain(self, run_id: str) -> str:
        """Explain results in plain language"""
        # Get results and ledger
        results = self.compute.results(run_id)
        ledger = self.memory.ledger({"run_id": run_id})
        
        # Generate explanation
        return self.interfaces.explain(
            results_assets=results.get("assets", []),
            ledger_slice=ledger
        )

# Mock MCP implementations for demonstration
class InterfacesMCP:
    def plan(self, task: str) -> Dict[str, Any]:
        """Mock plan generation"""
        from interfaces_mcp.tools import InterfacesTools
        tools = InterfacesTools()
        plan = tools.plan(task)
        
        # Convert assets to dicts
        plan["assets"] = [a.to_dict() for a in plan["assets"]]
        
        return plan
    
    def explain(self, results_assets, ledger_slice) -> str:
        """Mock explanation generation"""
        from interfaces_mcp.tools import InterfacesTools
        from common.schema import Asset, Edge
        
        tools = InterfacesTools()
        
        # Convert dicts to objects
        assets = [Asset.from_dict(a) for a in results_assets]
        edges = [Edge.from_dict(e) for e in ledger_slice]
        
        return tools.explain(assets, edges)

class ComputeMCP:
    def start(self, runner_kind: str, asset_ids: list, params: dict) -> Dict[str, Any]:
        """Mock compute start"""
        from common.ids import run_id
        
        run = {
            "id": run_id(),
            "kind": runner_kind,
            "status": "running"
        }
        
        # Simulate computation
        if runner_kind == "MaterialsProject":
            # Would actually run MP fetcher
            pass
        elif runner_kind == "LAMMPS":
            # Would actually run LAMMPS
            pass
        elif runner_kind == "kALDo":
            # Would actually run kALDo
            pass
        
        return run
    
    def status(self, run_id: str) -> Dict[str, Any]:
        """Mock status check"""
        # In reality, would check actual run status
        return {
            "status": "done",
            "eta": None
        }
    
    def results(self, run_id: str) -> Dict[str, Any]:
        """Mock results retrieval"""
        # Return simulated results for demonstration
        from common.schema import Asset
        from common.ids import asset_id
        
        # Check if this was a kALDo run based on run characteristics
        # In reality would check stored run metadata
        is_kaldo = run_id.endswith(('a', 'b', 'c', 'd', 'e', 'f'))  # Heuristic
        
        if is_kaldo:
            # Simulate BTE results (higher values, tensor components)
            results_asset = Asset(
                type="Results",
                id=asset_id("Results", {"run": run_id}),
                payload={
                    "T_K": [300, 400, 500, 600, 700, 800],
                    "kappa_W_per_mK": [185.2, 125.8, 89.3, 68.1, 54.2, 44.8],
                    "kappa_xx_W_per_mK": [188.9, 128.3, 91.1, 69.5, 55.3, 45.7],
                    "kappa_yy_W_per_mK": [181.5, 123.3, 87.5, 66.7, 53.1, 43.9],
                    "kappa_zz_W_per_mK": [185.2, 125.8, 89.3, 68.1, 54.2, 44.8],
                    "method": "BTE",
                    "solver": "kALDo",
                    "mesh": [20, 20, 20],
                    "phonon_freq_THz": [2.1, 4.5, 7.8, 12.3, 14.6],
                    "lifetimes_ps": [47.6, 22.2, 12.8, 8.1, 6.8],
                    "broadening_shape": "gauss",
                    "broadening_width_meV": 1.0
                },
                units={
                    "T_K": "K",
                    "kappa_W_per_mK": "W/(m*K)",
                    "kappa_xx_W_per_mK": "W/(m*K)",
                    "kappa_yy_W_per_mK": "W/(m*K)",
                    "kappa_zz_W_per_mK": "W/(m*K)",
                    "phonon_freq_THz": "THz",
                    "lifetimes_ps": "ps",
                    "broadening_width_meV": "meV"
                }
            )
        else:
            # Simulate LAMMPS Green-Kubo results
            results_asset = Asset(
                type="Results",
                id=asset_id("Results", {"run": run_id}),
                payload={
                    "T_K": [300, 400, 500, 600, 700, 800],
                    "kappa_W_per_mK": [148.5, 95.2, 68.1, 51.3, 40.2, 32.5],
                    "method": "Green-Kubo",
                    "supercell": [20, 20, 20]
                },
                units={
                    "T_K": "K",
                    "kappa_W_per_mK": "W/(m*K)"
                }
            )
        
        return {
            "assets": [results_asset.to_dict()],
            "edges": []
        }

class MemoryMCP:
    def __init__(self):
        # Use in-memory store for demonstration
        from memory_mcp.store import MemoryStore
        self.store = MemoryStore()
    
    def put_assets(self, assets) -> list:
        """Store assets"""
        from common.schema import Asset
        
        ids = []
        for asset_dict in assets:
            asset = Asset.from_dict(asset_dict)
            aid = self.store.put_asset(asset)
            ids.append(aid)
        return ids
    
    def link(self, edges) -> int:
        """Store edges"""
        from common.schema import Edge
        
        edge_objs = [Edge.from_dict(e) for e in edges]
        return self.store.append_edges(edge_objs)
    
    def ledger(self, query) -> list:
        """Query ledger"""
        edges = self.store.query_edges(
            from_id=query.get("from"),
            to_id=query.get("to"),
            run_id=query.get("run_id")
        )
        return [e.to_dict() for e in edges]

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="MaterialsCodeGraph CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mcg plan "Pull mp-149 and simulate thermal conductivity 300-800 K with 20x20x20 supercell"
  mcg start --plan plan.json
  mcg status R12345678
  mcg results R12345678
  mcg explain R12345678
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Plan command
    plan_parser = subparsers.add_parser("plan", help="Create execution plan from task")
    plan_parser.add_argument("task", help="Natural language task description")
    plan_parser.add_argument("-o", "--output", help="Save plan to file")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start computation")
    start_parser.add_argument("--plan", required=True, help="Plan file or inline JSON")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check run status")
    status_parser.add_argument("run_id", help="Run ID to check")
    
    # Results command
    results_parser = subparsers.add_parser("results", help="Get run results")
    results_parser.add_argument("run_id", help="Run ID")
    results_parser.add_argument("-o", "--output", help="Save results to file")
    
    # Explain command
    explain_parser = subparsers.add_parser("explain", help="Explain results")
    explain_parser.add_argument("run_id", help="Run ID to explain")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    client = MCGClient()
    
    try:
        if args.command == "plan":
            plan = client.plan(args.task)
            
            # Check for missing parameters
            if plan.get("missing"):
                print(f"Missing parameters: {', '.join(plan['missing'])}")
                print("Please provide:")
                for param in plan["missing"]:
                    if param == "temperature_grid":
                        print("  - Temperature range (e.g., '300-800 K')")
                    elif param == "supercell":
                        print("  - Supercell dimensions (e.g., '20x20x20')")
                    elif param == "material_id":
                        print("  - Material ID (e.g., 'mp-149')")
            
            # Save or print plan
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(plan, f, indent=2)
                print(f"Plan saved to {args.output}")
            else:
                print(json.dumps(plan, indent=2))
        
        elif args.command == "start":
            # Load plan
            if args.plan.startswith("{"):
                plan = json.loads(args.plan)
            else:
                with open(args.plan, "r") as f:
                    plan = json.load(f)
            
            # Handle workflow
            if plan.get("workflow") == "fetch_then_kappa":
                # Two-step workflow
                print("Starting two-step workflow: fetch then kappa")
                
                # Step 1: Fetch structure
                mp_plan = {
                    "runner_kind": "MaterialsProject",
                    "params": {"material_id": plan["params"]["material_id"]}
                }
                run_id1 = client.start(mp_plan)
                print(f"Step 1 - Materials Project fetch: {run_id1}")
                
                # Step 2: Run kappa calculation
                lammps_plan = {
                    "runner_kind": "LAMMPS",
                    "assets": plan["assets"],
                    "params": plan["params"]
                }
                run_id2 = client.start(lammps_plan)
                print(f"Step 2 - LAMMPS kappa calculation: {run_id2}")
                print(f"Run IDs: {run_id1}, {run_id2}")
            else:
                # Single runner
                run_id = client.start(plan)
                print(f"Started run: {run_id}")
        
        elif args.command == "status":
            status = client.status(args.run_id)
            print(f"Status: {status['status']}")
            if status.get("eta"):
                print(f"ETA: {status['eta']}")
        
        elif args.command == "results":
            results = client.results(args.run_id)
            
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"Results saved to {args.output}")
            else:
                # Pretty print results
                for asset in results.get("assets", []):
                    if asset["type"] == "Results":
                        payload = asset["payload"]
                        if "kappa_W_per_mK" in payload:
                            print("\nThermal Conductivity Results:")
                            print(f"Method: {payload.get('method', 'N/A')}")
                            print(f"Supercell: {payload.get('supercell', 'N/A')}")
                            print("\nκ(T) values:")
                            for T, k in zip(payload["T_K"], payload["kappa_W_per_mK"]):
                                print(f"  {T} K: {k:.2f} W/(m·K)")
        
        elif args.command == "explain":
            explanation = client.explain(args.run_id)
            print(explanation)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Add app directory to path for imports
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    main()