#!/usr/bin/env python3
"""
Deploy Redis Fallback System
Commits and pushes Redis fallback changes to production
"""

import os
import sys
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd, cwd=None):
    """Run a command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    logger.info("🚀 Deploying Redis Fallback System")
    logger.info("=" * 50)
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Check git status
    logger.info("📊 Checking git status...")
    success, stdout, stderr = run_command("git status --porcelain", cwd=project_root)
    if success and stdout.strip():
        logger.info("📝 Found changes to commit:")
        for line in stdout.strip().split('\n'):
            logger.info(f"  {line}")
    else:
        logger.info("✅ No changes to commit")
        return
    
    # Add all changes
    logger.info("📝 Adding changes to git...")
    success, stdout, stderr = run_command("git add .", cwd=project_root)
    if not success:
        logger.error(f"❌ Failed to add changes: {stderr}")
        return
    
    # Commit changes
    commit_message = """🔧 Implement Redis Fallback System for Production Resilience

✅ Key Features:
- ProductionRedisFallback class with in-memory cache fallback
- Orchestrator integration with Redis fallback manager
- ShareKhan token storage/retrieval with fallback support
- Graceful degradation when Redis unavailable
- Production environment configuration template

✅ Benefits:
- System continues working without Redis connection
- ShareKhan authentication tokens cached in memory
- No system crashes due to Redis failures
- Seamless fallback to in-memory cache
- Production-ready with proper error handling

✅ Files Modified:
- src/core/redis_fallback_manager.py (NEW)
- src/core/orchestrator.py (Redis integration)
- production.env.example (Environment template)
- Test scripts for validation

🚀 Ready for production deployment with Redis resilience"""
    
    logger.info("💾 Committing changes...")
    success, stdout, stderr = run_command(f'git commit -m "{commit_message}"', cwd=project_root)
    if not success:
        logger.error(f"❌ Failed to commit changes: {stderr}")
        return
    
    logger.info("✅ Changes committed successfully!")
    
    # Push to main branch
    logger.info("🚀 Pushing to main branch...")
    success, stdout, stderr = run_command("git push origin main", cwd=project_root)
    if not success:
        logger.error(f"❌ Failed to push changes: {stderr}")
        logger.error("Please check your git credentials and network connection")
        return
    
    logger.info("✅ Changes pushed to main branch successfully!")
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("🎉 REDIS FALLBACK SYSTEM DEPLOYED!")
    logger.info("=" * 50)
    logger.info("✅ Production Redis fallback system implemented")
    logger.info("✅ Orchestrator updated with fallback integration")
    logger.info("✅ Environment configuration template created")
    logger.info("✅ All changes committed and pushed to main")
    
    logger.info("\n📋 NEXT STEPS FOR PRODUCTION:")
    logger.info("1. Configure Redis environment variables on Digital Ocean:")
    logger.info("   - REDIS_HOST, REDIS_PORT, REDIS_PASSWORD")
    logger.info("   - Or use REDIS_URL for managed Redis service")
    logger.info("2. Deploy updated codebase to production")
    logger.info("3. Monitor logs for Redis connection status")
    logger.info("4. Verify ShareKhan token retrieval works")
    logger.info("5. Test real trade execution")
    
    logger.info("\n🔧 FALLBACK BEHAVIOR:")
    logger.info("- If Redis available: Normal Redis operations")
    logger.info("- If Redis unavailable: In-memory cache fallback")
    logger.info("- System continues working in both modes")
    logger.info("- ShareKhan tokens cached for session duration")
    
    logger.info("\n🚀 System is now resilient to Redis failures!")

if __name__ == "__main__":
    main()
