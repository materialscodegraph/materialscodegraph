"""Unit tests for Memory MCP and storage"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.schema import Asset, Edge
from memory_mcp.store import MemoryStore

class TestMemoryStore:
    """Test MemoryStore functionality"""
    
    def test_asset_storage(self):
        """Test storing and retrieving assets"""
        store = MemoryStore()
        
        # Create test asset
        asset = Asset(
            type="System",
            id="S_test123",
            payload={
                "atoms": [{"el": "Si", "pos": [0, 0, 0]}],
                "lattice": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "pbc": [True, True, True]
            }
        )
        
        # Store asset
        asset_id = store.put_asset(asset)
        assert asset_id == "S_test123"
        
        # Retrieve asset
        retrieved = store.get_asset(asset_id)
        assert retrieved is not None
        assert retrieved.type == asset.type
        assert retrieved.payload == asset.payload
    
    def test_multiple_assets(self):
        """Test storing and retrieving multiple assets"""
        store = MemoryStore()
        
        # Create multiple assets
        assets = [
            Asset(type="System", id=f"S{i}", payload={"test": i})
            for i in range(5)
        ]
        
        # Store all
        for asset in assets:
            store.put_asset(asset)
        
        # Retrieve multiple
        ids = ["S0", "S2", "S4"]
        retrieved = store.get_assets(ids)
        
        assert len(retrieved) == 3
        assert retrieved[0].id == "S0"
        assert retrieved[1].id == "S2"
        assert retrieved[2].id == "S4"
    
    def test_edge_append(self):
        """Test appending edges to ledger"""
        store = MemoryStore()
        
        # Create edges
        edge1 = Edge(
            from_id="S123",
            to_id="R456",
            rel="USES",
            t="2024-01-01T00:00:00Z"
        )
        
        edge2 = Edge(
            from_id="R456",
            to_id="R789",
            rel="PRODUCES",
            t="2024-01-01T00:01:00Z"
        )
        
        # Append edges
        store.append_edge(edge1)
        store.append_edge(edge2)
        
        # Verify immutability - edges should be in order
        assert len(store.edges) == 2
        assert store.edges[0].from_id == "S123"
        assert store.edges[1].from_id == "R456"
    
    def test_edge_query(self):
        """Test querying edges with filters"""
        store = MemoryStore()
        
        # Add test edges
        edges = [
            Edge("S1", "R1", "USES", "2024-01-01T00:00:00Z"),
            Edge("M1", "R1", "CONFIGURES", "2024-01-01T00:00:01Z"),
            Edge("R1", "R2", "PRODUCES", "2024-01-01T00:00:02Z"),
            Edge("R1", "A1", "LOGS", "2024-01-01T00:00:03Z"),
            Edge("S2", "R2", "USES", "2024-01-01T00:00:04Z"),
        ]
        
        for edge in edges:
            store.append_edge(edge)
        
        # Query by from_id
        from_r1 = store.query_edges(from_id="R1")
        assert len(from_r1) == 2
        assert all(e.from_id == "R1" for e in from_r1)
        
        # Query by to_id
        to_r1 = store.query_edges(to_id="R1")
        assert len(to_r1) == 2
        assert all(e.to_id == "R1" for e in to_r1)
        
        # Query by run_id (gets all edges related to run)
        run_edges = store.query_edges(run_id="R1")
        assert len(run_edges) == 4  # All edges with R1 as from or to
    
    def test_persistence(self, tmp_path):
        """Test persistence to disk"""
        persist_file = tmp_path / "test_store.json"
        
        # Create store with persistence
        store1 = MemoryStore(persist_path=persist_file)
        
        # Add data
        asset = Asset(
            type="Results",
            id="R_persist",
            payload={"data": [1, 2, 3]}
        )
        store1.put_asset(asset)
        
        edge = Edge("R_persist", "A1", "PRODUCES", "2024-01-01T00:00:00Z")
        store1.append_edge(edge)
        
        # Create new store from same file
        store2 = MemoryStore(persist_path=persist_file)
        
        # Verify data loaded
        loaded_asset = store2.get_asset("R_persist")
        assert loaded_asset is not None
        assert loaded_asset.payload == {"data": [1, 2, 3]}
        
        assert len(store2.edges) == 1
        assert store2.edges[0].from_id == "R_persist"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])