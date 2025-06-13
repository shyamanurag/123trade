# core/orchestrator.py
"""
Service Orchestrator
Manages the different FastAPI applications and their interactions
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI
import uvicorn
from multiprocessing import Process

from config.config_manager import config_manager
from config.loader import config_loader
from utils.async_utils import AsyncTaskManager

logger = logging.getLogger(__name__)

class ServiceOrchestrator:
    """Orchestrates different services in the trading system"""
    
    def __init__(self):
        self.processes: Dict[str, Process] = {}
        self.task_manager = AsyncTaskManager()
        self.config = config_loader.load_config("config.yaml", env="production")
        
    def start_main_api(self) -> None:
        """Start the main trading system API"""
        process = Process(
            target=uvicorn.run,
            args=("trading-system.src.main:app",),
            kwargs={
                "host": self.config["app"]["host"],
                "port": self.config["app"]["port"],
                "workers": self.config["app"]["workers"],
            }
        )
        process.start()
        self.processes["main_api"] = process
        
    def start_security_api(self) -> None:
        """Start the security API service"""
        process = Process(
            target=uvicorn.run,
            args=("security.main:app",),
            kwargs={
                "host": self.config["app"]["host"],
                "port": int(self.config["endpoints"]["security_api"].split(":")[-1]),
                "workers": 2,  # Security service uses fewer workers
            }
        )
        process.start()
        self.processes["security_api"] = process
        
    def start_dash_app(self) -> None:
        """Start the Dash frontend application"""
        process = Process(
            target=self._run_dash,
            args=(
                self.config["app"]["host"],
                int(self.config["endpoints"]["dash_app"].split(":")[-1])
            )
        )
        process.start()
        self.processes["dash"] = process
        
    def _run_dash(self, host: str, port: int) -> None:
        """Run Dash application"""
        from frontend.app import app
        app.run_server(
            host=host,
            port=port,
            debug=self.config["app"]["debug"]
        )
        
    async def start_all(self) -> None:
        """Start all services"""
        try:
            # Start services in order
            self.start_security_api()
            await asyncio.sleep(2)  # Wait for security service to initialize
            
            self.start_main_api()
            await asyncio.sleep(2)  # Wait for main API to initialize
            
            self.start_dash_app()
            
            logger.info("All services started successfully")
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            await self.stop_all()
            raise
            
    async def stop_all(self) -> None:
        """Stop all services"""
        try:
            # Stop all processes
            for name, process in self.processes.items():
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
                logger.info(f"Stopped {name} service")
                
            # Stop all async tasks
            await self.task_manager.stop_all()
            
            logger.info("All services stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping services: {e}")
            raise
            
    def is_running(self, service_name: str) -> bool:
        """Check if a service is running"""
        return (
            service_name in self.processes
            and self.processes[service_name].is_alive()
        )
        
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all services"""
        return {
            "main_api": self.is_running("main_api"),
            "security_api": self.is_running("security_api"),
            "dash": self.is_running("dash"),
        }

# Initialize orchestrator
orchestrator = ServiceOrchestrator()
