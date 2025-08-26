"""Simple unit helpers for MCG"""
from typing import Dict, Any, Optional

# Common unit mappings
UNIT_MAP = {
    "length": "angstrom",
    "energy": "eV",
    "force": "eV/angstrom",
    "stress": "GPa",
    "temperature": "K",
    "time": "fs",
    "thermal_conductivity": "W/(m*K)",
    "frequency": "THz",
    "lifetime": "ps"
}

def add_units(value: Any, unit: str) -> Dict[str, Any]:
    """Add unit annotation to a value"""
    return {"value": value, "unit": unit}

def extract_value(unitful_value: Dict[str, Any]) -> Any:
    """Extract value from unitful dictionary"""
    if isinstance(unitful_value, dict) and "value" in unitful_value:
        return unitful_value["value"]
    return unitful_value

def get_unit(unitful_value: Dict[str, Any]) -> Optional[str]:
    """Get unit from unitful dictionary"""
    if isinstance(unitful_value, dict) and "unit" in unitful_value:
        return unitful_value["unit"]
    return None

def standardize_units(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add standard units to common parameter names"""
    unit_patterns = {
        "_K": "K",
        "_eV": "eV",
        "_fs": "fs",
        "_ps": "ps",
        "_ns": "ns",
        "_A": "angstrom",
        "_GPa": "GPa",
        "_THz": "THz",
        "_W_per_mK": "W/(m*K)"
    }
    
    result = {}
    for key, value in params.items():
        for pattern, unit in unit_patterns.items():
            if key.endswith(pattern):
                result[key] = {"value": value, "unit": unit}
                break
        else:
            result[key] = value
    
    return result