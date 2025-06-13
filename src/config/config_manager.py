"""
Configuration Manager
Handles loading and managing all configuration files in a unified way
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from pydantic import BaseSettings, validator
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages all configuration files and settings"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_cache: Dict[str, Any] = {}
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self, redis_url: str) -> None:
        """Initialize configuration manager with Redis connection"""
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            await self.load_all_configs()
        except Exception as e:
            logger.error(f"Error initializing config manager: {e}")
            raise
            
    async def load_all_configs(self) -> None:
        """Load all configuration files"""
        try:
            # Load main config
            main_config = await self.load_config("config.yaml")
            self.config_cache["main"] = main_config
            
            # Load trading system config
            trading_config = await self.load_config("trading-system/config.yaml")
            self.config_cache["trading"] = trading_config
            
            # Load monitoring config
            monitoring_config = await self.load_config("monitoring/prometheus.yml")
            self.config_cache["monitoring"] = monitoring_config
            
            # Load security config
            security_config = await self.load_config("security/config.yaml")
            self.config_cache["security"] = security_config
            
            # Store in Redis for service access
            if self.redis_client:
                for name, config in self.config_cache.items():
                    await self.redis_client.set(
                        f"config:{name}",
                        json.dumps(config)
                    )
                    
            logger.info("All configurations loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            raise
            
    async def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            full_path = self.config_dir / config_path
            if not full_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
                
            with open(full_path, 'r') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    return yaml.safe_load(f)
                elif config_path.endswith('.json'):
                    return json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path}")
        except Exception as e:
            logger.error(f"Error loading config {config_path}: {e}")
            raise
            
    async def get_config(self, name: str) -> Dict[str, Any]:
        """Get configuration by name"""
        if name in self.config_cache:
            return self.config_cache[name]
            
        # Try to load from Redis
        if self.redis_client:
            config_str = await self.redis_client.get(f"config:{name}")
            if config_str:
                return json.loads(config_str)
                
        raise KeyError(f"Configuration not found: {name}")
        
    async def update_config(self, name: str, config: Dict[str, Any]) -> None:
        """Update configuration"""
        try:
            # Update cache
            self.config_cache[name] = config
            
            # Update Redis
            if self.redis_client:
                await self.redis_client.set(
                    f"config:{name}",
                    json.dumps(config)
                )
                
            # Update file
            config_path = self.config_dir / f"{name}.yaml"
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
                
            logger.info(f"Configuration {name} updated successfully")
        except Exception as e:
            logger.error(f"Error updating config {name}: {e}")
            raise
            
    async def validate_config(self, name: str) -> bool:
        """Validate configuration"""
        try:
            config = await self.get_config(name)
            
            # Basic validation
            if not isinstance(config, dict):
                return False
                
            # Service-specific validation
            if name == "main":
                return self._validate_main_config(config)
            elif name == "trading":
                return self._validate_trading_config(config)
            elif name == "monitoring":
                return self._validate_monitoring_config(config)
            elif name == "security":
                return self._validate_security_config(config)
                
            return True
        except Exception as e:
            logger.error(f"Error validating config {name}: {e}")
            return False
            
    def _validate_main_config(self, config: Dict[str, Any]) -> bool:
        """Validate main configuration"""
        required_keys = ["app", "database", "redis", "logging"]
        return all(key in config for key in required_keys)
        
    def _validate_trading_config(self, config: Dict[str, Any]) -> bool:
        """Validate trading configuration"""
        required_keys = ["broker", "strategies", "risk", "execution"]
        return all(key in config for key in required_keys)
        
    def _validate_monitoring_config(self, config: Dict[str, Any]) -> bool:
        """Validate monitoring configuration"""
        required_keys = ["prometheus", "grafana", "alerts"]
        return all(key in config for key in required_keys)
        
    def _validate_security_config(self, config: Dict[str, Any]) -> bool:
        """Validate security configuration"""
        required_keys = ["auth", "encryption", "rate_limiting"]
        return all(key in config for key in required_keys)
        
    async def watch_config_changes(self) -> None:
        """Watch for configuration changes"""
        if not self.redis_client:
            return
            
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("config:changes")
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    config_name = message["data"]
                    await self.load_config(f"{config_name}.yaml")
                    logger.info(f"Configuration {config_name} reloaded")
        except Exception as e:
            logger.error(f"Error watching config changes: {e}")
            raise
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

# Initialize configuration manager
config_manager = ConfigManager() 