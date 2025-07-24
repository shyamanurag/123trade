#!/usr/bin/env python3
"""
Unified Trading System Main Entry Point
Supports multiple deployment modes: production, development, free-tier, and simple
"""

import asyncio
import logging
import os
import sys
import uvicorn
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

class DeploymentMode(str, Enum):
    """Deployment modes supported by the system"""
    PRODUCTION = "production"
    DEVELOPMENT = "development" 
    FREE_TIER = "free-tier"
    SIMPLE = "simple"
    TESTING = "testing"

class TradingSystemLauncher:
    """Unified launcher for all trading system modes"""
    
    def __init__(self, mode: DeploymentMode = DeploymentMode.DEVELOPMENT):
        self.mode = mode
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
    def setup_logging(self):
        """Setup logging based on deployment mode"""
        log_level = logging.INFO
        if self.mode == DeploymentMode.DEVELOPMENT:
            log_level = logging.DEBUG
        elif self.mode == DeploymentMode.PRODUCTION:
            log_level = logging.WARNING
            
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        log_handlers = [logging.StreamHandler(sys.stdout)]
        
        if self.mode != DeploymentMode.TESTING:
            log_handlers.append(
                logging.FileHandler(f'logs/trading_system_{self.mode.value}.log')
            )
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=log_handlers
        )
        
    def get_app_config(self) -> Dict[str, Any]:
        """Get application configuration based on mode"""
        base_config = {
            "host": "0.0.0.0",
            "port": 8000,
            "reload": False,
            "workers": 1,
            "log_level": "info"
        }
        
        if self.mode == DeploymentMode.DEVELOPMENT:
            base_config.update({
                "reload": True,
                "log_level": "debug"
            })
        elif self.mode == DeploymentMode.PRODUCTION:
            base_config.update({
                "workers": 4,
                "log_level": "warning"
            })
        elif self.mode == DeploymentMode.FREE_TIER:
            base_config.update({
                "port": 8001,  # Different port for free tier
                "log_level": "info"
            })
        elif self.mode == DeploymentMode.SIMPLE:
            base_config.update({
                "port": 8002,  # Different port for simple mode
                "log_level": "info"
            })
            
        return base_config
        
    def get_app_module(self) -> str:
        """Get the FastAPI app module based on mode"""
        if self.mode == DeploymentMode.SIMPLE:
            return "app_simple:app"
        elif self.mode == DeploymentMode.FREE_TIER:
            os.environ["TRADING_MODE"] = "free-tier"
            return "app:app"
        elif self.mode in [DeploymentMode.PRODUCTION, DeploymentMode.DEVELOPMENT]:
            os.environ["TRADING_MODE"] = self.mode.value
            return "app:app"
        else:  # testing
            return "app:app"
            
    def display_startup_banner(self):
        """Display startup banner based on mode"""
        mode_banners = {
            DeploymentMode.PRODUCTION: """
╔══════════════════════════════════════════════════════════════╗
║              🚀 QUANTUM CRYPTO TRADING SYSTEM 🚀             ║
║                     PRODUCTION MODE                          ║
╚══════════════════════════════════════════════════════════════╝""",
            DeploymentMode.DEVELOPMENT: """
╔══════════════════════════════════════════════════════════════╗
║              🛠️  QUANTUM CRYPTO TRADING SYSTEM 🛠️           ║
║                    DEVELOPMENT MODE                          ║
╚══════════════════════════════════════════════════════════════╝""",
            DeploymentMode.FREE_TIER: """
╔══════════════════════════════════════════════════════════════╗
║        🚀 QUANTUM CRYPTO TRADING SYSTEM - FREE TIER 🚀       ║
║                   🆓 100% FREE VERSION 🆓                     ║
║              Paper Trading (No Real Money Risk)             ║
╚══════════════════════════════════════════════════════════════╝""",
            DeploymentMode.SIMPLE: """
╔══════════════════════════════════════════════════════════════╗
║              📊 CRYPTO TRADING SYSTEM - SIMPLE 📊            ║
║                    Testing & Development                     ║
╚══════════════════════════════════════════════════════════════╝"""
        }
        
        banner = mode_banners.get(self.mode, "Trading System Starting...")
        print(banner)
        
    def check_requirements(self) -> bool:
        """Check system requirements based on mode"""
        self.logger.info(f"🔍 Checking requirements for {self.mode.value} mode...")
        
        try:
            # Check basic Python requirements
            import fastapi
            import uvicorn
            
            if self.mode == DeploymentMode.PRODUCTION:
                # Additional production requirements
                import prometheus_client
                import redis
                
            self.logger.info("✅ Requirements check passed")
            return True
            
        except ImportError as e:
            self.logger.error(f"❌ Missing required dependency: {e}")
            return False
            
    def run(self):
        """Run the trading system in the specified mode"""
        self.display_startup_banner()
        
        if not self.check_requirements():
            sys.exit(1)
            
        # Set environment variables
        os.environ["DEPLOYMENT_MODE"] = self.mode.value
        
        # Get configuration
        config = self.get_app_config()
        app_module = self.get_app_module()
        
        self.logger.info(f"🚀 Starting {self.mode.value} mode on {config['host']}:{config['port']}")
        
        try:
            # Run the application
            uvicorn.run(
                app_module,
                host=config["host"],
                port=config["port"],
                reload=config["reload"],
                workers=config["workers"] if not config["reload"] else 1,
                log_level=config["log_level"]
            )
        except KeyboardInterrupt:
            self.logger.info("👋 Trading system stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Failed to start trading system: {e}")
            sys.exit(1)

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description="Quantum Crypto Trading System")
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=[mode.value for mode in DeploymentMode],
        default=DeploymentMode.DEVELOPMENT.value,
        help="Deployment mode"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to"
    )
    
    args = parser.parse_args()
    
    # Create and run launcher
    mode = DeploymentMode(args.mode)
    launcher = TradingSystemLauncher(mode)
    
    # Override config with command line args if provided
    if args.host != "0.0.0.0" or args.port != 8000:
        os.environ["APP_HOST"] = args.host
        os.environ["APP_PORT"] = str(args.port)
    
    launcher.run()

if __name__ == "__main__":
    main()