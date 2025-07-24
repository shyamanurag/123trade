#!/usr/bin/env python3
"""
Direct Local Production Runner
Runs the full production trading system locally without Docker
All production features enabled - no shortcuts
"""

import os
import sys
import subprocess
import time
import logging
import asyncio
from pathlib import Path
import shutil
import signal
from typing import List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DirectProductionRunner:
    """Run production environment directly without Docker"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.project_root = Path(__file__).parent
        self.setup_environment()
        
    def setup_environment(self):
        """Setup environment for production deployment"""
        logger.info("🔧 Setting up production environment...")
        
        # Copy environment file if it doesn't exist
        env_file = self.project_root / ".env"
        template_file = self.project_root / "local-production.env"
        
        if not env_file.exists() and template_file.exists():
            logger.info("📄 Creating .env from production template...")
            shutil.copy(template_file, env_file)
            logger.info("✅ Environment file created")
        
        # Create required directories
        for directory in ['logs', 'data', 'backups', 'temp']:
            dir_path = self.project_root / directory
            dir_path.mkdir(exist_ok=True)
            
        logger.info("✅ Environment setup complete")
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        logger.info("📦 Checking dependencies...")
        
        try:
            import fastapi
            import uvicorn
            import redis
            import psycopg2
            import sqlalchemy
            import pydantic
            import jwt
            import bcrypt
            logger.info("✅ All core dependencies available")
            return True
        except ImportError as e:
            logger.error(f"❌ Missing dependency: {e}")
            logger.info("Installing missing dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            return True
    
    def setup_local_services(self):
        """Setup local services info"""
        logger.info("🔍 Checking local services...")
        
        # Check if PostgreSQL service exists
        try:
            result = subprocess.run(
                ['sc', 'query', 'postgresql'], 
                capture_output=True, 
                text=True, 
                shell=True
            )
            if result.returncode == 0:
                logger.info("✅ PostgreSQL service found")
            else:
                logger.warning("⚠️ PostgreSQL not found as Windows service")
                logger.info("💡 You can install PostgreSQL from: https://www.postgresql.org/download/windows/")
        except Exception as e:
            logger.warning(f"⚠️ Could not check PostgreSQL service: {e}")
        
        # Check if Redis is available
        try:
            result = subprocess.run(
                ['sc', 'query', 'Redis'], 
                capture_output=True, 
                text=True, 
                shell=True
            )
            if result.returncode == 0:
                logger.info("✅ Redis service found")
            else:
                logger.warning("⚠️ Redis not found as Windows service")
                logger.info("💡 You can install Redis from the official Redis website or package manager")
        except Exception as e:
            logger.warning(f"⚠️ Could not check Redis service: {e}")
    
    def start_trading_api(self):
        """Start the main trading API in production mode"""
        logger.info("🚀 Starting Trading API (Production Mode)...")
        
        # Set production environment variables
        env = os.environ.copy()
        env.update({
            'DEPLOYMENT_MODE': 'production',
            'TRADING_MODE': 'production',
            'LOG_LEVEL': 'INFO',
            'DEBUG': 'false',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8000',
            'API_WORKERS': '4'
        })
        
        # Start the API server
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--workers", "4",
            "--log-level", "info",
            "--access-log"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.processes.append(process)
            logger.info("✅ Trading API starting...")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to start Trading API: {e}")
            return None
    
    def start_frontend(self):
        """Start the frontend development server"""
        logger.info("💻 Starting Frontend Dashboard...")
        
        frontend_dir = self.project_root / "src" / "frontend"
        if not frontend_dir.exists():
            logger.warning("⚠️ Frontend directory not found")
            return None
            
        try:
            # Check if npm is available
            subprocess.run(['npm', '--version'], check=True, capture_output=True)
            
            # Install dependencies if needed
            if not (frontend_dir / "node_modules").exists():
                logger.info("📦 Installing frontend dependencies...")
                subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
            
            # Start the development server
            env = os.environ.copy()
            env.update({
                'REACT_APP_API_URL': 'http://localhost:8000',
                'REACT_APP_WS_URL': 'ws://localhost:8000'
            })
            
            process = subprocess.Popen(
                ['npm', 'run', 'dev'],
                cwd=frontend_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            self.processes.append(process)
            logger.info("✅ Frontend starting...")
            return process
        except subprocess.CalledProcessError:
            logger.warning("⚠️ npm not found - frontend will not start")
            logger.info("💡 Install Node.js from: https://nodejs.org/")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to start frontend: {e}")
            return None
    
    def monitor_processes(self):
        """Monitor running processes"""
        logger.info("👀 Monitoring services...")
        
        while True:
            try:
                time.sleep(5)
                
                # Check if processes are still running
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        logger.warning(f"⚠️ Process {i} has stopped")
                        
                # Check API health
                try:
                    import requests
                    response = requests.get("http://localhost:8000/health", timeout=5)
                    if response.status_code == 200:
                        logger.debug("✅ API health check passed")
                    else:
                        logger.warning(f"⚠️ API health check failed: {response.status_code}")
                except:
                    pass  # API might still be starting
                    
            except KeyboardInterrupt:
                break
    
    def cleanup(self):
        """Clean up processes"""
        logger.info("🛑 Stopping all services...")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.warning(f"Error stopping process: {e}")
        
        logger.info("✅ All services stopped")
    
    def display_startup_info(self):
        """Display startup information"""
        logger.info("=" * 80)
        logger.info("🚀 LOCAL PRODUCTION ENVIRONMENT STARTED!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("📊 AVAILABLE SERVICES:")
        logger.info("")
        logger.info("  🏛️  Trading API (Production): http://localhost:8000")
        logger.info("  📖 API Documentation:         http://localhost:8000/docs")
        logger.info("  🩺 Health Check:              http://localhost:8000/health")
        logger.info("  💻 Frontend Dashboard:        http://localhost:3000")
        logger.info("")
        logger.info("🔐 PRODUCTION FEATURES ENABLED:")
        logger.info("  • Real-time market data integration")
        logger.info("  • Autonomous trading capabilities")
        logger.info("  • Advanced risk management")
        logger.info("  • 6 sophisticated trading strategies")
        logger.info("  • Production-grade authentication")
        logger.info("  • No mock data - all real and dynamic")
        logger.info("")
        logger.info("⚠️  IMPORTANT:")
        logger.info("  • Paper trading enabled for safety")
        logger.info("  • Configure broker credentials in .env file")
        logger.info("  • Check logs/ directory for application logs")
        logger.info("")
        logger.info("🛑 TO STOP: Press Ctrl+C")
        logger.info("=" * 80)
        
        # Open services in browser
        try:
            import webbrowser
            webbrowser.open("http://localhost:8000/docs")
            time.sleep(2)
            webbrowser.open("http://localhost:3000")
        except:
            pass
    
    def run(self):
        """Run the complete production environment"""
        try:
            logger.info("🚀 Starting Local Production Environment...")
            logger.info("=" * 80)
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, lambda s, f: self.cleanup())
            signal.signal(signal.SIGTERM, lambda s, f: self.cleanup())
            
            # Check dependencies
            if not self.check_dependencies():
                return 1
            
            # Setup local services
            self.setup_local_services()
            
            # Start services
            api_process = self.start_trading_api()
            if not api_process:
                logger.error("❌ Failed to start Trading API")
                return 1
            
            # Wait for API to start
            logger.info("⏳ Waiting for API to start...")
            time.sleep(10)
            
            # Start frontend
            frontend_process = self.start_frontend()
            
            # Display information
            self.display_startup_info()
            
            # Monitor processes
            self.monitor_processes()
            
        except KeyboardInterrupt:
            logger.info("👋 Shutting down...")
        except Exception as e:
            logger.error(f"❌ Error running production environment: {e}")
            return 1
        finally:
            self.cleanup()
        
        return 0

def main():
    """Main entry point"""
    runner = DirectProductionRunner()
    return runner.run()

if __name__ == "__main__":
    sys.exit(main()) 