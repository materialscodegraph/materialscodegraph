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
        self.memory = MemoryMCP()  # Create shared memory instance
        self.compute = ComputeMCP(shared_memory=self.memory)
    
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
        
        # Handle both Run objects and dictionaries
        if hasattr(run, 'id'):
            return run.id
        elif isinstance(run, dict) and 'id' in run:
            return run["id"]
        else:
            return str(run)
    
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

# Interfaces MCP client
class InterfacesMCP:
    def plan(self, task: str) -> Dict[str, Any]:
        """Generate execution plan from natural language task"""
        try:
            from interfaces_mcp.tools import InterfacesTools
            tools = InterfacesTools()
            plan = tools.plan(task)
            
            # Convert assets to dicts
            plan["assets"] = [a.to_dict() for a in plan["assets"]]
            
            return plan
        except ImportError:
            raise ImportError(
                "Interfaces MCP tools not available. "
                "Please ensure interfaces_mcp module is properly installed."
            )
    
    def explain(self, results_assets, ledger_slice) -> str:
        """Generate explanation of results"""
        try:
            from interfaces_mcp.tools import InterfacesTools
            from common.schema import Asset, Edge
            
            tools = InterfacesTools()
            
            # Convert dicts to objects
            assets = [Asset.from_dict(a) for a in results_assets]
            edges = [Edge.from_dict(e) for e in ledger_slice]
            
            return tools.explain(assets, edges)
        except ImportError:
            raise ImportError(
                "Interfaces MCP tools not available. "
                "Please ensure interfaces_mcp module is properly installed."
            )

class ComputeMCP:
    def __init__(self, shared_memory=None):
        self.shared_memory = shared_memory
    
    def start(self, runner_kind: str, asset_ids: list, params: dict) -> Dict[str, Any]:
        """Start actual compute run"""
        from common.ids import run_id
        from common.schema import Run, Asset
        
        # Create run object
        run_obj = Run(
            id=run_id(),
            kind=runner_kind,
            status="running",
            runner_version="1.0.0"
        )
        
        # Get assets from memory
        memory = self.shared_memory or MemoryMCP()
        assets = []
        if asset_ids:
            stored_assets = memory.get_assets(asset_ids)
            assets = [Asset.from_dict(a) for a in stored_assets if a is not None]
        
        # Execute using config-based runner
        try:
            from compute_mcp.generic_runner import GenericRunner
            runner = GenericRunner()
            result = runner.run(runner_kind, run_obj, assets, params)
            
            # Store results in shared memory  
            if result.get("assets"):
                memory.put_assets(result["assets"])  # Already dictionaries
            if result.get("edges"):
                memory.link(result["edges"])  # Already dictionaries
            
            return result.get("run", result)
            
        except Exception as e:
            run_obj.status = "error"
            raise e
    
    def status(self, run_id: str) -> Dict[str, Any]:
        """Check run status"""
        # TODO: Implement proper status tracking
        # For now, assume all runs are completed
        return {
            "status": "done",
            "eta": None
        }
    
    def results(self, run_id: str) -> Dict[str, Any]:
        """Retrieve actual results from memory"""
        memory = self.shared_memory or MemoryMCP()
        
        # Query edges to find assets produced by this run
        edges = memory.query_edges(from_id=run_id)
        
        # Find assets produced by this run
        result_assets = []
        for edge_dict in edges:
            if edge_dict["rel"] == "PRODUCES":
                asset = memory.get_asset(edge_dict["to"])
                if asset:
                    result_assets.append(asset)
        
        if not result_assets:
            raise ValueError(f"No assets found for run {run_id}")
        
        return {
            "assets": result_assets,
            "edges": edges
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
        for asset_data in assets:
            # Handle both Asset objects and dictionaries
            if isinstance(asset_data, dict):
                asset = Asset.from_dict(asset_data)
            else:
                # Already an Asset object
                asset = asset_data
            aid = self.store.put_asset(asset)
            ids.append(aid)
        return ids
    
    def link(self, edges) -> int:
        """Store edges"""
        from common.schema import Edge
        
        edge_objs = []
        for edge_data in edges:
            # Handle both Edge objects and dictionaries
            if isinstance(edge_data, dict):
                edge = Edge.from_dict(edge_data)
            else:
                # Already an Edge object
                edge = edge_data
            edge_objs.append(edge)
        return self.store.append_edges(edge_objs)
    
    def get_asset(self, asset_id: str) -> dict:
        """Get single asset"""
        asset = self.store.get_asset(asset_id)
        return asset.to_dict() if asset else None
    
    def get_assets(self, asset_ids: list) -> list:
        """Get multiple assets"""
        assets = self.store.get_assets(asset_ids)
        return [a.to_dict() for a in assets]
    
    def query_edges(self, **kwargs) -> list:
        """Query edges"""
        edges = self.store.query_edges(**kwargs)
        return [e.to_dict() for e in edges]
    
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
    
    # Run command (combines plan and start)
    run_parser = subparsers.add_parser("run", help="Plan and execute task in one step")
    run_parser.add_argument("task", help="Natural language task description or plan file")
    run_parser.add_argument("-o", "--output", help="Save final results to file")
    run_parser.add_argument("--save-plan", help="Save intermediate plan to file")
    run_parser.add_argument("--dry-run", action="store_true", help="Only create plan, don't execute")
    
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
            
            # Handle workflow execution in start command as well
            if plan.get("workflow") == "fetch_then_kappa":
                try:
                    # Two-step workflow
                    print("Starting two-step workflow: fetch then kappa")
                    
                    # Step 1: Fetch structure
                    mp_plan = {
                        "runner_kind": "MaterialsProject",
                        "assets": [a for a in plan["assets"] if a["type"] == "Params"],
                        "params": plan["params"]
                    }
                    run_id1 = client.start(mp_plan)
                    print(f"Step 1 - Materials Project fetch: {run_id1}")
                    
                    # Step 2: Run kappa calculation using assets from Step 1
                    step1_results = client.results(run_id1)
                    
                    # Combine System asset from Step 1 with Method/Params from original plan
                    combined_assets = step1_results["assets"]  # System asset from MaterialsProject
                    
                    # Add Method and Params assets from original plan
                    for asset in plan.get("assets", []):
                        if asset["type"] in ["Method", "Params"]:
                            combined_assets.append(asset)
                    
                    # If no Method asset found, add a default LAMMPS method
                    has_method = any(asset["type"] == "Method" for asset in combined_assets)
                    if not has_method:
                        from common.ids import generate_id
                        method_asset = {
                            "type": "Method",
                            "id": generate_id("M"),
                            "payload": {
                                "family": "MD",
                                "code": "LAMMPS", 
                                "model": "LJ",
                                "device": "CPU"
                            }
                        }
                        combined_assets.append(method_asset)
                    
                    # Run LAMMPS calculation
                    lammps_plan = {
                        "runner_kind": "LAMMPS",
                        "assets": combined_assets,
                        "params": plan["params"]
                    }
                    run_id2 = client.start(lammps_plan)
                    print(f"Step 2 - LAMMPS kappa calculation: {run_id2}")
                    print(f"Run IDs: {run_id1}, {run_id2}")
                    
                except Exception as e:
                    print(f"Error: {e}")
                    raise
            else:
                # Single-step execution
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
        
        elif args.command == "run":
            # Combined plan and execute command
            
            # Check if task is a file path (existing plan)
            if args.task.endswith('.json') and Path(args.task).exists():
                print(f"Loading plan from: {args.task}")
                with open(args.task, "r") as f:
                    plan = json.load(f)
            else:
                # Create plan from natural language task
                print(f"Creating plan for: {args.task}")
                plan = client.plan(args.task)
                
                # Check for missing parameters
                if plan.get("missing"):
                    print(f"Error: Missing parameters: {', '.join(plan['missing'])}")
                    print("Please provide more specific task details:")
                    for param in plan["missing"]:
                        if param == "temperature_grid":
                            print("  - Temperature range (e.g., '300-800 K in 100K steps')")
                        elif param == "supercell":
                            print("  - Supercell size (e.g., '5x5x5 supercell')")
                        elif param == "material_id":
                            print("  - Material ID (e.g., 'mp-149 silicon')")
                    sys.exit(1)
            
            # Save plan if requested
            if args.save_plan:
                with open(args.save_plan, "w") as f:
                    json.dump(plan, f, indent=2)
                print(f"Plan saved to: {args.save_plan}")
            
            # Exit if dry run
            if args.dry_run:
                print("\nDry run - plan created but not executed:")
                print(json.dumps(plan, indent=2))
                return
            
            print("\nExecuting plan...")
            
            # Handle workflow execution
            if plan.get("workflow") == "fetch_then_kappa":
                try:
                    # Two-step workflow
                    print("Starting two-step workflow: fetch then kappa")
                    
                    # Step 1: Fetch structure
                    mp_plan = {
                        "runner_kind": "MaterialsProject",
                        "assets": [a for a in plan["assets"] if a["type"] == "Params"],
                        "params": plan["params"]
                    }
                    run_id1 = client.start(mp_plan)
                    print(f"Step 1 - Materials Project fetch: {run_id1}")
                    
                    # Step 2: Run kappa calculation using assets from Step 1
                    step1_results = client.results(run_id1)
                    
                    # Combine System asset from Step 1 with Method/Params from original plan
                    combined_assets = step1_results["assets"]  # System asset from MaterialsProject
                    
                    # Add Method and Params assets from original plan
                    for asset in plan.get("assets", []):
                        if asset["type"] in ["Method", "Params"]:
                            combined_assets.append(asset)
                    
                    # If no Method asset found, add a default LAMMPS method
                    has_method = any(asset["type"] == "Method" for asset in combined_assets)
                    if not has_method:
                        from common.ids import generate_id
                        method_asset = {
                            "type": "Method",
                            "id": generate_id("M"),
                            "payload": {
                                "family": "MD",
                                "code": "LAMMPS", 
                                "model": "LJ",
                                "device": "CPU"
                            }
                        }
                        combined_assets.append(method_asset)
                    
                    # Run LAMMPS calculation
                    lammps_plan = {
                        "runner_kind": "LAMMPS",
                        "assets": combined_assets,
                        "params": plan["params"]
                    }
                    run_id2 = client.start(lammps_plan)
                    print(f"Step 2 - LAMMPS kappa calculation: {run_id2}")
                    
                    final_run_id = run_id2
                    print(f"\nWorkflow complete! Run IDs: {run_id1}, {run_id2}")
                    
                except Exception as e:
                    print(f"Error: {e}")
                    raise
                
            else:
                # Single-step execution
                final_run_id = client.start(plan)
                print(f"Started run: {final_run_id}")
            
            # Get and display results
            print("\nRetrieving results...")
            results = client.results(final_run_id)
            
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"Results saved to: {args.output}")
            
            # Pretty print results summary
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
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Add app directory to path for imports
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    main()