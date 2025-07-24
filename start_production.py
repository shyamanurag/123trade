#!/usr/bin/env python3
"""
Production-grade startup script for the Crypto Trading System
Integrates frontend and backend with comprehensive monitoring and error handling
"""

import os
import sys
import asyncio
import logging
import subprocess
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any
import uvicorn
from contextlib import asynccontextmanager

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from main import QuantumTradingSystem
from src.core.crypto_strategy_orchestrator_enhanced import EnhancedCryptoStrategyOrchestrator


class ProductionTradingSystemManager:
    """Production-grade manager for the entire trading system"""
    
    def __init__(self):
        self.trading_system: Optional[QuantumTradingSystem] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.backend_process: Optional[subprocess.Popen] = None
        self.config_path = "config/trading_config.json"
        self.is_running = False
        self.setup_logging()
        
    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/production.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        try:
            import fastapi
            import uvicorn
            import websockets
            import prometheus_client
            self.logger.info("✅ Backend dependencies verified")
            return True
        except ImportError as e:
            self.logger.error(f"❌ Missing backend dependency: {e}")
            return False
            
    def check_frontend_dependencies(self) -> bool:
        """Check if frontend dependencies are installed"""
        frontend_path = Path("src/frontend")
        if not frontend_path.exists():
            self.logger.error("❌ Frontend directory not found")
            return False
            
        node_modules = frontend_path / "node_modules"
        if not node_modules.exists():
            self.logger.warning("⚠️ Frontend dependencies not installed, installing...")
            return self.install_frontend_dependencies()
            
        self.logger.info("✅ Frontend dependencies verified")
        return True
        
    def install_frontend_dependencies(self) -> bool:
        """Install frontend dependencies"""
        try:
            frontend_path = Path("src/frontend")
            result = subprocess.run(
                ["npm", "install"],
                cwd=frontend_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Frontend dependencies installed successfully")
                return True
            else:
                self.logger.error(f"❌ Failed to install frontend dependencies: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("❌ Frontend dependency installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error installing frontend dependencies: {e}")
            return False
            
    def build_frontend(self) -> bool:
        """Build the frontend for production"""
        try:
            frontend_path = Path("src/frontend")
            self.logger.info("🔨 Building frontend for production...")
            
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=frontend_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Frontend built successfully")
                return True
            else:
                self.logger.error(f"❌ Frontend build failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("❌ Frontend build timed out")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error building frontend: {e}")
            return False
            
    async def initialize_trading_system(self) -> bool:
        """Initialize the quantum trading system"""
        try:
            self.logger.info("🚀 Initializing Quantum Trading System...")
            self.trading_system = QuantumTradingSystem(self.config_path)
            await self.trading_system.initialize()
            self.logger.info("✅ Trading system initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize trading system: {e}")
            return False
            
    def start_backend_server(self) -> bool:
        """Start the FastAPI backend server"""
        try:
            self.logger.info("🌐 Starting FastAPI backend server...")
            
            # Use uvicorn programmatically for better control
            config = uvicorn.Config(
                "app:app",
                host="0.0.0.0",
                port=8000,
                log_level="info",
                reload=False,
                workers=1,
                access_log=True
            )
            
            server = uvicorn.Server(config)
            
            # Run server in background
            import threading
            server_thread = threading.Thread(target=server.run)
            server_thread.daemon = True
            server_thread.start()
            
            # Give server time to start
            time.sleep(3)
            
            self.logger.info("✅ Backend server started on http://localhost:8000")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start backend server: {e}")
            return False
            
    async def start_trading_loop(self):
        """Start the main trading loop"""
        try:
            if self.trading_system:
                self.logger.info("📈 Starting trading loop...")
                await self.trading_system.start()
            else:
                self.logger.error("❌ Trading system not initialized")
        except Exception as e:
            self.logger.error(f"❌ Error in trading loop: {e}")
            
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"🛑 Received signal {signum}, shutting down...")
            asyncio.create_task(self.shutdown())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    async def shutdown(self):
        """Graceful shutdown of all components"""
        self.logger.info("🛑 Initiating graceful shutdown...")
        self.is_running = False
        
        # Stop trading system
        if self.trading_system:
            try:
                # Add shutdown method to trading system if available
                if self.trading_system:
                    await self.trading_system.stop()
                    self.logger.info("✅ Trading system stopped")
            except Exception as e:
                self.logger.error(f"❌ Error stopping trading system: {e}")
                
        # Stop processes
        for process, name in [(self.frontend_process, "Frontend"), (self.backend_process, "Backend")]:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=10)
                    self.logger.info(f"✅ {name} process stopped")
                except subprocess.TimeoutExpired:
                    process.kill()
                    self.logger.warning(f"⚠️ {name} process killed (timeout)")
                except Exception as e:
                    self.logger.error(f"❌ Error stopping {name} process: {e}")
                    
        self.logger.info("🏁 Shutdown complete")
        
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {}
        }
        
        try:
            # Check trading system
            if self.trading_system:
                health_status["components"]["trading_system"] = "healthy"
            else:
                health_status["components"]["trading_system"] = "not_initialized"
                health_status["status"] = "degraded"
                
            # Check backend server
            try:
                import requests
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    health_status["components"]["backend"] = "healthy"
                else:
                    health_status["components"]["backend"] = "unhealthy"
                    health_status["status"] = "degraded"
            except Exception:
                health_status["components"]["backend"] = "unreachable"
                health_status["status"] = "degraded"
                
            # Check frontend build
            frontend_dist = Path("src/frontend/dist")
            if frontend_dist.exists():
                health_status["components"]["frontend"] = "built"
            else:
                health_status["components"]["frontend"] = "not_built"
                health_status["status"] = "degraded"
                
        except Exception as e:
            health_status["status"] = "error"
            health_status["error"] = str(e)
            
        return health_status
        
    async def run(self):
        """Main entry point for the production system"""
        self.logger.info("🚀 Starting Production Crypto Trading System...")
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Pre-flight checks
        if not self.check_dependencies():
            self.logger.error("❌ Dependency check failed")
            return False
            
        if not self.check_frontend_dependencies():
            self.logger.error("❌ Frontend dependency check failed")
            return False
            
        # Build frontend
        if not self.build_frontend():
            self.logger.error("❌ Frontend build failed")
            return False
            
        # Initialize trading system
        if not await self.initialize_trading_system():
            self.logger.error("❌ Trading system initialization failed")
            return False
            
        # Start backend server
        if not self.start_backend_server():
            self.logger.error("❌ Backend server startup failed")
            return False
            
        self.is_running = True
        
        # Health check
        health = await self.health_check()
        self.logger.info(f"📊 System health: {health['status']}")
        
        # Start trading loop
        self.logger.info("🎯 System ready! Starting trading operations...")
        
        try:
            # Run trading loop
            await self.start_trading_loop()
        except KeyboardInterrupt:
            self.logger.info("🛑 Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}")
        finally:
            await self.shutdown()
            
        return True


async def main():
    """Main entry point"""
    manager = ProductionTradingSystemManager()
    success = await manager.run()
    return 0 if success else 1


if __name__ == "__main__":
    # Ensure required directories exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    
    # Run the production system
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
