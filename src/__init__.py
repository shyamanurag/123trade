"""
Trading System Package
"""
import os
import sys

# Add the src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The src package
# This empty file marks the src directory as a Python package so that
# imports such as `from src.core.websocket_manager import WebSocketManager`
# work correctly. 