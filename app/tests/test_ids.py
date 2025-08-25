"""Unit tests for ID and hash generation"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.common.ids import generate_id, hash_dict, asset_id, run_id

class TestIDGeneration:
    """Test ID generation functions"""
    
    def test_generate_id(self):
        """Test basic ID generation"""
        # Without prefix
        id1 = generate_id()
        assert len(id1) == 8
        assert id1.isalnum()
        
        # With prefix
        id2 = generate_id("TEST_")
        assert id2.startswith("TEST_")
        assert len(id2) == 13  # TEST_ + 8 chars
        
        # IDs should be unique
        id3 = generate_id()
        assert id1 != id3
    
    def test_hash_dict_deterministic(self):
        """Test deterministic hashing of dictionaries"""
        data = {"key1": "value1", "key2": 42, "key3": [1, 2, 3]}
        
        # Same data should produce same hash
        hash1 = hash_dict(data)
        hash2 = hash_dict(data)
        assert hash1 == hash2
        assert len(hash1) == 16
        
        # Different order but same data should produce same hash
        data_reordered = {"key3": [1, 2, 3], "key1": "value1", "key2": 42}
        hash3 = hash_dict(data_reordered)
        assert hash1 == hash3
        
        # Different data should produce different hash
        data_modified = {"key1": "value1", "key2": 43, "key3": [1, 2, 3]}
        hash4 = hash_dict(data_modified)
        assert hash1 != hash4
    
    def test_asset_id_generation(self):
        """Test asset ID generation with type prefixes"""
        # Test different asset types
        system_id = asset_id("System", {"atoms": []})
        assert system_id.startswith("S")
        assert len(system_id) == 7  # S + 6 hash chars
        
        method_id = asset_id("Method", {"family": "MD"})
        assert method_id.startswith("M")
        
        params_id = asset_id("Params", {"temp": 300})
        assert params_id.startswith("P")
        
        results_id = asset_id("Results", {"kappa": [150]})
        assert results_id.startswith("R")
        
        artifact_id = asset_id("Artifact", {"uri": "test.log"})
        assert artifact_id.startswith("A")
        
        # Unknown type should get X prefix
        unknown_id = asset_id("Unknown", {"data": "test"})
        assert unknown_id.startswith("X")
    
    def test_asset_id_deterministic(self):
        """Test that asset IDs are deterministic based on payload"""
        payload = {"atoms": [{"el": "Si", "pos": [0, 0, 0]}]}
        
        # Same payload should generate same ID
        id1 = asset_id("System", payload)
        id2 = asset_id("System", payload)
        assert id1 == id2
        
        # Different payload should generate different ID
        payload2 = {"atoms": [{"el": "C", "pos": [0, 0, 0]}]}
        id3 = asset_id("System", payload2)
        assert id1 != id3
        
        # Different type with same payload should generate different ID
        id4 = asset_id("Results", payload)
        assert id1 != id4
        assert id4.startswith("R")
    
    def test_run_id(self):
        """Test run ID generation"""
        rid1 = run_id()
        assert rid1.startswith("R")
        assert len(rid1) == 9  # R + 8 hex chars
        
        # Should be unique
        rid2 = run_id()
        assert rid1 != rid2
        
        # Should be valid hex after R
        hex_part = rid1[1:]
        assert all(c in "0123456789abcdef" for c in hex_part)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])