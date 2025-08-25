"""Memory MCP server for asset storage and lineage tracking"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from mcp import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.common.schema import Asset, Edge
from app.common.ids import asset_id
from app.memory_mcp.store import MemoryStore

# Initialize store with persistence
STORE_PATH = Path.home() / ".mcg" / "memory" / "store.json"
store = MemoryStore(persist_path=STORE_PATH)

# Create MCP server
app = Server("memory-mcp")

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Memory MCP tools"""
    return [
        Tool(
            name="put_assets",
            description="Store one or more assets",
            input_schema={
                "type": "object",
                "properties": {
                    "assets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "id": {"type": "string"},
                                "payload": {"type": "object"},
                                "units": {"type": "object"},
                                "uri": {"type": "string"},
                                "hash": {"type": "string"}
                            },
                            "required": ["type", "id", "payload"]
                        }
                    }
                },
                "required": ["assets"]
            }
        ),
        Tool(
            name="get_assets",
            description="Retrieve assets by IDs",
            input_schema={
                "type": "object",
                "properties": {
                    "ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["ids"]
            }
        ),
        Tool(
            name="link",
            description="Record lineage edges",
            input_schema={
                "type": "object",
                "properties": {
                    "edges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "rel": {"type": "string"},
                                "t": {"type": "string"}
                            },
                            "required": ["from", "to", "rel"]
                        }
                    }
                },
                "required": ["edges"]
            }
        ),
        Tool(
            name="ledger",
            description="Query lineage edges",
            input_schema={
                "type": "object",
                "properties": {
                    "select": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "run_id": {"type": "string"}
                        }
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute Memory MCP tools"""
    
    if name == "put_assets":
        assets_data = arguments.get("assets", [])
        ids = []
        
        for asset_data in assets_data:
            # Ensure ID is set
            if "id" not in asset_data or not asset_data["id"]:
                asset_data["id"] = asset_id(
                    asset_data["type"], 
                    asset_data["payload"]
                )
            
            asset = Asset.from_dict(asset_data)
            asset_id_str = store.put_asset(asset)
            ids.append(asset_id_str)
        
        return [TextContent(
            type="text",
            text=f"Stored {len(ids)} assets: {ids}"
        )]
    
    elif name == "get_assets":
        ids = arguments.get("ids", [])
        assets = store.get_assets(ids)
        
        return [TextContent(
            type="text",
            text=str([a.to_dict() for a in assets])
        )]
    
    elif name == "link":
        edges_data = arguments.get("edges", [])
        edges = []
        
        for edge_data in edges_data:
            # Add timestamp if not provided
            if "t" not in edge_data:
                edge_data["t"] = datetime.utcnow().isoformat()
            
            edge = Edge.from_dict(edge_data)
            edges.append(edge)
        
        count = store.append_edges(edges)
        
        return [TextContent(
            type="text",
            text=f"Added {count} edges to ledger"
        )]
    
    elif name == "ledger":
        select = arguments.get("select", {})
        edges = store.query_edges(
            from_id=select.get("from"),
            to_id=select.get("to"),
            run_id=select.get("run_id")
        )
        
        return [TextContent(
            type="text",
            text=str([e.to_dict() for e in edges])
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Run the Memory MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())