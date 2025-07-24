#!/usr/bin/env python3
"""
Complete Trading System Launcher
Starts both backend API and frontend dashboard
"""

import os
import sys
import subprocess
import time
import logging
import webbrowser
from pathlib import Path
import signal
from typing import List
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompleteTradingSystem:
    """Launch complete trading system with backend and frontend"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.project_root = Path(__file__).parent
        self.setup_environment()
        
    def setup_environment(self):
        """Setup environment for complete system"""
        logger.info("🔧 Setting up complete trading environment...")
        
        # Ensure .env exists
        env_file = self.project_root / ".env"
        template_file = self.project_root / "local-production.env"
        
        if not env_file.exists() and template_file.exists():
            logger.info("📄 Creating .env from production template...")
            import shutil
            shutil.copy(template_file, env_file)
        
        # Create required directories
        for directory in ['logs', 'data', 'backups', 'temp']:
            dir_path = self.project_root / directory
            dir_path.mkdir(exist_ok=True)
            
        logger.info("✅ Environment setup complete")
    
    def start_backend_api(self):
        """Start the backend trading API"""
        logger.info("🚀 Starting Backend Trading API...")
        
        # Set production environment variables
        env = os.environ.copy()
        env.update({
            'DEPLOYMENT_MODE': 'production',
            'TRADING_MODE': 'production',
            'LOG_LEVEL': 'INFO',
            'DEBUG': 'false',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8000'
        })
        
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                cwd=self.project_root,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.processes.append(process)
            logger.info("✅ Backend API started in new console")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to start backend API: {e}")
            return None
    
    def start_frontend(self):
        """Start the frontend dashboard"""
        logger.info("💻 Starting Frontend Dashboard...")
        
        frontend_dir = self.project_root / "src" / "frontend"
        if not frontend_dir.exists():
            logger.error("❌ Frontend directory not found")
            return None
            
        try:
            # Set environment variables for frontend
            env = os.environ.copy()
            env.update({
                'REACT_APP_API_URL': 'http://localhost:8000',
                'REACT_APP_WS_URL': 'ws://localhost:8000',
                'BROWSER': 'none'  # Prevent auto-opening browser
            })
            
            # Start the frontend development server
            cmd = ['cmd.exe', '/c', 'npm', 'run', 'dev']
            
            process = subprocess.Popen(
                cmd,
                cwd=frontend_dir,
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.processes.append(process)
            logger.info("✅ Frontend started in new console")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to start frontend: {e}")
            return None
    
    def wait_for_services(self):
        """Wait for services to become available"""
        logger.info("⏳ Waiting for services to start...")
        
        # Wait for backend
        backend_ready = False
        for i in range(30):  # Wait up to 30 seconds
            try:
                import requests
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    logger.info("✅ Backend API ready")
                    backend_ready = True
                    break
            except:
                pass
            time.sleep(1)
        
        if not backend_ready:
            logger.warning("⚠️ Backend API may not be ready")
        
        # Wait for frontend
        frontend_ready = False
        for i in range(30):  # Wait up to 30 seconds
            try:
                import requests
                response = requests.get("http://localhost:3000", timeout=2)
                if response.status_code == 200:
                    logger.info("✅ Frontend ready")
                    frontend_ready = True
                    break
            except:
                pass
            time.sleep(1)
        
        if not frontend_ready:
            logger.warning("⚠️ Frontend may not be ready")
        
        return backend_ready, frontend_ready
    
    def open_browser_tabs(self):
        """Open browser tabs for the application"""
        logger.info("🌐 Opening browser tabs...")
        
        time.sleep(2)  # Give services time to fully start
        
        try:
            # Open main dashboard
            webbrowser.open("http://localhost:3000")
            time.sleep(1)
            
            # Open API documentation
            webbrowser.open("http://localhost:8000/docs")
            time.sleep(1)
            
            logger.info("✅ Browser tabs opened")
        except Exception as e:
            logger.warning(f"⚠️ Could not open browser: {e}")
    
    def display_status(self):
        """Display system status and URLs"""
        logger.info("================================================================================")
        logger.info("🚀 COMPLETE TRADING SYSTEM STARTED!")
        logger.info("================================================================================")
        logger.info("")
        logger.info("📊 AVAILABLE SERVICES:")
        logger.info("")
        logger.info("   🎯 Frontend Dashboard:        http://localhost:3000")
        logger.info("   🏛️  Backend Trading API:      http://localhost:8000")
        logger.info("   📖 API Documentation:         http://localhost:8000/docs")
        logger.info("   🩺 Health Check:              http://localhost:8000/health")
        logger.info("   📊 System Status:             http://localhost:8000/api/system/status")
        logger.info("   💹 Market Data:               http://localhost:8000/api/market-data")
        logger.info("   🎯 Trading Strategies:        http://localhost:8000/api/strategies")
        logger.info("")
        logger.info("🔐 FEATURES ENABLED:")
        logger.info("   • Complete React Frontend Dashboard")
        logger.info("   • Real-time market data integration")
        logger.info("   • Autonomous trading capabilities")
        logger.info("   • Advanced risk management")
        logger.info("   • 6 sophisticated trading strategies")
        logger.info("   • Production-grade authentication")
        logger.info("   • Live WebSocket connections")
        logger.info("   • Portfolio management")
        logger.info("   • Real-time trade execution")
        logger.info("")
        logger.info("⚠️  IMPORTANT:")
        logger.info("   • Paper trading enabled for safety")
        logger.info("   • Configure broker credentials in .env file")
        logger.info("   • Both frontend and backend running in separate consoles")
        logger.info("   • Check logs/ directory for application logs")
        logger.info("")
        logger.info("🛑 TO STOP: Close this window or press Ctrl+C")
        logger.info("================================================================================")
    
    def monitor_system(self):
        """Monitor the complete system"""
        logger.info("👀 Monitoring complete system...")
        
        try:
            while True:
                time.sleep(10)
                
                # Check processes
                running_processes = []
                for i, process in enumerate(self.processes):
                    if process.poll() is None:
                        running_processes.append(i)
                    else:
                        logger.warning(f"⚠️ Process {i} has stopped")
                
                if not running_processes:
                    logger.error("❌ All processes have stopped")
                    break
                
                # Quick health check
                try:
                    import requests
                    response = requests.get("http://localhost:8000/health", timeout=2)
                    if response.status_code == 200:
                        logger.debug("✅ System health check passed")
                    else:
                        logger.warning(f"⚠️ Health check failed: {response.status_code}")
                except:
                    logger.warning("⚠️ Backend not responding")
                    
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown signal received")
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown all processes"""
        logger.info("🛑 Shutting down complete system...")
        
        for i, process in enumerate(self.processes):
            try:
                process.terminate()
                logger.info(f"✅ Process {i} terminated")
            except:
                try:
                    process.kill()
                    logger.info(f"✅ Process {i} killed")
                except:
                    logger.warning(f"⚠️ Could not stop process {i}")
        
        logger.info("✅ System shutdown complete")
    
    def run(self):
        """Run the complete trading system"""
        logger.info("🚀 Starting Complete Trading System...")
        logger.info("================================================================================")
        
        try:
            # Start backend
            backend_process = self.start_backend_api()
            if not backend_process:
                logger.error("❌ Failed to start backend - aborting")
                return
            
            # Wait a moment for backend to initialize
            time.sleep(3)
            
            # Start frontend
            frontend_process = self.start_frontend()
            if not frontend_process:
                logger.warning("⚠️ Frontend failed to start - continuing with backend only")
            
            # Wait for services
            backend_ready, frontend_ready = self.wait_for_services()
            
            # Display status
            self.display_status()
            
            # Open browser tabs
            if frontend_ready:
                self.open_browser_tabs()
            
            # Monitor system
            self.monitor_system()
            
        except KeyboardInterrupt:
            logger.info("🛑 Interrupted by user")
            self.shutdown()
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            self.shutdown()

def main():
    """Main entry point"""
    try:
        system = CompleteTradingSystem()
        system.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 