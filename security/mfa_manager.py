"""
Multi-Factor Authentication (MFA) Manager
Provides TOTP, SMS, and email-based 2FA for enhanced security
"""

import asyncio
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pyotp
import qrcode
import io
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import aiosmtplib
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class MFAConfig:
    """MFA configuration settings"""
    # TOTP settings
    totp_issuer: str = "Elite Trading System"
    totp_window: int = 1  # Allow 1 time step tolerance
    totp_interval: int = 30  # 30-second intervals
    
    # SMS settings (Twilio/AWS SNS)
    sms_provider: str = "twilio"  # "twilio", "aws_sns", "mock"
    sms_from_number: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@tradingsystem.com"
    
    # Backup codes
    backup_codes_count: int = 10
    backup_code_length: int = 8
    
    # Rate limiting
    max_attempts_per_hour: int = 5
    lockout_duration_minutes: int = 30

@dataclass
class MFAMethod:
    """MFA method configuration"""
    method_type: str  # "totp", "sms", "email"
    identifier: str  # phone number, email, or secret key
    is_verified: bool = False
    backup_codes: List[str] = None
    created_at: datetime = None
    last_used: datetime = None

class MFAManager:
    """Manages multi-factor authentication for users"""
    
    def __init__(self, config: MFAConfig, redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.rate_limit_prefix = "mfa_attempts"
        self.backup_codes_prefix = "backup_codes"
        
    async def setup_totp(self, user_id: str, user_email: str) -> Dict[str, str]:
        """Set up TOTP for a user"""
        try:
            # Generate secret key
            secret = pyotp.random_base32()
            
            # Create TOTP object
            totp = pyotp.TOTP(secret)
            
            # Generate provisioning URI for QR code
            provisioning_uri = totp.provisioning_uri(
                name=user_email,
                issuer_name=self.config.totp_issuer
            )
            
            # Generate QR code
            qr_code_data = await self._generate_qr_code(provisioning_uri)
            
            # Store secret temporarily (user must verify before it's permanent)
            await self.redis.setex(
                f"totp_setup:{user_id}",
                300,  # 5 minutes
                secret
            )
            
            return {
                "secret": secret,
                "qr_code": qr_code_data,
                "provisioning_uri": provisioning_uri,
                "backup_codes": await self._generate_backup_codes(user_id)
            }
            
        except Exception as e:
            logger.error(f"Error setting up TOTP for user {user_id}: {e}")
            raise
    
    async def verify_totp_setup(self, user_id: str, token: str) -> bool:
        """Verify TOTP setup with user-provided token"""
        try:
            # Get temporary secret
            secret = await self.redis.get(f"totp_setup:{user_id}")
            if not secret:
                return False
            
            secret = secret.decode()
            totp = pyotp.TOTP(secret)
            
            # Verify token
            if totp.verify(token, valid_window=self.config.totp_window):
                # Save permanent secret
                await self.redis.hset(
                    f"mfa:{user_id}",
                    mapping={
                        "totp_secret": secret,
                        "totp_verified": "true",
                        "setup_date": datetime.now().isoformat()
                    }
                )
                
                # Remove temporary secret
                await self.redis.delete(f"totp_setup:{user_id}")
                
                logger.info(f"TOTP setup completed for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying TOTP setup for user {user_id}: {e}")
            return False
    
    async def setup_sms(self, user_id: str, phone_number: str) -> bool:
        """Set up SMS-based MFA"""
        try:
            # Generate and send verification code
            verification_code = self._generate_numeric_code(6)
            
            # Store verification code
            await self.redis.setex(
                f"sms_setup:{user_id}",
                300,  # 5 minutes
                f"{phone_number}:{verification_code}"
            )
            
            # Send SMS
            success = await self._send_sms(phone_number, f"Your verification code is: {verification_code}")
            
            if success:
                logger.info(f"SMS verification sent to {phone_number} for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error setting up SMS for user {user_id}: {e}")
            return False
    
    async def verify_sms_setup(self, user_id: str, code: str) -> bool:
        """Verify SMS setup with user-provided code"""
        try:
            # Get stored data
            stored_data = await self.redis.get(f"sms_setup:{user_id}")
            if not stored_data:
                return False
            
            stored_data = stored_data.decode()
            phone_number, expected_code = stored_data.split(":", 1)
            
            if code == expected_code:
                # Save SMS configuration
                await self.redis.hset(
                    f"mfa:{user_id}",
                    mapping={
                        "sms_phone": phone_number,
                        "sms_verified": "true",
                        "setup_date": datetime.now().isoformat()
                    }
                )
                
                # Remove temporary data
                await self.redis.delete(f"sms_setup:{user_id}")
                
                logger.info(f"SMS MFA setup completed for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying SMS setup for user {user_id}: {e}")
            return False
    
    async def verify_mfa(self, user_id: str, token: str, method: str = "auto") -> bool:
        """Verify MFA token"""
        try:
            # Check rate limiting
            if not await self._check_rate_limit(user_id):
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return False
            
            # Get user MFA configuration
            mfa_config = await self.redis.hgetall(f"mfa:{user_id}")
            if not mfa_config:
                return False
            
            # Try TOTP verification
            if method in ["auto", "totp"] and mfa_config.get(b"totp_verified") == b"true":
                secret = mfa_config.get(b"totp_secret")
                if secret:
                    totp = pyotp.TOTP(secret.decode())
                    if totp.verify(token, valid_window=self.config.totp_window):
                        await self._record_successful_verification(user_id, "totp")
                        return True
            
            # Try backup code verification
            if await self._verify_backup_code(user_id, token):
                await self._record_successful_verification(user_id, "backup_code")
                return True
            
            # Record failed attempt
            await self._record_failed_attempt(user_id)
            return False
            
        except Exception as e:
            logger.error(f"Error verifying MFA for user {user_id}: {e}")
            return False
    
    async def generate_sms_code(self, user_id: str) -> bool:
        """Generate and send SMS verification code"""
        try:
            # Check rate limiting
            if not await self._check_rate_limit(user_id):
                return False
            
            # Get user SMS configuration
            mfa_config = await self.redis.hgetall(f"mfa:{user_id}")
            phone_number = mfa_config.get(b"sms_phone")
            
            if not phone_number or mfa_config.get(b"sms_verified") != b"true":
                return False
            
            phone_number = phone_number.decode()
            
            # Generate code
            code = self._generate_numeric_code(6)
            
            # Store code temporarily
            await self.redis.setex(
                f"sms_code:{user_id}",
                300,  # 5 minutes
                code
            )
            
            # Send SMS
            success = await self._send_sms(phone_number, f"Your login code is: {code}")
            
            if success:
                logger.info(f"SMS code sent to user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error generating SMS code for user {user_id}: {e}")
            return False
    
    async def _generate_backup_codes(self, user_id: str) -> List[str]:
        """Generate backup codes for user"""
        codes = []
        for _ in range(self.config.backup_codes_count):
            code = self._generate_alphanumeric_code(self.config.backup_code_length)
            codes.append(code)
        
        # Store backup codes
        await self.redis.sadd(f"{self.backup_codes_prefix}:{user_id}", *codes)
        
        return codes
    
    async def _verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify and consume backup code"""
        # Check if code exists
        is_valid = await self.redis.sismember(f"{self.backup_codes_prefix}:{user_id}", code)
        
        if is_valid:
            # Remove used code
            await self.redis.srem(f"{self.backup_codes_prefix}:{user_id}", code)
            logger.info(f"Backup code used for user {user_id}")
            return True
        
        return False
    
    async def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        key = f"{self.rate_limit_prefix}:{user_id}"
        current_time = int(time.time())
        hour_ago = current_time - 3600
        
        # Remove old attempts
        await self.redis.zremrangebyscore(key, 0, hour_ago)
        
        # Count recent attempts
        recent_attempts = await self.redis.zcard(key)
        
        if recent_attempts >= self.config.max_attempts_per_hour:
            return False
        
        return True
    
    async def _record_failed_attempt(self, user_id: str):
        """Record failed MFA attempt"""
        key = f"{self.rate_limit_prefix}:{user_id}"
        current_time = int(time.time())
        
        await self.redis.zadd(key, {str(current_time): current_time})
        await self.redis.expire(key, 3600)  # Expire after 1 hour
    
    async def _record_successful_verification(self, user_id: str, method: str):
        """Record successful MFA verification"""
        await self.redis.hset(
            f"mfa:{user_id}",
            "last_verified",
            datetime.now().isoformat()
        )
        
        logger.info(f"Successful MFA verification for user {user_id} using {method}")
    
    async def _generate_qr_code(self, data: str) -> str:
        """Generate QR code as base64 image"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def _generate_numeric_code(self, length: int) -> str:
        """Generate numeric verification code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def _generate_alphanumeric_code(self, length: int) -> str:
        """Generate alphanumeric code"""
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def _send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message"""
        try:
            if self.config.sms_provider == "mock":
                # Mock SMS for development
                logger.info(f"Mock SMS to {phone_number}: {message}")
                return True
            elif self.config.sms_provider == "twilio":
                # Twilio implementation would go here
                logger.info(f"Would send SMS via Twilio to {phone_number}")
                return True
            else:
                logger.warning(f"Unknown SMS provider: {self.config.sms_provider}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
    
    async def get_user_mfa_status(self, user_id: str) -> Dict[str, any]:
        """Get user's MFA configuration status"""
        try:
            mfa_config = await self.redis.hgetall(f"mfa:{user_id}")
            backup_codes_count = await self.redis.scard(f"{self.backup_codes_prefix}:{user_id}")
            
            return {
                "totp_enabled": mfa_config.get(b"totp_verified") == b"true",
                "sms_enabled": mfa_config.get(b"sms_verified") == b"true",
                "backup_codes_remaining": backup_codes_count,
                "last_verified": mfa_config.get(b"last_verified", b"").decode() if mfa_config.get(b"last_verified") else None
            }
            
        except Exception as e:
            logger.error(f"Error getting MFA status for user {user_id}: {e}")
            return {}
    
    async def disable_mfa(self, user_id: str, method: str = "all") -> bool:
        """Disable MFA for user"""
        try:
            if method == "all":
                # Remove all MFA data
                await self.redis.delete(f"mfa:{user_id}")
                await self.redis.delete(f"{self.backup_codes_prefix}:{user_id}")
                await self.redis.delete(f"{self.rate_limit_prefix}:{user_id}")
            elif method == "totp":
                await self.redis.hdel(f"mfa:{user_id}", "totp_secret", "totp_verified")
            elif method == "sms":
                await self.redis.hdel(f"mfa:{user_id}", "sms_phone", "sms_verified")
            
            logger.info(f"MFA disabled for user {user_id}, method: {method}")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling MFA for user {user_id}: {e}")
            return False

# Global MFA manager instance
mfa_manager: Optional[MFAManager] = None

def get_mfa_manager() -> Optional[MFAManager]:
    """Get the global MFA manager instance"""
    return mfa_manager

async def init_mfa_manager(config: MFAConfig, redis_client: redis.Redis) -> MFAManager:
    """Initialize the global MFA manager"""
    global mfa_manager
    
    mfa_manager = MFAManager(config, redis_client)
    logger.info("✅ MFA manager initialized successfully")
    return mfa_manager 