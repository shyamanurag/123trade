"""Top-level core package.

This package exposes the modules located in `src/core` so that they can be
imported simply as `import core.models` etc. It ensures the `src` directory is
on `sys.path` when the package is imported so that unit-tests and application
code do not have to manipulate `PYTHONPATH` manually.

Enhanced with new components for production deployment.
"""

import importlib
import pkgutil
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Add the project `src` directory to sys.path so that `src.core` becomes
# importable regardless of the working directory or environment.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Lazily re-export the submodules inside ``src.core`` so callers can just do
# ``import core.models`` instead of ``from src.core import models``.
# We only eagerly import ``src.core`` itself so that attribute access works.
try:
    importlib.import_module("src.core")
    logger.debug("Successfully imported src.core module")
except ImportError as e:
    logger.warning(f"Could not import src.core module: {e}")

# Enhanced components - import with error handling for deployment flexibility
ENHANCED_COMPONENTS = {
    "api_standards": "src.core.api_standards",
    "enhanced_exceptions": "src.core.enhanced_exceptions", 
    "enhanced_monitoring": "src.core.enhanced_monitoring",
    "optimized_database_manager": "src.core.optimized_database_manager"
}

# Track which enhanced components are available
AVAILABLE_COMPONENTS = {}

for component_name, module_path in ENHANCED_COMPONENTS.items():
    try:
        module = importlib.import_module(module_path)
        AVAILABLE_COMPONENTS[component_name] = module
        logger.debug(f"Enhanced component available: {component_name}")
    except ImportError as e:
        logger.warning(f"Enhanced component {component_name} not available: {e}")
        AVAILABLE_COMPONENTS[component_name] = None

# Provide easy access to enhanced features
def get_enhanced_component(name: str):
    """Get an enhanced component if available"""
    return AVAILABLE_COMPONENTS.get(name)

def is_component_available(name: str) -> bool:
    """Check if an enhanced component is available"""
    return AVAILABLE_COMPONENTS.get(name) is not None

def get_available_components() -> dict:
    """Get all available enhanced components"""
    return {k: v for k, v in AVAILABLE_COMPONENTS.items() if v is not None}

# Export enhanced features status
ENHANCED_FEATURES = {
    "api_standards": is_component_available("api_standards"),
    "enhanced_exceptions": is_component_available("enhanced_exceptions"),
    "enhanced_monitoring": is_component_available("enhanced_monitoring"),
    "optimized_database": is_component_available("optimized_database_manager")
}

# Initialize enhanced components if available
def initialize_enhanced_system():
    """Initialize enhanced system components"""
    initialized = []
    
    # Initialize monitoring system
    if is_component_available("enhanced_monitoring"):
        try:
            monitoring_module = get_enhanced_component("enhanced_monitoring")
            if monitoring_module and hasattr(monitoring_module, 'get_monitoring_system'):
                monitoring_system = monitoring_module.get_monitoring_system()
                initialized.append("monitoring")
                logger.info("Enhanced monitoring system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize monitoring system: {e}")
    
    # Initialize database manager
    if is_component_available("optimized_database_manager"):
        try:
            db_module = get_enhanced_component("optimized_database_manager")
            if db_module and hasattr(db_module, 'get_db_manager'):
                db_manager = db_module.get_db_manager()
                initialized.append("database")
                logger.info("Optimized database manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
    
    logger.info(f"Enhanced system initialized with components: {', '.join(initialized)}")
    return initialized

# Graceful fallback for missing components
def ensure_compatibility():
    """Ensure compatibility when enhanced components are missing"""
    missing_components = [name for name, available in ENHANCED_FEATURES.items() if not available]
    
    if missing_components:
        logger.warning(f"Running with reduced functionality. Missing components: {', '.join(missing_components)}")
        logger.warning("Install all dependencies from requirements.txt for full enhanced functionality")
    else:
        logger.info("All enhanced components available - running with full functionality")

# Anything that tries ``import core.models`` will trigger regular import
# machinery which now resolves to ``src.core.models`` thanks to the updated
# `sys.path`.

# Auto-initialize enhanced features on import
try:
    ensure_compatibility()
    if any(ENHANCED_FEATURES.values()):
        initialize_enhanced_system()
except Exception as e:
    logger.error(f"Error during enhanced system initialization: {e}")
    logger.warning("Falling back to basic functionality")

# Export enhanced features information
__all__ = [
    "ENHANCED_FEATURES", 
    "get_enhanced_component", 
    "is_component_available",
    "get_available_components",
    "initialize_enhanced_system",
    "ensure_compatibility"
]
