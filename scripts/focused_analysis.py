#!/usr/bin/env python3
"""
Focused Code Analysis Script
Analyzes only the main Python files, excluding tests and generated files
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("Focused Code Analysis - Main Files Only")
    print("=" * 60)
    
    # Define main Python files to analyze
    main_files = [
        "main.py",
        "websocket_main.py",
        "websocket_manager.py",
        "database_manager.py",
        "start_trading_system.py",
        "src/api/*.py",
        "src/core/*.py",
        "common/*.py",
        "data/*.py",
        "scripts/*.py"
    ]
    
    # Exclude patterns
    exclude_patterns = [
        "--exclude=venv,env,node_modules,dist,build,.git,__pycache__",
        "--exclude=tests,test_*,*_test.py",
        "--exclude=migrations,alembic",
        "--exclude=static,templates,frontend"
    ]
    
    # Run flake8 with specific files
    print("\n1. Flake8 Analysis (Style Issues)")
    print("-" * 40)
    flake8_cmd = [
        sys.executable, "-m", "flake8",
        "--max-line-length=120",
        "--ignore=E501,W503,E203",  # Ignore long lines, line break before binary operator
        "--count",
        "--statistics"
    ] + exclude_patterns + main_files
    
    result = subprocess.run(flake8_cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    # Run bandit on main files only
    print("\n2. Bandit Security Analysis")
    print("-" * 40)
    bandit_cmd = [
        sys.executable, "-m", "bandit",
        "-r", ".",
        "-ll",  # Only medium and high severity
        "-f", "screen",
        "-x", "venv,env,node_modules,tests,frontend"
    ]
    
    subprocess.run(bandit_cmd)
    
    # Quick type check on main.py
    print("\n3. Type Check - main.py")
    print("-" * 40)
    mypy_cmd = [
        sys.executable, "-m", "mypy",
        "--ignore-missing-imports",
        "--no-error-summary",
        "main.py"
    ]
    
    subprocess.run(mypy_cmd)
    
    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("\nFor full analysis, run: python scripts/code_analysis.py")

if __name__ == "__main__":
    main() 