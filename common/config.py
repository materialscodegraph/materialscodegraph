"""Configuration management for MaterialsCodeGraph

This module provides a centralized configuration system for all computational codes.
Configuration is loaded from config.json in the repository root.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Singleton configuration manager"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from JSON file"""
        # Look for config.json in multiple locations
        config_paths = [
            Path("config.json"),  # Current directory
            Path(__file__).parent.parent / "config.json",  # Repository root
            Path(os.environ.get("MCG_CONFIG_PATH", "")),  # Environment variable
            Path.home() / ".mcg" / "config.json",  # User home
        ]
        
        for config_path in config_paths:
            if config_path and config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        self._config = json.load(f)
                        logger.info(f"Loaded configuration from {config_path}")
                        self._config_path = config_path
                        self._apply_environment_overrides()
                        return
                except Exception as e:
                    logger.error(f"Failed to load config from {config_path}: {e}")
        
        # If no config found, use defaults
        logger.warning("No config.json found, using defaults")
        self._config = self._get_default_config()
        self._config_path = None
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        # Generic storage path override
        if "MCG_STORAGE_PATH" in os.environ:
            self._config["storage"]["base_path"] = os.environ["MCG_STORAGE_PATH"]
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return minimal default configuration"""
        return {
            "codes": {},
            "storage": {
                "base_path": "/tmp/mcg/data"
            },
            "logging": {
                "level": "INFO"
            }
        }
    
    def get_code_config(self, code: str) -> Dict[str, Any]:
        """Get configuration for a specific code"""
        if not self._config:
            self._load_config()
        
        code_config = self._config.get("codes", {}).get(code, {})
        if not code_config:
            raise ValueError(f"No configuration found for code: {code}")
        
        if not code_config.get("enabled", False):
            raise ValueError(f"Code {code} is disabled in configuration")
        
        return code_config
    
    
    def get_execution_mode(self, code: str) -> str:
        """Get execution mode for a code (docker, local, hpc)"""
        code_config = self.get_code_config(code)
        mode = code_config.get("execution", {}).get("mode")
        if not mode:
            raise ValueError(
                f"No execution mode configured for {code}. "
                f"Please set mode to 'local', 'docker', or 'hpc' in config.json"
            )
        return mode
    
    def get_storage_path(self) -> Path:
        """Get base storage path"""
        if not self._config:
            self._load_config()
        return Path(self._config.get("storage", {}).get("base_path", "/tmp/mcg/data"))
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation path
        
        Example:
            config.get("codes.lammps.defaults.timestep_fs", 1.0)
        """
        if not self._config:
            self._load_config()
        
        keys = key_path.split(".")
        value = self._config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def reload(self):
        """Reload configuration from file"""
        self._config = None
        self._load_config()
    
    @property
    def config_path(self) -> Optional[Path]:
        """Get path to loaded configuration file"""
        return self._config_path
    
    def save(self, path: Optional[Path] = None):
        """Save current configuration to file"""
        save_path = path or self._config_path
        if not save_path:
            save_path = Path("config.json")
        
        with open(save_path, 'w') as f:
            json.dump(self._config, f, indent=2)
        logger.info(f"Saved configuration to {save_path}")


# Convenience function for getting config instance
def get_config() -> Config:
    """Get the singleton Config instance"""
    return Config()


# Generic convenience functions for any code
def get_code_executable(code: str) -> str:
    """Get executable path for any code based on execution mode"""
    config = get_config()
    code_config = config.get_code_config(code)
    mode = code_config["execution"]["mode"]

    if mode == "docker":
        return code_config["execution"]["docker"]["command"]
    elif mode == "local":
        return code_config["execution"]["local"]["executable"]
    elif mode == "hpc":
        return code_config["execution"]["hpc"]["executable"]
    else:
        raise ValueError(f"Unknown execution mode: {mode}")


def get_code_defaults(code: str) -> Dict[str, Any]:
    """Get default parameters for any code"""
    config = get_config()
    return config.get(f"codes.{code}.defaults", {})