#!/usr/bin/env python3
"""
Code Analysis Script
Runs various code quality tools and generates reports
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def run_command(command, output_file=None):
    """Run a command and optionally save output to file"""
    print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )
        
        output = result.stdout + result.stderr
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(f"Command: {' '.join(command)}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Return code: {result.returncode}\n")
                f.write("-" * 80 + "\n")
                f.write(output)
        
        if result.returncode == 0:
            print(f"✓ {command[0]} completed successfully")
        else:
            print(f"✗ {command[0]} completed with errors (code: {result.returncode})")
            
        return result.returncode == 0
        
    except FileNotFoundError:
        print(f"✗ {command[0]} not found. Please install it first.")
        if output_file:
            with open(output_file, 'w') as f:
                f.write(f"Error: {command[0]} not found. Please install it.\n")
        return False
    except Exception as e:
        print(f"✗ Error running {command[0]}: {e}")
        return False

def main():
    """Run all code analysis tools"""
    print("=" * 80)
    print("Code Quality Analysis")
    print("=" * 80)
    
    # Create reports directory
    reports_dir = Path("code_analysis_reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Define tools and their commands
    tools = [
        {
            "name": "pylint",
            "command": [sys.executable, "-m", "pylint", ".", "--output-format=text"],
            "output": reports_dir / "pylint_report.txt",
            "install": "pip install pylint"
        },
        {
            "name": "mypy",
            "command": [sys.executable, "-m", "mypy", ".", "--ignore-missing-imports"],
            "output": reports_dir / "mypy_report.txt",
            "install": "pip install mypy"
        },
        {
            "name": "bandit",
            "command": [sys.executable, "-m", "bandit", "-r", ".", "-f", "txt"],
            "output": reports_dir / "bandit_report.txt",
            "install": "pip install bandit"
        },
        {
            "name": "flake8",
            "command": [sys.executable, "-m", "flake8", ".", "--max-line-length=120"],
            "output": reports_dir / "flake8_report.txt",
            "install": "pip install flake8"
        },
        {
            "name": "black",
            "command": [sys.executable, "-m", "black", ".", "--check", "--diff"],
            "output": reports_dir / "black_report.txt",
            "install": "pip install black"
        }
    ]
    
    # Run each tool
    results = {}
    for tool in tools:
        print(f"\n{tool['name'].upper()}")
        print("-" * 40)
        
        success = run_command(tool["command"], tool["output"])
        results[tool["name"]] = success
        
        if not success and "not found" in str(tool["output"].read_text() if tool["output"].exists() else ""):
            print(f"  Install with: {tool['install']}")
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    summary_file = reports_dir / "summary.txt"
    with open(summary_file, 'w') as f:
        f.write("Code Analysis Summary\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        for tool_name, success in results.items():
            status = "PASSED" if success else "FAILED"
            print(f"{tool_name:<15} {status}")
            f.write(f"{tool_name:<15} {status}\n")
        
        f.write("\nReports generated in: code_analysis_reports/\n")
    
    print(f"\nAnalysis complete. Check reports in '{reports_dir}/' directory.")
    print(f"Summary available at: {summary_file}")
    
    # Return non-zero if any tool failed
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
