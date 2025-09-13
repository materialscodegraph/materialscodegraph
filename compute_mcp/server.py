"""Compute MCP server for running simulations"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from mcp import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from common.schema import Asset, Edge, Run
from common.ids import run_id
from compute_mcp.generic_runner import GenericRunner

# Create MCP server
app = Server("compute-mcp")

# Store for active runs (in production, use proper state management)
active_runs: Dict[str, Run] = {}
run_results: Dict[str, Dict[str, Any]] = {}

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Compute MCP tools"""
    return [
        Tool(
            name="start",
            description="Start a compute run",
            input_schema={
                "type": "object",
                "properties": {
                    "runner_kind": {
                        "type": "string",
                        "description": "Name of the computational runner to use"
                    },
                    "asset_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "params": {"type": "object"}
                },
                "required": ["runner_kind"]
            }
        ),
        Tool(
            name="status",
            description="Get run status",
            input_schema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="results",
            description="Get run results",
            input_schema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"}
                },
                "required": ["run_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute Compute MCP tools"""
    
    if name == "start":
        runner_kind = arguments["runner_kind"]
        asset_ids = arguments.get("asset_ids", [])
        params = arguments.get("params", {})
        
        # Create run record
        run = Run(
            id=run_id(),
            kind=runner_kind,
            status="queued",
            started_at=datetime.utcnow().isoformat()
        )
        
        active_runs[run.id] = run
        
        # In production, would dispatch to queue/scheduler
        # For now, run synchronously
        try:
            # Note: In real implementation, would fetch assets from Memory MCP
            # For now, create placeholder assets
            assets = []

            # Use the generic runner with zero domain knowledge
            runner = GenericRunner()
            results = runner.run(runner_kind, run, assets, params)

            run_results[run.id] = results
            active_runs[run.id] = results["run"]
            
        except Exception as e:
            run.status = "error"
            run.ended_at = datetime.utcnow().isoformat()
            active_runs[run.id] = run
            return [TextContent(
                type="text",
                text=f"Error starting run: {str(e)}"
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps(run.to_dict())
        )]
    
    elif name == "status":
        run_id_str = arguments["run_id"]
        
        if run_id_str not in active_runs:
            return [TextContent(
                type="text",
                text=f"Run {run_id_str} not found"
            )]
        
        run = active_runs[run_id_str]
        
        # Estimate ETA for running jobs
        eta = None
        if run.status == "running":
            eta = "~5 minutes"  # Placeholder
        
        status_info = {
            "status": run.status,
            "started_at": run.started_at,
            "ended_at": run.ended_at
        }
        if eta:
            status_info["eta"] = eta
        
        return [TextContent(
            type="text",
            text=json.dumps(status_info)
        )]
    
    elif name == "results":
        run_id_str = arguments["run_id"]
        
        if run_id_str not in run_results:
            return [TextContent(
                type="text",
                text=f"Results for run {run_id_str} not available"
            )]
        
        results = run_results[run_id_str]
        
        # Return assets and edges
        output = {
            "assets": [a.to_dict() for a in results["assets"]],
            "edges": [e.to_dict() for e in results["edges"]]
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(output)
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Run the Compute MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())