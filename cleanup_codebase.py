#!/usr/bin/env python3
"""
Codebase Cleanup Script
======================
Removes unused files and organizes the trading system codebase for better maintainability.
"""

import os
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_codebase():
    """Clean up unused files and organize codebase"""
    
    # Files and directories to remove (unused/redundant)
    files_to_remove = [
        # Duplicate/old files
        "main_production.py",  # Use main.py instead
        "sharekhan_standalone.py",  # Integrated into main system
        "websocket_manager.py",  # Integrated into orchestrator
        "zero_trade_diagnosis.py",  # Diagnostic script, not needed in production
        "verify_sharekhan_fix.py",  # Diagnostic script
        "fix_sharekhan_auth.py",  # Diagnostic script
        "debug_signal_generation.py",  # Debug script
        "diagnose_signal_timing.py",  # Debug script
        "strategy_fine_tuning_analysis.py",  # Analysis script
        "analyze_strategy_signals.py",  # Analysis script
        "monitor_deployment.py",  # Use monitoring system instead
        "monitor_deployment_status.py",  # Use monitoring system instead
        "manual_cleanup_migration.py",  # Migration script, not needed
        "emergency_db_cleanup.py",  # Emergency script, keep in scripts/
        "add_broker_user_and_start_trading.py",  # Use API instead
        "start_trading.py",  # Use main.py instead
        "subscribe_indices.py",  # Integrated into main system
        "update_sharekhan_symbols.py",  # Integrated into main system
        "update_sharekhan_credentials.py",  # Use API instead
        
        # Test files (move to tests/ directory)
        "test_redis_token_retrieval.py",
        "test_signal_fixes.py",
        "test_symbol_expansion.js",
        
        # Temporary files
        "temp_changes.txt",
        "test_creation.txt",
        "local_development.log",
        
        # Duplicate directories
        "api/",  # Use src/api/ instead
        "core/",  # Use src/core/ instead
        
        # Old deployment files
        "deployment_trigger.txt",
        "DEPLOYMENT_TRIGGER_2025_07_03.txt",
        "DEPLOYMENT_TRIGGER_MIGRATION_010.txt",
        
        # Package files (if not needed)
        "package.json",
        "package-lock.json",
    ]
    
    # Directories to clean up
    dirs_to_remove = [
        "__pycache__",
        ".pytest_cache",
        "dist",
        "Lib",  # Python virtual env lib
        "DLLs",  # Python virtual env DLLs
        "Doc",  # Python virtual env docs
        "Tools",  # Python virtual env tools
        "tcl",  # Python virtual env tcl
    ]
    
    # Move files to appropriate locations
    files_to_move = {
        "test_redis_token_retrieval.py": "tests/",
        "test_signal_fixes.py": "tests/",
        "emergency_db_cleanup.py": "scripts/",
    }
    
    project_root = Path(__file__).parent
    
    logger.info("🧹 Starting codebase cleanup...")
    
    # Remove unused files
    for file_path in files_to_remove:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                if full_path.is_file():
                    full_path.unlink()
                    logger.info(f"✅ Removed file: {file_path}")
                elif full_path.is_dir():
                    shutil.rmtree(full_path)
                    logger.info(f"✅ Removed directory: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove {file_path}: {e}")
    
    # Remove cache directories
    for dir_name in dirs_to_remove:
        for cache_dir in project_root.rglob(dir_name):
            if cache_dir.is_dir():
                try:
                    shutil.rmtree(cache_dir)
                    logger.info(f"✅ Removed cache directory: {cache_dir}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not remove {cache_dir}: {e}")
    
    # Move files to appropriate locations
    for src_file, dest_dir in files_to_move.items():
        src_path = project_root / src_file
        dest_path = project_root / dest_dir
        
        if src_path.exists():
            try:
                dest_path.mkdir(exist_ok=True)
                shutil.move(str(src_path), str(dest_path / src_file))
                logger.info(f"✅ Moved {src_file} to {dest_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Could not move {src_file}: {e}")
    
    # Clean up duplicate strategy files
    strategy_duplicates = [
        "src/core/volume_profile_scalper.py",  # Use strategies/ version
        "src/core/news_impact_scalper.py",  # Use strategies/ version
    ]
    
    for duplicate in strategy_duplicates:
        duplicate_path = project_root / duplicate
        if duplicate_path.exists():
            try:
                duplicate_path.unlink()
                logger.info(f"✅ Removed duplicate strategy: {duplicate}")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove duplicate {duplicate}: {e}")
    
    # Create organized directory structure
    essential_dirs = [
        "logs",
        "tests",
        "scripts",
        "docs/api",
        "docs/deployment",
    ]
    
    for dir_path in essential_dirs:
        (project_root / dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Ensured directory exists: {dir_path}")
    
    logger.info("🎉 Codebase cleanup completed!")
    logger.info("📁 Organized structure:")
    logger.info("  - src/: Main application code")
    logger.info("  - strategies/: Trading strategies")
    logger.info("  - config/: Configuration files")
    logger.info("  - tests/: Test files")
    logger.info("  - scripts/: Utility scripts")
    logger.info("  - docs/: Documentation")
    logger.info("  - logs/: Application logs")

if __name__ == "__main__":
    cleanup_codebase()
