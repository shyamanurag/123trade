"""
Quick Start Script - Deploy Trading System Locally
Simple deployment without complex health checks
"""

import os
import subprocess
import sys
from pathlib import Path

def setup_environment():
    """Load environment variables"""
    try:
        from dotenv import load_dotenv
        load_dotenv('config/local_deployment.env')
        load_dotenv('config/sharekhan_credentials.env')
        print("✅ Environment loaded")
    except Exception as e:
        print(f"⚠️  Environment loading failed: {e}")

def create_directories():
    """Create necessary directories"""
    directories = ['logs', 'data', 'static']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Directories created")

def main():
    print("🚀 QUICK START - TRADING SYSTEM")
    print("=" * 40)
    
    # Setup
    setup_environment()
    create_directories()
    
    print("\n🎯 STARTING SERVER...")
    print("=" * 40)
    print("🌐 URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs") 
    print("🔐 ShareKhan Auth: http://localhost:8000/auth/sharekhan")
    print("\n🛑 Press Ctrl+C to stop")
    print("=" * 40)
    
    # Start server
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")

if __name__ == "__main__":
    main() 