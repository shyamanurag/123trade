"""
Configuration Loader
Handles loading and processing of configuration files with environment variable support
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from pydantic import BaseSettings, validator
import re

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Loads and processes configuration files with environment variable support"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_cache: Dict[str, Any] = {}
        self.env_pattern = re.compile(r'\${([^}]+)}')
        
    def load_config(self, config_path: str, env: str = "production") -> Dict[str, Any]:
        """Load configuration from file with environment variable support"""
        try:
            # Load base config
            base_config = self._load_yaml(config_path)
            
            # Load environment-specific config if exists
            env_config_path = self._get_env_config_path(config_path, env)
            if env_config_path.exists():
                env_config = self._load_yaml(env_config_path)
                base_config = self._merge_configs(base_config, env_config)
            
            # Process environment variables
            processed_config = self._process_env_vars(base_config)
            
            # Validate configuration
            self._validate_config(processed_config)
            
            return processed_config
        except Exception as e:
            logger.error(f"Error loading config {config_path}: {e}")
            raise
            
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file"""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading YAML file {path}: {e}")
            raise
            
    def _get_env_config_path(self, base_path: str, env: str) -> Path:
        """Get environment-specific config path"""
        base_path = Path(base_path)
        return base_path.parent / f"{base_path.stem}.{env}{base_path.suffix}"
        
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configurations, with override taking precedence"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def _process_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process environment variables in configuration"""
        if isinstance(config, dict):
            return {k: self._process_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._process_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._replace_env_vars(config)
        else:
            return config
            
    def _replace_env_vars(self, value: str) -> str:
        """Replace environment variables in string"""
        def replace(match):
            env_var = match.group(1)
            if env_var in os.environ:
                return os.environ[env_var]
            logger.warning(f"Environment variable {env_var} not found")
            return match.group(0)
            
        return self.env_pattern.sub(replace, value)
        
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration structure"""
        required_sections = ["app", "database", "redis", "logging"]
        missing_sections = [section for section in required_sections if section not in config]
        
        if missing_sections:
            raise ValueError(f"Missing required configuration sections: {', '.join(missing_sections)}")
            
    def get_value(self, config: Dict[str, Any], path: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation path"""
        try:
            current = config
            for key in path.split('.'):
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
            
    def set_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """Set configuration value by dot-notation path"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
            
        current[keys[-1]] = value
        
    def save_config(self, config: Dict[str, Any], path: str) -> None:
        """Save configuration to file"""
        try:
            with open(path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Error saving config to {path}: {e}")
            raise

# Initialize configuration loader
config_loader = ConfigLoader() 