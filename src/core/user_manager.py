"""
User Management System
Handles user registration, authentication, and API key management
"""

import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import jwt
import bcrypt
import redis.asyncio as redis
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class User:
    """User data structure"""
    user_id: str
    username: str
    email: str
    created_at: datetime
    last_login: datetime
    is_active: bool
    preferences: Dict
    api_keys: Dict[str, str]  # broker -> api_key mapping

class UserManager:
    """Manages users and their API keys"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.redis = redis.from_url(config['redis_url'])
        self.jwt_secret = config['jwt_secret']
        self.token_expiry = timedelta(days=1)
        
    async def register_user(self, username: str, email: str, password: str) -> Optional[User]:
        """Register a new user"""
        try:
            # Check if user exists
            if await self.redis.hexists('users:by_username', username):
                logger.warning(f"Username {username} already exists")
                return None
                
            # Create user
            user_id = f"user_{datetime.now().timestamp()}"
            hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                created_at=datetime.now(),
                last_login=datetime.now(),
                is_active=True,
                preferences={},
                api_keys={}
            )
            
            # Store user data
            await self.redis.hset('users:by_username', username, user_id)
            await self.redis.hset('users:by_email', email, user_id)
            await self.redis.hset(f'users:{user_id}', mapping={
                'username': username,
                'email': email,
                'password': hashed_password.decode(),
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat(),
                'is_active': str(user.is_active),
                'preferences': '{}',
                'api_keys': '{}'
            })
            
            logger.info(f"User registered: {username}")
            return user
            
        except Exception as e:
            logger.error(f"User registration failed: {e}")
            return None
            
    async def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return JWT token"""
        try:
            # Get user ID
            user_id = await self.redis.hget('users:by_username', username)
            if not user_id:
                return None
                
            # Get user data
            user_data = await self.redis.hgetall(f'users:{user_id}')
            if not user_data:
                return None
                
            # Verify password
            stored_password = user_data['password'].encode()
            if not bcrypt.checkpw(password.encode(), stored_password):
                return None
                
            # Update last login
            await self.redis.hset(f'users:{user_id}', 'last_login', datetime.now().isoformat())
            
            # Generate JWT token
            token = jwt.encode({
                'user_id': user_id,
                'username': username,
                'exp': datetime.utcnow() + self.token_expiry
            }, self.jwt_secret, algorithm='HS256')
            
            return token
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
            
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            user_data = await self.redis.hgetall(f'users:{user_id}')
            if not user_data:
                return None
                
            return User(
                user_id=user_id,
                username=user_data['username'],
                email=user_data['email'],
                created_at=datetime.fromisoformat(user_data['created_at']),
                last_login=datetime.fromisoformat(user_data['last_login']),
                is_active=user_data['is_active'] == 'True',
                preferences=eval(user_data['preferences']),
                api_keys=eval(user_data['api_keys'])
            )
            
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
            
    async def update_user_api_key(self, user_id: str, broker: str, api_key: str, api_secret: str) -> bool:
        """Update user's API key for a broker"""
        try:
            # Get current API keys
            api_keys = eval(await self.redis.hget(f'users:{user_id}', 'api_keys') or '{}')
            
            # Update API key
            api_keys[broker] = {
                'api_key': api_key,
                'api_secret': api_secret,
                'updated_at': datetime.now().isoformat()
            }
            
            # Store updated keys
            await self.redis.hset(f'users:{user_id}', 'api_keys', str(api_keys))
            
            logger.info(f"Updated API key for user {user_id} and broker {broker}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update API key: {e}")
            return False
            
    async def get_user_api_key(self, user_id: str, broker: str) -> Optional[Dict]:
        """Get user's API key for a broker"""
        try:
            api_keys = eval(await self.redis.hget(f'users:{user_id}', 'api_keys') or '{}')
            return api_keys.get(broker)
            
        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            return None
            
    async def update_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """Update user preferences"""
        try:
            await self.redis.hset(f'users:{user_id}', 'preferences', str(preferences))
            return True
            
        except Exception as e:
            logger.error(f"Failed to update preferences: {e}")
            return False
            
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account"""
        try:
            await self.redis.hset(f'users:{user_id}', 'is_active', 'False')
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate user: {e}")
            return False
            
    async def list_users(self) -> List[User]:
        """List all users"""
        try:
            users = []
            async for user_id in self.redis.scan_iter('users:*'):
                if ':' in user_id:  # Skip username/email mappings
                    continue
                user = await self.get_user(user_id)
                if user:
                    users.append(user)
            return users
            
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return [] 