"""Interfaces MCP server for natural language interactions"""
import asyncio
import json
from typing import Dict, List, Any

from mcp import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.common.schema import Asset, Edge
from app.interfaces_mcp.tools import InterfacesTools

# Create MCP server
app = Server("interfaces-mcp")

# Initialize tools
tools = InterfacesTools()

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Interfaces MCP tools"""
    return [
        Tool(
            name="plan",
            description="Parse natural language task and create execution plan",
            input_schema={
                "type": "object",
                "properties": {
                    "nl_task": {"type": "string"},
                    "context_assets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "id": {"type": "string"},
                                "payload": {"type": "object"}
                            }
                        }
                    }
                },
                "required": ["nl_task"]
            }
        ),
        Tool(
            name="explain",
            description="Generate human-readable explanation of results",
            input_schema={
                "type": "object",
                "properties": {
                    "results_assets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "id": {"type": "string"},
                                "payload": {"type": "object"}
                            }
                        }
                    },
                    "ledger_slice": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "rel": {"type": "string"},
                                "t": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["results_assets", "ledger_slice"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute Interfaces MCP tools"""
    
    if name == "plan":
        nl_task = arguments["nl_task"]
        context_assets_data = arguments.get("context_assets", [])
        
        # Convert dict to Asset objects
        context_assets = []
        for asset_data in context_assets_data:
            context_assets.append(Asset.from_dict(asset_data))
        
        plan = tools.plan(nl_task, context_assets)
        
        # Convert assets back to dicts for JSON serialization
        plan["assets"] = [a.to_dict() for a in plan["assets"]]
        
        return [TextContent(
            type="text",
            text=json.dumps(plan)
        )]
    
    elif name == "explain":
        results_assets_data = arguments["results_assets"]
        ledger_slice_data = arguments["ledger_slice"]
        
        # Convert dicts to objects
        results_assets = [Asset.from_dict(a) for a in results_assets_data]
        ledger_slice = [Edge.from_dict(e) for e in ledger_slice_data]
        
        explanation = tools.explain(results_assets, ledger_slice)
        
        return [TextContent(
            type="text",
            text=explanation
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Run the Interfaces MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())