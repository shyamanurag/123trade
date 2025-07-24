#!/usr/bin/env python3
"""
Auto-fix common style issues in Python files
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("Auto-fixing common style issues...")
    print("=" * 50)
    
    # Run autopep8 to fix common PEP8 issues
    print("\n1. Running autopep8 to fix whitespace and formatting issues...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "autopep8", "--quiet"
        ])
        
        # Fix main Python files
        main_files = [
            "main.py",
            "websocket_main.py",
            "websocket_manager.py",
            "database_manager.py",
            "start_trading_system.py"
        ]
        
        for file in main_files:
            if Path(file).exists():
                print(f"   Fixing {file}...")
                subprocess.run([
                    sys.executable, "-m", "autopep8",
                    "--in-place",
                    "--aggressive",
                    "--max-line-length=120",
                    file
                ])
        
        print("   ✓ Whitespace and formatting issues fixed")
        
    except Exception as e:
        print(f"   ✗ Error running autopep8: {e}")
    
    # Run isort to fix import order
    print("\n2. Running isort to fix import order...")
    try:
        # Fix import order
        subprocess.run([
            sys.executable, "-m", "isort",
            ".",
            "--profile", "black",
            "--line-length", "120",
            "--skip", "venv,env,node_modules"
        ])
        print("   ✓ Import order fixed")
        
    except Exception as e:
        print(f"   ✗ Error running isort: {e}")
    
    # Run black for consistent formatting
    print("\n3. Running black for consistent formatting...")
    try:
        subprocess.run([
            sys.executable, "-m", "black",
            ".",
            "--line-length", "120",
            "--exclude", "venv|env|node_modules|migrations"
        ])
        print("   ✓ Code formatting standardized")
        
    except Exception as e:
        print(f"   ✗ Error running black: {e}")
    
    print("\n" + "=" * 50)
    print("Auto-fix complete!")
    print("\nNote: Some issues may require manual fixing:")
    print("- Unused imports (F401)")
    print("- Redefined functions (F811)")
    print("- Unused variables (F841)")
    print("\nRun 'python scripts/focused_analysis.py' to see remaining issues.")

if __name__ == "__main__":
    main() 