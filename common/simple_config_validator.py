#!/usr/bin/env python3
"""
Simple configuration validator for the trading system.
Validates YAML configuration files for basic syntax and required fields.
"""

import sys
import os
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, List

def validate_yaml_syntax(file_path: str) -> bool:
    """Validate YAML file syntax."""
    try:
        with open(file_path, 'r') as file:
            yaml.safe_load(file)
        print(f"✓ YAML syntax valid: {file_path}")
        return True
    except yaml.YAMLError as e:
        print(f"✗ YAML syntax error in {file_path}: {e}")
        return False
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
        return False

def validate_required_fields(config: Dict[str, Any], required_fields: List[str]) -> bool:
    """Validate that required fields are present in config."""
    missing_fields = []
    
    for field in required_fields:
        if '.' in field:
            # Handle nested fields
            keys = field.split('.')
            current = config
            try:
                for key in keys:
                    current = current[key]
            except (KeyError, TypeError):
                missing_fields.append(field)
        else:
            if field not in config:
                missing_fields.append(field)
    
    if missing_fields:
        print(f"✗ Missing required fields: {', '.join(missing_fields)}")
        return False
    
    print("✓ All required fields present")
    return True

def validate_config_file(file_path: str) -> bool:
    """Validate a single configuration file."""
    print(f"\nValidating: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"✗ Configuration file not found: {file_path}")
        return False
    
    # Validate YAML syntax
    if not validate_yaml_syntax(file_path):
        return False
    
    # Load and validate content
    try:
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
        
        if not isinstance(config, dict):
            print(f"✗ Configuration must be a dictionary/object")
            return False
        
        # Define required fields based on environment
        required_fields = [
            'environment',
            'database.host',
            'database.port', 
            'redis.host',
            'redis.port',
            'security.jwt_algorithm',
            'trading.max_daily_trades',
            'monitoring.log_level'
        ]
        
        # Validate required fields
        if not validate_required_fields(config, required_fields):
            return False
        
        # Validate specific values
        valid_environments = ['development', 'test', 'staging', 'production']
        if config.get('environment') not in valid_environments:
            print(f"✗ Invalid environment: {config.get('environment')}. Must be one of: {valid_environments}")
            return False
        
        print(f"✓ Configuration valid for environment: {config.get('environment')}")
        return True
        
    except Exception as e:
        print(f"✗ Error validating config: {e}")
        return False

def validate_all_configs() -> bool:
    """Validate all configuration files."""
    config_dir = Path("config")
    
    if not config_dir.exists():
        print(f"✗ Config directory not found: {config_dir}")
        return False
    
    config_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))
    
    if not config_files:
        print(f"✗ No configuration files found in {config_dir}")
        return False
    
    all_valid = True
    for config_file in config_files:
        if not validate_config_file(str(config_file)):
            all_valid = False
    
    return all_valid

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate trading system configuration files")
    parser.add_argument('action', choices=['validate'], help='Action to perform')
    parser.add_argument('--file', help='Specific config file to validate')
    
    args = parser.parse_args()
    
    if args.action == 'validate':
        if args.file:
            success = validate_config_file(args.file)
        else:
            success = validate_all_configs()
        
        if success:
            print("\n✓ All configurations are valid!")
            sys.exit(0)
        else:
            print("\n✗ Configuration validation failed!")
            sys.exit(1)

if __name__ == "__main__":
    main() 