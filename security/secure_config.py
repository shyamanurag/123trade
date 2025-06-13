"""
Secure Configuration Manager
Handles encryption, decryption, and secure storage of sensitive configuration data
"""

import os
import base64
import logging
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class SecureConfigManager:
    """Manages secure configuration with encryption/decryption capabilities"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize SecureConfigManager.
        
        Args:
            master_key: Master encryption key. If None, will be loaded from environment.
        """
        self._master_key = master_key or os.environ.get("MASTER_ENCRYPTION_KEY")
        self._fernet = None
        if self._master_key:
            self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize Fernet encryption with the master key."""
        try:
            # Derive key from master key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'trading_system_salt',  # In production, use random salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))
            self._fernet = Fernet(key)
            logger.info("Encryption initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self._fernet = None
    
    def encrypt_value(self, value: str) -> str:
        """
        Encrypt a configuration value.
        
        Args:
            value: Plain text value to encrypt
            
        Returns:
            Encrypted value as base64 string
        """
        if not self._fernet:
            logger.warning("Encryption not available, returning plain value")
            return value
        
        try:
            encrypted = self._fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return value
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt a configuration value.
        
        Args:
            encrypted_value: Encrypted value as base64 string
            
        Returns:
            Decrypted plain text value
        """
        if not self._fernet:
            logger.warning("Encryption not available, returning encrypted value")
            return encrypted_value
        
        try:
            decoded = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self._fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_value
    
    def encrypt_config_dict(self, config: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
        """
        Encrypt specific fields in a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            fields_to_encrypt: List of field paths to encrypt (e.g., ['database.password', 'api.secret'])
            
        Returns:
            Configuration with encrypted fields
        """
        encrypted_config = config.copy()
        
        for field_path in fields_to_encrypt:
            try:
                # Navigate to nested field
                keys = field_path.split('.')
                current = encrypted_config
                
                # Navigate to parent
                for key in keys[:-1]:
                    if key in current and isinstance(current[key], dict):
                        current = current[key]
                    else:
                        break
                else:
                    # Encrypt the final field
                    final_key = keys[-1]
                    if final_key in current and isinstance(current[final_key], str):
                        current[final_key] = self.encrypt_value(current[final_key])
                        logger.info(f"Encrypted field: {field_path}")
                    else:
                        logger.warning(f"Field not found or not string: {field_path}")
                        
            except Exception as e:
                logger.error(f"Failed to encrypt field {field_path}: {e}")
        
        return encrypted_config
    
    def decrypt_config_dict(self, config: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
        """
        Decrypt specific fields in a configuration dictionary.
        
        Args:
            config: Configuration dictionary with encrypted fields
            fields_to_decrypt: List of field paths to decrypt
            
        Returns:
            Configuration with decrypted fields
        """
        decrypted_config = config.copy()
        
        for field_path in fields_to_decrypt:
            try:
                # Navigate to nested field
                keys = field_path.split('.')
                current = decrypted_config
                
                # Navigate to parent
                for key in keys[:-1]:
                    if key in current and isinstance(current[key], dict):
                        current = current[key]
                    else:
                        break
                else:
                    # Decrypt the final field
                    final_key = keys[-1]
                    if final_key in current and isinstance(current[final_key], str):
                        current[final_key] = self.decrypt_value(current[final_key])
                        logger.info(f"Decrypted field: {field_path}")
                    else:
                        logger.warning(f"Field not found or not string: {field_path}")
                        
            except Exception as e:
                logger.error(f"Failed to decrypt field {field_path}: {e}")
        
        return decrypted_config
    
    def get_sensitive_fields(self) -> list:
        """
        Get list of fields that should be encrypted in configuration.
        
        Returns:
            List of sensitive field paths
        """
        return [
            'database.password',
            'database.username',
            'security.jwt_secret_key',
            'security.encryption_key',
            'brokers.zerodha.api_key',
            'brokers.zerodha.api_secret',
            'brokers.upstox.api_key',
            'brokers.upstox.api_secret',
            'redis.password',
            'webhook.secret_key',
            'email.password',
            'sms.api_key',
            'cloud.access_key',
            'cloud.secret_key'
        ]
    
    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive data for logging purposes.
        
        Args:
            data: Data dictionary
            
        Returns:
            Data with sensitive fields masked
        """
        masked_data = data.copy()
        sensitive_keywords = [
            'password', 'secret', 'key', 'token', 'credential',
            'auth', 'pin', 'otp', 'private', 'access_token'
        ]
        
        def mask_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if any(keyword in key.lower() for keyword in sensitive_keywords):
                        obj[key] = "***MASKED***"
                    elif isinstance(value, (dict, list)):
                        mask_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        mask_recursive(item, f"{path}[{i}]")
        
        mask_recursive(masked_data)
        return masked_data
    
    def generate_master_key(self) -> str:
        """
        Generate a new master encryption key.
        
        Returns:
            Base64-encoded master key
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode()
    
    def validate_config_security(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration for security issues.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check for default/weak values
        if config.get('security', {}).get('jwt_secret_key') in [
            'development-secret', 'change-me', 'secret', 'jwt-secret'
        ]:
            issues.append("Weak JWT secret key detected")
        
        # Check password complexity (if available)
        db_password = config.get('database', {}).get('password', '')
        if len(db_password) < 8:
            warnings.append("Database password is too short")
        
        # Check if sensitive data is in plain text
        for field_path in self.get_sensitive_fields():
            try:
                keys = field_path.split('.')
                current = config
                for key in keys:
                    if key in current:
                        current = current[key]
                    else:
                        break
                else:
                    if isinstance(current, str) and len(current) < 50:
                        warnings.append(f"Field {field_path} may contain unencrypted sensitive data")
            except:
                pass
        
        return {
            'is_secure': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        } 