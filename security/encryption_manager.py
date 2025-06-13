"""
Data Encryption Manager
Provides AES-256 encryption, key rotation, and field-level encryption for sensitive data
"""

import asyncio
import logging
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import redis.asyncio as redis
import json

logger = logging.getLogger(__name__)

@dataclass
class EncryptionConfig:
    """Encryption configuration settings"""
    # Master key settings
    master_key_length: int = 32  # 256 bits
    key_derivation_iterations: int = 100000
    salt_length: int = 16
    
    # Key rotation settings
    key_rotation_days: int = 90
    max_key_versions: int = 5
    
    # Field encryption settings
    sensitive_fields: Optional[List[str]] = None
    
    # Storage settings
    encrypted_storage_prefix: str = "encrypted"
    key_storage_prefix: str = "encryption_keys"
    
    def __post_init__(self):
        if self.sensitive_fields is None:
            self.sensitive_fields = [
                'password', 'password_hash', 'ssn', 'credit_card',
                'bank_account', 'api_key', 'secret', 'token',
                'phone', 'email', 'address', 'zerodha_client_id'
            ]

@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    version: int
    algorithm: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    key_data: bytes

class EncryptionManager:
    """Manages data encryption and key rotation"""
    
    def __init__(self, config: EncryptionConfig, redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.backend = default_backend()
        self.current_key: Optional[EncryptionKey] = None
        self.key_cache: Dict[str, EncryptionKey] = {}
        
    async def initialize(self) -> bool:
        """Initialize encryption manager"""
        try:
            # Load or create master key
            await self._load_or_create_master_key()
            
            # Load existing keys
            await self._load_encryption_keys()
            
            # Check if key rotation is needed
            await self._check_key_rotation()
            
            logger.info("✅ Encryption manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Encryption manager initialization failed: {e}")
            return False
    
    async def encrypt_data(self, data: Union[str, bytes], key_id: Optional[str] = None) -> Dict[str, str]:
        """Encrypt data with specified or current key"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Use specified key or current active key
            encryption_key = self.key_cache.get(key_id) if key_id else self.current_key
            if not encryption_key:
                raise ValueError("No encryption key available")
            
            # Create Fernet cipher
            fernet = Fernet(base64.urlsafe_b64encode(encryption_key.key_data))
            
            # Encrypt data
            encrypted_data = fernet.encrypt(data)
            
            return {
                "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8'),
                "key_id": encryption_key.key_id,
                "algorithm": encryption_key.algorithm,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise
    
    async def decrypt_data(self, encrypted_payload: Dict[str, str]) -> bytes:
        """Decrypt data using the specified key"""
        try:
            key_id = encrypted_payload.get("key_id")
            encrypted_data = encrypted_payload.get("encrypted_data")
            
            if not key_id or not encrypted_data:
                raise ValueError("Invalid encrypted payload")
            
            # Get decryption key
            encryption_key = self.key_cache.get(key_id)
            if not encryption_key:
                # Try to load key from storage
                encryption_key = await self._load_key_by_id(key_id)
                if not encryption_key:
                    raise ValueError(f"Encryption key {key_id} not found")
            
            # Create Fernet cipher
            fernet = Fernet(base64.urlsafe_b64encode(encryption_key.key_data))
            
            # Decrypt data
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = fernet.decrypt(encrypted_bytes)
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
    
    async def encrypt_field(self, field_name: str, value: Any) -> Union[str, Any]:
        """Encrypt a specific field if it's marked as sensitive"""
        try:
            if self.config.sensitive_fields and field_name.lower() in [f.lower() for f in self.config.sensitive_fields]:
                if value is None:
                    return None
                
                # Convert value to string for encryption
                str_value = str(value)
                encrypted_payload = await self.encrypt_data(str_value)
                
                # Return as JSON string with encryption metadata
                return json.dumps(encrypted_payload)
            
            # Return original value if not sensitive
            return value
            
        except Exception as e:
            logger.error(f"Error encrypting field {field_name}: {e}")
            return value
    
    async def decrypt_field(self, field_name: str, value: Any) -> Any:
        """Decrypt a specific field if it's encrypted"""
        try:
            if not isinstance(value, str):
                return value
            
            # Check if value looks like encrypted JSON
            if value.startswith('{"encrypted_data"'):
                try:
                    encrypted_payload = json.loads(value)
                    decrypted_bytes = await self.decrypt_data(encrypted_payload)
                    return decrypted_bytes.decode('utf-8')
                except (json.JSONDecodeError, ValueError):
                    # Not encrypted, return as-is
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Error decrypting field {field_name}: {e}")
            return value
    
    async def encrypt_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in a record"""
        encrypted_record = {}
        
        for field_name, value in record.items():
            encrypted_record[field_name] = await self.encrypt_field(field_name, value)
        
        return encrypted_record
    
    async def decrypt_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in a record"""
        decrypted_record = {}
        
        for field_name, value in record.items():
            decrypted_record[field_name] = await self.decrypt_field(field_name, value)
        
        return decrypted_record
    
    async def rotate_keys(self) -> bool:
        """Rotate encryption keys"""
        try:
            logger.info("Starting key rotation...")
            
            # Create new key
            new_key = await self._generate_new_key()
            
            # Store new key
            await self._store_encryption_key(new_key)
            
            # Update current key
            self.current_key = new_key
            self.key_cache[new_key.key_id] = new_key
            
            # Mark old keys as inactive (but keep for decryption)
            await self._deactivate_old_keys()
            
            # Clean up expired keys
            await self._cleanup_expired_keys()
            
            logger.info(f"✅ Key rotation completed. New key ID: {new_key.key_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Key rotation failed: {e}")
            return False
    
    async def _load_or_create_master_key(self):
        """Load existing master key or create new one"""
        try:
            # Try to load existing master key
            master_key_data = await self.redis.get("master_encryption_key")
            
            if master_key_data:
                logger.info("Loaded existing master key")
                return
            
            # Create new master key
            master_key = secrets.token_bytes(self.config.master_key_length)
            
            # Store master key (in production, this should be in a secure key vault)
            await self.redis.set("master_encryption_key", base64.b64encode(master_key))
            
            logger.info("✅ Created new master encryption key")
            
        except Exception as e:
            logger.error(f"Error with master key: {e}")
            raise
    
    async def _generate_new_key(self) -> EncryptionKey:
        """Generate a new encryption key"""
        try:
            # Generate key ID
            key_id = f"key_{int(datetime.now().timestamp())}_{secrets.token_hex(8)}"
            
            # Get current version number
            version = await self._get_next_key_version()
            
            # Generate key data
            key_data = Fernet.generate_key()
            
            # Create key object
            encryption_key = EncryptionKey(
                key_id=key_id,
                version=version,
                algorithm="Fernet-AES256",
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=self.config.key_rotation_days * 2),
                is_active=True,
                key_data=base64.urlsafe_b64decode(key_data)
            )
            
            return encryption_key
            
        except Exception as e:
            logger.error(f"Error generating new key: {e}")
            raise
    
    async def _store_encryption_key(self, key: EncryptionKey):
        """Store encryption key in Redis"""
        try:
            key_data = {
                "key_id": key.key_id,
                "version": str(key.version),
                "algorithm": key.algorithm,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "is_active": str(key.is_active),
                "key_data": base64.b64encode(key.key_data).decode('utf-8')
            }
            
            # Store key
            await self.redis.hset(
                f"{self.config.key_storage_prefix}:{key.key_id}",
                mapping=key_data
            )
            
            # Update active key reference
            if key.is_active:
                await self.redis.set("active_encryption_key", key.key_id)
            
            logger.info(f"Stored encryption key: {key.key_id}")
            
        except Exception as e:
            logger.error(f"Error storing encryption key: {e}")
            raise
    
    async def _load_encryption_keys(self):
        """Load all encryption keys from storage"""
        try:
            # Get all key IDs
            key_pattern = f"{self.config.key_storage_prefix}:*"
            key_keys = await self.redis.keys(key_pattern)
            
            for key_key in key_keys:
                key_data = await self.redis.hgetall(key_key)
                if key_data:
                    encryption_key = self._deserialize_key(key_data)
                    self.key_cache[encryption_key.key_id] = encryption_key
                    
                    if encryption_key.is_active:
                        self.current_key = encryption_key
            
            # If no active key found, create one
            if not self.current_key:
                new_key = await self._generate_new_key()
                await self._store_encryption_key(new_key)
                self.current_key = new_key
                self.key_cache[new_key.key_id] = new_key
            
            logger.info(f"Loaded {len(self.key_cache)} encryption keys")
            
        except Exception as e:
            logger.error(f"Error loading encryption keys: {e}")
            raise
    
    async def _load_key_by_id(self, key_id: str) -> Optional[EncryptionKey]:
        """Load a specific key by ID"""
        try:
            key_data = await self.redis.hgetall(f"{self.config.key_storage_prefix}:{key_id}")
            if key_data:
                encryption_key = self._deserialize_key(key_data)
                self.key_cache[key_id] = encryption_key
                return encryption_key
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading key {key_id}: {e}")
            return None
    
    def _deserialize_key(self, key_data: Dict) -> EncryptionKey:
        """Deserialize key data from Redis"""
        return EncryptionKey(
            key_id=key_data[b"key_id"].decode(),
            version=int(key_data[b"version"]),
            algorithm=key_data[b"algorithm"].decode(),
            created_at=datetime.fromisoformat(key_data[b"created_at"].decode()),
            expires_at=datetime.fromisoformat(key_data[b"expires_at"].decode()) if key_data.get(b"expires_at") else None,
            is_active=key_data[b"is_active"].decode().lower() == "true",
            key_data=base64.b64decode(key_data[b"key_data"])
        )
    
    async def _get_next_key_version(self) -> int:
        """Get the next key version number"""
        try:
            # Get current max version
            max_version = 0
            for key in self.key_cache.values():
                if key.version > max_version:
                    max_version = key.version
            
            return max_version + 1
            
        except Exception as e:
            logger.error(f"Error getting next key version: {e}")
            return 1
    
    async def _check_key_rotation(self):
        """Check if key rotation is needed"""
        try:
            if not self.current_key:
                return
            
            # Check if current key is old enough for rotation
            age = datetime.now() - self.current_key.created_at
            if age.days >= self.config.key_rotation_days:
                logger.info("Key rotation needed due to age")
                await self.rotate_keys()
            
        except Exception as e:
            logger.error(f"Error checking key rotation: {e}")
    
    async def _deactivate_old_keys(self):
        """Deactivate old keys but keep them for decryption"""
        try:
            for key in self.key_cache.values():
                if key.key_id != self.current_key.key_id and key.is_active:
                    key.is_active = False
                    await self._store_encryption_key(key)
            
        except Exception as e:
            logger.error(f"Error deactivating old keys: {e}")
    
    async def _cleanup_expired_keys(self):
        """Remove expired keys"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key_id, key in self.key_cache.items():
                if key.expires_at and current_time > key.expires_at:
                    expired_keys.append(key_id)
            
            # Keep at least one key for decryption
            if len(self.key_cache) - len(expired_keys) >= 1:
                for key_id in expired_keys:
                    await self.redis.delete(f"{self.config.key_storage_prefix}:{key_id}")
                    del self.key_cache[key_id]
                    logger.info(f"Removed expired key: {key_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up expired keys: {e}")
    
    async def get_encryption_status(self) -> Dict[str, Any]:
        """Get encryption system status"""
        try:
            active_keys = sum(1 for key in self.key_cache.values() if key.is_active)
            total_keys = len(self.key_cache)
            
            current_key_age = None
            current_key_id = None
            if self.current_key:
                current_key_age = (datetime.now() - self.current_key.created_at).days
                current_key_id = self.current_key.key_id
            
            return {
                "encryption_enabled": True,
                "active_keys": active_keys,
                "total_keys": total_keys,
                "current_key_id": current_key_id,
                "current_key_age_days": current_key_age,
                "key_rotation_due": current_key_age >= self.config.key_rotation_days if current_key_age else False,
                "sensitive_fields": self.config.sensitive_fields or []
            }
            
        except Exception as e:
            logger.error(f"Error getting encryption status: {e}")
            return {"encryption_enabled": False, "error": str(e)}

# Global encryption manager instance
encryption_manager: Optional[EncryptionManager] = None

def get_encryption_manager() -> Optional[EncryptionManager]:
    """Get the global encryption manager instance"""
    return encryption_manager

async def init_encryption_manager(config: EncryptionConfig, redis_client: redis.Redis) -> EncryptionManager:
    """Initialize the global encryption manager"""
    global encryption_manager
    
    encryption_manager = EncryptionManager(config, redis_client)
    
    if await encryption_manager.initialize():
        logger.info("✅ Encryption manager initialized successfully")
        return encryption_manager
    else:
        raise RuntimeError("Failed to initialize encryption manager") 