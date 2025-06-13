"""
Backup Manager
Handles automated backup of encrypted configurations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import json
import os
from typing import Dict, List, Optional
import aiofiles
import yaml
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, config: Dict):
        self.config = config
        self.backup_dir = Path(config.get('backup_dir', 'backups'))
        self.retention_days = config.get('backup_retention_days', 30)
        self.encryption_key = config.get('backup_encryption_key')
        self.cipher_suite = Fernet(self.encryption_key.encode()) if self.encryption_key else None
        self._backup_task = None

    async def start(self):
        """Start the backup manager"""
        self._backup_task = asyncio.create_task(self._run_backup_schedule())
        logger.info("Backup manager started")

    async def stop(self):
        """Stop the backup manager"""
        if self._backup_task:
            self._backup_task.cancel()
            try:
                await self._backup_task
            except asyncio.CancelledError:
                pass
        logger.info("Backup manager stopped")

    async def _run_backup_schedule(self):
        """Run backup schedule"""
        while True:
            try:
                # Create backup
                await self.create_backup()
                
                # Clean up old backups
                await self.cleanup_old_backups()
                
                # Wait until next backup
                await asyncio.sleep(24 * 60 * 60)  # Daily backup
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in backup schedule: {e}")
                await asyncio.sleep(60 * 60)  # Wait an hour before retrying

    async def create_backup(self):
        """Create a new backup"""
        try:
            # Create backup directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.backup_dir / timestamp
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Backup configuration files
            config_dir = Path(self.config.get('config_dir', 'config'))
            for config_file in config_dir.glob('*.yaml'):
                await self._backup_file(config_file, backup_path)
            
            # Create backup manifest
            manifest = {
                'timestamp': timestamp,
                'files': [f.name for f in backup_path.glob('*')],
                'encrypted': bool(self.cipher_suite)
            }
            
            async with aiofiles.open(backup_path / 'manifest.json', 'w') as f:
                await f.write(json.dumps(manifest, indent=2))
            
            logger.info(f"Created backup: {backup_path}")
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")

    async def _backup_file(self, file_path: Path, backup_path: Path):
        """Backup a single file"""
        try:
            # Read file content
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            
            # Encrypt if needed
            if self.cipher_suite:
                content = self.cipher_suite.encrypt(content.encode()).decode()
            
            # Write to backup
            backup_file = backup_path / file_path.name
            async with aiofiles.open(backup_file, 'w') as f:
                await f.write(content)
            
            # Set secure permissions
            os.chmod(backup_file, 0o600)
            
        except Exception as e:
            logger.error(f"Error backing up file {file_path}: {e}")

    async def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for backup_dir in self.backup_dir.glob('*'):
                if not backup_dir.is_dir():
                    continue
                
                try:
                    # Parse timestamp from directory name
                    timestamp = datetime.strptime(backup_dir.name, '%Y%m%d_%H%M%S')
                    
                    if timestamp < cutoff_date:
                        shutil.rmtree(backup_dir)
                        logger.info(f"Removed old backup: {backup_dir}")
                        
                except ValueError:
                    # Skip directories that don't match timestamp format
                    continue
                
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    async def restore_backup(self, backup_timestamp: str, target_dir: Optional[Path] = None):
        """Restore from a backup"""
        try:
            backup_path = self.backup_dir / backup_timestamp
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup not found: {backup_path}")
            
            # Read manifest
            async with aiofiles.open(backup_path / 'manifest.json', 'r') as f:
                manifest = json.loads(await f.read())
            
            # Set target directory
            target_dir = target_dir or Path(self.config.get('config_dir', 'config'))
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Restore files
            for file_name in manifest['files']:
                if file_name == 'manifest.json':
                    continue
                    
                source_file = backup_path / file_name
                target_file = target_dir / file_name
                
                await self._restore_file(source_file, target_file, manifest['encrypted'])
            
            logger.info(f"Restored backup {backup_timestamp} to {target_dir}")
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            raise

    async def _restore_file(self, source_file: Path, target_file: Path, is_encrypted: bool):
        """Restore a single file"""
        try:
            # Read backup file
            async with aiofiles.open(source_file, 'r') as f:
                content = await f.read()
            
            # Decrypt if needed
            if is_encrypted and self.cipher_suite:
                content = self.cipher_suite.decrypt(content.encode()).decode()
            
            # Write to target
            async with aiofiles.open(target_file, 'w') as f:
                await f.write(content)
            
            # Set secure permissions
            os.chmod(target_file, 0o600)
            
        except Exception as e:
            logger.error(f"Error restoring file {source_file}: {e}")
            raise

    async def list_backups(self) -> List[Dict]:
        """List available backups"""
        try:
            backups = []
            
            for backup_dir in self.backup_dir.glob('*'):
                if not backup_dir.is_dir():
                    continue
                
                try:
                    # Read manifest
                    async with aiofiles.open(backup_dir / 'manifest.json', 'r') as f:
                        manifest = json.loads(await f.read())
                    
                    backups.append({
                        'timestamp': manifest['timestamp'],
                        'files': manifest['files'],
                        'encrypted': manifest['encrypted']
                    })
                    
                except (ValueError, FileNotFoundError):
                    # Skip invalid backups
                    continue
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return [] 