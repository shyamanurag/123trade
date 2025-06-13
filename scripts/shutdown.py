"""
Graceful Shutdown Script
Handles clean shutdown of the trading system
"""

import asyncio
import logging
import signal
import sys
from typing import List, Optional
import aiohttp
import yaml
from datetime import datetime

logger = logging.getLogger(__name__)

class GracefulShutdown:
    def __init__(self, config_path: str = 'config/shutdown.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        self.components = []
        self._shutdown_event = asyncio.Event()
        self._shutdown_timeout = self.config.get('shutdown_timeout', 30)
        self._force_shutdown = False

    def _load_config(self) -> dict:
        """Load shutdown configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    async def register_component(self, component):
        """Register a component for shutdown"""
        self.components.append(component)

    async def start(self):
        """Start shutdown handler"""
        # Set up signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)

        logger.info("Shutdown handler started")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        asyncio.create_task(self.shutdown())

    async def shutdown(self, force: bool = False):
        """Initiate graceful shutdown"""
        if self._shutdown_event.is_set():
            return

        self._shutdown_event.set()
        self._force_shutdown = force

        try:
            # Start shutdown timer
            shutdown_task = asyncio.create_task(self._shutdown_timeout_handler())
            
            # Shutdown components
            await self._shutdown_components()
            
            # Cancel shutdown timer
            shutdown_task.cancel()
            
            logger.info("Shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            if not self._force_shutdown:
                raise

    async def _shutdown_timeout_handler(self):
        """Handle shutdown timeout"""
        try:
            await asyncio.sleep(self._shutdown_timeout)
            if not self._force_shutdown:
                logger.warning("Shutdown timeout reached, forcing shutdown")
                self._force_shutdown = True
                await self._force_shutdown_components()
        except asyncio.CancelledError:
            pass

    async def _shutdown_components(self):
        """Shutdown all registered components"""
        shutdown_tasks = []
        
        for component in self.components:
            if hasattr(component, 'stop'):
                shutdown_tasks.append(self._shutdown_component(component))
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

    async def _shutdown_component(self, component):
        """Shutdown a single component"""
        try:
            if asyncio.iscoroutinefunction(component.stop):
                await component.stop()
            else:
                component.stop()
            logger.info(f"Component {component.__class__.__name__} stopped")
        except Exception as e:
            logger.error(f"Error stopping component {component.__class__.__name__}: {e}")
            if not self._force_shutdown:
                raise

    async def _force_shutdown_components(self):
        """Force shutdown all components"""
        for component in self.components:
            try:
                if hasattr(component, 'force_stop'):
                    if asyncio.iscoroutinefunction(component.force_stop):
                        await component.force_stop()
                    else:
                        component.force_stop()
                logger.info(f"Component {component.__class__.__name__} force stopped")
            except Exception as e:
                logger.error(f"Error force stopping component {component.__class__.__name__}: {e}")

    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self._shutdown_event.wait()

async def main():
    """Main shutdown script"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create shutdown handler
    shutdown_handler = GracefulShutdown()
    await shutdown_handler.start()
    
    # Wait for shutdown signal
    await shutdown_handler.wait_for_shutdown()
    
    # Perform shutdown
    await shutdown_handler.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown interrupted by user")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        sys.exit(1) 