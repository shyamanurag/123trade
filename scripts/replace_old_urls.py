#!/usr/bin/env python3
"""
Script to replace old Digital Ocean URLs with new ones across the entire codebase.
This will scan all relevant files and update any hardcoded URLs.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict

# Define old and new URLs
OLD_URL = "algoauto-9gx56.ondigitalocean.app"
NEW_URL = "algoauto-9gx56.ondigitalocean.app"

# File extensions to scan
SCAN_EXTENSIONS = [
    '.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yaml', '.yml',
    '.env', '.env.example', '.env.production', '.env.development',
    '.md', '.txt', '.html', '.css', '.scss'
]

# Directories to skip
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.pytest_cache', 
    'dist', 'build', '.next', 'coverage', 'venv', 'env',
    '.venv', 'htmlcov', '.tox', 'egg-info'
}

# Files to skip
SKIP_FILES = {
    'package-lock.json', 'yarn.lock', 'poetry.lock',
    'Pipfile.lock', '.gitignore', '.dockerignore'
}


def should_scan_file(file_path: Path) -> bool:
    """Check if a file should be scanned."""
    # Skip if in skip list
    if file_path.name in SKIP_FILES:
        return False
    
    # Skip if no extension match
    if file_path.suffix.lower() not in SCAN_EXTENSIONS:
        # Also check files without extensions (like Dockerfile)
        if file_path.suffix == '' and file_path.name not in ['Dockerfile', 'Makefile']:
            return False
    
    return True


def find_files_to_scan(root_dir: str) -> List[Path]:
    """Find all files that should be scanned for URL replacement."""
    files_to_scan = []
    root_path = Path(root_dir)
    
    for path in root_path.rglob('*'):
        # Skip directories
        if path.is_dir():
            continue
            
        # Skip if any parent directory is in skip list
        if any(part in SKIP_DIRS for part in path.parts):
            continue
            
        # Check if file should be scanned
        if should_scan_file(path):
            files_to_scan.append(path)
    
    return files_to_scan


def scan_file_for_urls(file_path: Path) -> List[Tuple[int, str]]:
    """Scan a file for old URLs and return line numbers and content."""
    matches = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines, 1):
            if OLD_URL in line:
                matches.append((i, line.strip()))
                
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return matches


def replace_urls_in_file(file_path: Path, dry_run: bool = False) -> int:
    """Replace old URLs with new URLs in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count occurrences
        count = content.count(OLD_URL)
        
        if count > 0:
            # Replace URLs
            new_content = content.replace(OLD_URL, NEW_URL)
            
            if not dry_run:
                # Write back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    
            return count
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        
    return 0


def main(dry_run: bool = False):
    """Main function to scan and replace URLs."""
    # Get the project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print(f"Scanning project at: {project_root}")
    print(f"Looking for: {OLD_URL}")
    print(f"Replacing with: {NEW_URL}")
    print(f"Dry run: {dry_run}")
    print("-" * 80)
    
    # Find all files to scan
    files_to_scan = find_files_to_scan(project_root)
    print(f"Found {len(files_to_scan)} files to scan")
    
    # Track statistics
    files_with_matches = 0
    total_replacements = 0
    file_results: Dict[Path, List[Tuple[int, str]]] = {}
    
    # Scan all files
    for file_path in files_to_scan:
        matches = scan_file_for_urls(file_path)
        if matches:
            files_with_matches += 1
            file_results[file_path] = matches
            
            # Perform replacement
            count = replace_urls_in_file(file_path, dry_run)
            total_replacements += count
    
    # Print results
    print("\n" + "=" * 80)
    print("SCAN RESULTS")
    print("=" * 80)
    
    if file_results:
        print(f"\nFound old URLs in {files_with_matches} files:")
        print(f"Total occurrences: {total_replacements}")
        
        for file_path, matches in file_results.items():
            relative_path = file_path.relative_to(project_root)
            print(f"\n📄 {relative_path} ({len(matches)} occurrences):")
            for line_num, line_content in matches[:3]:  # Show first 3 matches
                print(f"   Line {line_num}: {line_content[:100]}...")
            if len(matches) > 3:
                print(f"   ... and {len(matches) - 3} more")
                
        if not dry_run:
            print(f"\n✅ Successfully replaced {total_replacements} occurrences in {files_with_matches} files")
        else:
            print(f"\n🔍 DRY RUN: Would replace {total_replacements} occurrences in {files_with_matches} files")
            print("   Run with --execute to perform actual replacements")
    else:
        print("\n✨ No occurrences of old URL found! Your codebase is clean.")
    
    # Additional checks for common patterns
    print("\n" + "=" * 80)
    print("ADDITIONAL CHECKS")
    print("=" * 80)
    
    # Check for partial URLs or variations
    variations = [
        f"https://{OLD_URL}",
        f"http://{OLD_URL}",
        f"wss://{OLD_URL}",
        f"ws://{OLD_URL}",
        OLD_URL.replace('-', '_'),  # Check for underscore variations
        OLD_URL.upper(),  # Check for uppercase
    ]
    
    print("\nChecking for URL variations...")
    for variation in variations:
        variation_found = False
        for file_path in files_to_scan:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if variation in content and variation != OLD_URL:
                    if not variation_found:
                        print(f"\n⚠️  Found variation: {variation}")
                        variation_found = True
                    relative_path = file_path.relative_to(project_root)
                    print(f"   In: {relative_path}")
            except:
                pass


if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        print("🚀 Running in EXECUTE mode - files will be modified!")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() == 'yes':
            main(dry_run=False)
        else:
            print("Aborted.")
    else:
        print("🔍 Running in DRY RUN mode - no files will be modified")
        main(dry_run=True) 