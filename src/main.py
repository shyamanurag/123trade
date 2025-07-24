"""
Main entry point for the trading system.
This is a thin wrapper around the bootstrap module that handles the actual application setup.
"""
import uvicorn
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from bootstrap import app

if __name__ == "__main__":
    uvicorn.run(
        "src.bootstrap:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 