#!/usr/bin/env python3
"""
Quick Code Analysis Script
Runs essential code quality checks quickly
"""

import subprocess
import sys
from pathlib import Path

def check_tool(tool_name):
    """Check if a tool is installed"""
    try:
        subprocess.run([sys.executable, "-m", tool_name, "--version"], 
                      capture_output=True, check=False)
        return True
    except:
        return False

def main():
    print("Quick Code Analysis")
    print("=" * 50)
    
    # Check for required tools
    tools = ["flake8", "mypy", "bandit"]
    missing = [tool for tool in tools if not check_tool(tool)]
    
    if missing:
        print("Missing tools:", ", ".join(missing))
        print("\nInstall with:")
        print(f"pip install {' '.join(missing)}")
        return 1
    
    # Run flake8 for style issues
    print("\n1. Running flake8 (style checker)...")
    subprocess.run([
        sys.executable, "-m", "flake8", 
        "--max-line-length=120",
        "--exclude=venv,env,node_modules,dist,build,.git",
        "--count",
        "--statistics",
        "."
    ])
    
    # Run mypy for type checking
    print("\n2. Running mypy (type checker)...")
    subprocess.run([
        sys.executable, "-m", "mypy",
        "--ignore-missing-imports",
        "--exclude", "venv|env|node_modules",
        "."
    ])
    
    # Run bandit for security issues
    print("\n3. Running bandit (security checker)...")
    subprocess.run([
        sys.executable, "-m", "bandit",
        "-r", ".",
        "-ll",  # Only show medium and high severity
        "-x", "venv,env,node_modules,tests"
    ])
    
    print("\n" + "=" * 50)
    print("Quick analysis complete!")
    print("For detailed reports, run: python scripts/code_analysis.py")

if __name__ == "__main__":
    sys.exit(main()) 