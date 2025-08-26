"""Unit tests for schema validation"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.schema import Asset, Run, Edge, validate_system, validate_method, validate_asset

class TestAsset:
    """Test Asset dataclass and validation"""
    
    def test_system_asset_valid(self):
        """Test valid System asset"""
        system = Asset(
            type="System",
            id="S123",
            payload={
                "atoms": [
                    {"el": "Si", "pos": [0.0, 0.0, 0.0]},
                    {"el": "Si", "pos": [1.35, 1.35, 1.35]}
                ],
                "lattice": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
                "pbc": [True, True, True]
            },
            units={"length": "angstrom"}
        )
        
        assert validate_asset(system)
        assert system.type == "System"
        assert len(system.payload["atoms"]) == 2
    
    def test_system_asset_invalid(self):
        """Test invalid System asset"""
        # Missing atoms
        system1 = Asset(
            type="System",
            id="S124",
            payload={
                "lattice": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
                "pbc": [True, True, True]
            }
        )
        assert not validate_asset(system1)
        
        # Wrong atom position dimensions
        system2 = Asset(
            type="System",
            id="S125",
            payload={
                "atoms": [{"el": "Si", "pos": [0.0, 0.0]}],  # Only 2D
                "lattice": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
                "pbc": [True, True, True]
            }
        )
        assert not validate_asset(system2)
    
    def test_method_asset_valid(self):
        """Test valid Method asset"""
        method = Asset(
            type="Method",
            id="M123",
            payload={
                "family": "MD",
                "code": "LAMMPS",
                "model": "CHGNet",
                "device": "GPU"
            }
        )
        
        assert validate_asset(method)
        assert method.payload["family"] == "MD"
    
    def test_method_asset_invalid(self):
        """Test invalid Method asset"""
        # Invalid family
        method = Asset(
            type="Method",
            id="M124",
            payload={
                "family": "INVALID",
                "code": "LAMMPS"
            }
        )
        assert not validate_asset(method)
    
    def test_asset_serialization(self):
        """Test asset to_dict and from_dict"""
        original = Asset(
            type="Results",
            id="R123",
            payload={"kappa_W_per_mK": [150.0, 120.0]},
            units={"kappa_W_per_mK": "W/(m*K)"},
            uri="mcg://results/R123.json",
            hash="abcd1234"
        )
        
        # Convert to dict and back
        asset_dict = original.to_dict()
        restored = Asset.from_dict(asset_dict)
        
        assert restored.type == original.type
        assert restored.id == original.id
        assert restored.payload == original.payload
        assert restored.units == original.units
        assert restored.uri == original.uri
        assert restored.hash == original.hash

class TestRun:
    """Test Run dataclass"""
    
    def test_run_creation(self):
        """Test Run creation and attributes"""
        run = Run(
            id="R12345678",
            kind="LAMMPS",
            status="running",
            runner_version="1.0.0"
        )
        
        assert run.id == "R12345678"
        assert run.kind == "LAMMPS"
        assert run.status == "running"
        assert run.runner_version == "1.0.0"
    
    def test_run_serialization(self):
        """Test Run to_dict and from_dict"""
        original = Run(
            id="R87654321",
            kind="MaterialsProject",
            status="done",
            runner_version="1.0.0",
            started_at="2024-01-01T00:00:00",
            ended_at="2024-01-01T00:01:00"
        )
        
        run_dict = original.to_dict()
        restored = Run.from_dict(run_dict)
        
        assert restored.id == original.id
        assert restored.kind == original.kind
        assert restored.status == original.status
        assert restored.started_at == original.started_at
        assert restored.ended_at == original.ended_at

class TestEdge:
    """Test Edge dataclass"""
    
    def test_edge_creation(self):
        """Test Edge creation"""
        edge = Edge(
            from_id="S123",
            to_id="R456",
            rel="USES",
            t="2024-01-01T00:00:00Z"
        )
        
        assert edge.from_id == "S123"
        assert edge.to_id == "R456"
        assert edge.rel == "USES"
    
    def test_edge_serialization(self):
        """Test Edge to_dict and from_dict"""
        original = Edge(
            from_id="R456",
            to_id="R789",
            rel="PRODUCES",
            t="2024-01-01T00:00:00Z"
        )
        
        edge_dict = original.to_dict()
        assert edge_dict["from"] == "R456"  # Check field name mapping
        assert edge_dict["to"] == "R789"
        
        restored = Edge.from_dict(edge_dict)
        assert restored.from_id == original.from_id
        assert restored.to_id == original.to_id
        assert restored.rel == original.rel

if __name__ == "__main__":
    pytest.main([__file__, "-v"])