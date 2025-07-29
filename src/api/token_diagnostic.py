"""
ShareKhan Token Diagnostic API
Comprehensive token debugging and repair functionality
"""

import os
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import redis.asyncio as redis
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/token-diagnostic", tags=["token-diagnostic"])

class TokenRepairRequest(BaseModel):
    action: str  # "repair", "migrate", "cleanup"
    source_user_id: Optional[str] = None
    target_user_id: Optional[str] = None

async def get_redis_client():
    """Get Redis client with proper SSL configuration"""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # Parse Redis URL for connection details
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        
        config = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 6379,
            'password': parsed.password,
            'db': int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
            'decode_responses': True,
            'socket_timeout': 10,
            'socket_connect_timeout': 10,
            'retry_on_timeout': True,
            'health_check_interval': 30
        }
        
        # Add SSL configuration for DigitalOcean
        if 'ondigitalocean.com' in redis_url or redis_url.startswith('rediss://'):
            config.update({
                'ssl': True,
                'ssl_cert_reqs': None,
                'ssl_check_hostname': False
            })
        
        client = redis.Redis(**config)
        await client.ping()  # Test connection
        return client
        
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return None

@router.get("/status")
async def get_token_diagnostic_status():
    """Comprehensive token diagnostic status"""
    try:
        client = await get_redis_client()
        if not client:
            return JSONResponse(content={
                "success": False,
                "error": "Redis connection failed",
                "redis_connected": False
            })
        
        # Get environment variables
        env_user_id = os.getenv('SHAREKHAN_USER_ID', 'NOT_SET')
        env_api_key = os.getenv('SHAREKHAN_API_KEY', 'NOT_SET')
        env_access_token = os.getenv('SHAREKHAN_ACCESS_TOKEN', 'NOT_SET')
        
        # Search for all sharekhan tokens
        all_token_keys = await client.keys("sharekhan:token:*")
        all_expiry_keys = await client.keys("sharekhan:token_expiry:*")
        
        tokens_found = {}
        for key in all_token_keys:
            try:
                key_str = key.decode() if isinstance(key, bytes) else key
                token = await client.get(key)
                if token:
                    tokens_found[key_str] = {
                        'token_preview': token[:15] + '...' if len(token) > 15 else token,
                        'token_length': len(token),
                        'user_id': key_str.replace('sharekhan:token:', '')
                    }
            except Exception as e:
                tokens_found[key_str] = {'error': str(e)}
        
        # Check expiry times
        expiry_info = {}
        for key in all_expiry_keys:
            try:
                key_str = key.decode() if isinstance(key, bytes) else key
                expiry_time = await client.get(key)
                if expiry_time:
                    try:
                        expiry_dt = datetime.fromisoformat(expiry_time)
                        is_expired = expiry_dt <= datetime.now()
                        expiry_info[key_str] = {
                            'expiry_time': expiry_time,
                            'is_expired': is_expired,
                            'time_remaining': str(expiry_dt - datetime.now()) if not is_expired else 'EXPIRED'
                        }
                    except Exception as parse_error:
                        expiry_info[key_str] = {'error': f'Parse error: {parse_error}'}
            except Exception as e:
                expiry_info[key_str] = {'error': str(e)}
        
        # Check orchestrator expected keys
        orchestrator_keys = [
            f"sharekhan:token:{env_user_id}",
            "sharekhan:token:PAPER_TRADER_001",
            "sharekhan:token:QSW899",
            "sharekhan:token:PAPER_TRADER_MAIN"
        ]
        
        orchestrator_tokens = {}
        for key in orchestrator_keys:
            try:
                token = await client.get(key)
                orchestrator_tokens[key] = {
                    'exists': token is not None,
                    'token_preview': token[:15] + '...' if token and len(token) > 15 else token,
                    'token_length': len(token) if token else 0
                }
            except Exception as e:
                orchestrator_tokens[key] = {'error': str(e)}
        
        await client.close()
        
        # Analyze the situation
        analysis = {
            'total_tokens_found': len(tokens_found),
            'has_tokens': len(tokens_found) > 0,
            'environment_user_id': env_user_id,
            'environment_has_api_key': env_api_key != 'NOT_SET',
            'environment_has_access_token': env_access_token != 'NOT_SET',
            'orchestrator_can_find_token': any(info['exists'] for info in orchestrator_tokens.values()),
            'recommended_action': 'none'
        }
        
        # Determine recommended action
        if not analysis['has_tokens']:
            analysis['recommended_action'] = 'authenticate_frontend'
        elif not analysis['orchestrator_can_find_token']:
            analysis['recommended_action'] = 'migrate_token'
        elif any(info.get('is_expired', False) for info in expiry_info.values()):
            analysis['recommended_action'] = 'refresh_token'
        else:
            analysis['recommended_action'] = 'check_orchestrator'
        
        return JSONResponse(content={
            "success": True,
            "redis_connected": True,
            "environment": {
                "user_id": env_user_id,
                "has_api_key": analysis['environment_has_api_key'],
                "has_access_token": analysis['environment_has_access_token']
            },
            "tokens_found": tokens_found,
            "expiry_info": expiry_info,
            "orchestrator_tokens": orchestrator_tokens,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Token diagnostic failed: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

@router.post("/repair")
async def repair_token_issue(request: TokenRepairRequest):
    """Repair token authentication issues"""
    try:
        client = await get_redis_client()
        if not client:
            raise HTTPException(status_code=500, detail="Redis connection failed")
        
        if request.action == "migrate":
            # Migrate token from one user ID to another
            source_id = request.source_user_id
            target_id = request.target_user_id or os.getenv('SHAREKHAN_USER_ID', 'QSW899')
            
            if not source_id:
                # Find any existing token
                all_keys = await client.keys("sharekhan:token:*")
                if all_keys:
                    source_key = all_keys[0]
                    source_id = source_key.decode().replace('sharekhan:token:', '') if isinstance(source_key, bytes) else source_key.replace('sharekhan:token:', '')
                else:
                    raise HTTPException(status_code=404, detail="No tokens found to migrate")
            
            # Get source token
            source_token = await client.get(f"sharekhan:token:{source_id}")
            if not source_token:
                raise HTTPException(status_code=404, detail=f"No token found for source user {source_id}")
            
            # Copy to target
            await client.set(f"sharekhan:token:{target_id}", source_token)
            
            # Copy expiry if exists
            source_expiry = await client.get(f"sharekhan:token_expiry:{source_id}")
            if source_expiry:
                await client.set(f"sharekhan:token_expiry:{target_id}", source_expiry)
            
            await client.close()
            
            return JSONResponse(content={
                "success": True,
                "action": "migrate",
                "message": f"Token migrated from {source_id} to {target_id}",
                "source_user_id": source_id,
                "target_user_id": target_id
            })
        
        elif request.action == "cleanup":
            # Clean up expired tokens
            all_keys = await client.keys("sharekhan:token:*")
            cleaned_count = 0
            
            for key in all_keys:
                try:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    user_id = key_str.replace('sharekhan:token:', '')
                    
                    # Check if expired
                    expiry_key = f"sharekhan:token_expiry:{user_id}"
                    expiry_time = await client.get(expiry_key)
                    
                    if expiry_time:
                        try:
                            expiry_dt = datetime.fromisoformat(expiry_time)
                            if expiry_dt <= datetime.now():
                                await client.delete(key)
                                await client.delete(expiry_key)
                                cleaned_count += 1
                        except Exception:
                            pass
                except Exception:
                    pass
            
            await client.close()
            
            return JSONResponse(content={
                "success": True,
                "action": "cleanup",
                "message": f"Cleaned up {cleaned_count} expired tokens"
            })
        
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'migrate' or 'cleanup'")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token repair failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orchestrator-debug")
async def debug_orchestrator_token_access():
    """Debug what the orchestrator sees when looking for tokens"""
    try:
        client = await get_redis_client()
        if not client:
            return JSONResponse(content={
                "success": False,
                "error": "Redis connection failed"
            })
        
        env_user_id = os.getenv('SHAREKHAN_USER_ID', 'QSW899')
        
        # Simulate orchestrator token search
        # DYNAMIC TOKEN PATTERNS: Use environment-based user ID
        master_user_id = os.getenv('SHAREKHAN_USER_ID', 'QSW899')
        token_keys_to_check = [
            f"sharekhan:token:{env_user_id}",
            f"sharekhan:token:{master_user_id}",  # Dynamic master user
            f"sharekhan:token:PAPER_TRADER_MAIN",
            f"sharekhan:token:QSW899",  # Backup specific user
            f"sharekhan:{env_user_id}:access_token",
            f"sharekhan:access_token",
            f"sharekhan_token_{env_user_id}"
        ]
        
        search_results = {}
        found_token = None
        
        for key in token_keys_to_check:
            try:
                token = await client.get(key)
                search_results[key] = {
                    'exists': token is not None,
                    'token_preview': token[:15] + '...' if token and len(token) > 15 else token,
                    'token_length': len(token) if token else 0
                }
                if token and not found_token:
                    found_token = token
            except Exception as e:
                search_results[key] = {'error': str(e)}
        
        # Also check wildcard search
        wildcard_keys = await client.keys("sharekhan:token:*")
        wildcard_results = {}
        
        for key in wildcard_keys:
            try:
                key_str = key.decode() if isinstance(key, bytes) else key
                token = await client.get(key)
                wildcard_results[key_str] = {
                    'exists': token is not None,
                    'token_preview': token[:15] + '...' if token and len(token) > 15 else token,
                    'token_length': len(token) if token else 0
                }
                if token and not found_token:
                    found_token = token
            except Exception as e:
                wildcard_results[key_str] = {'error': str(e)}
        
        await client.close()
        
        return JSONResponse(content={
            "success": True,
            "environment_user_id": env_user_id,
            "orchestrator_search_results": search_results,
            "wildcard_search_results": wildcard_results,
            "token_found": found_token is not None,
            "token_preview": found_token[:15] + '...' if found_token and len(found_token) > 15 else found_token,
            "recommendation": "migrate" if not found_token and wildcard_results else "check_connection",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Orchestrator debug failed: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }) 