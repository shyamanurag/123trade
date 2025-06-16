#!/usr/bin/env python
"""
Apply Production Enhancements

This script adds production enhancement imports to the main.py file.
It adds imports at the top of the file and adds code to integrate the
production enhancements after the app initialization.
"""

import os
import re
import shutil
import sys
from datetime import datetime

def backup_file(file_path):
    """Create a backup of the file before modifying it"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def insert_import(content):
    """Insert the production enhancer import at the appropriate location"""
    # Find the last import block
    import_pattern = r"(from .+? import .+?)(\n\n)"
    last_import_match = list(re.finditer(import_pattern, content))
    
    if not last_import_match:
        print("Could not find import section. Using fallback location.")
        # Fallback to insert after the last import line
        lines = content.split('\n')
        import_lines = [i for i, line in enumerate(lines) if line.startswith('import ') or line.startswith('from ')]
        if import_lines:
            import_idx = import_lines[-1] + 1
            lines.insert(import_idx, "\n# Import production enhancements\nfrom core.production_enhancer import integrate_with_main")
            return '\n'.join(lines)
        else:
            return "# Import production enhancements\nfrom core.production_enhancer import integrate_with_main\n\n" + content
    
    # Insert after the last import block
    last_match = last_import_match[-1]
    insert_pos = last_match.end() - 1  # -1 to insert before the last newline
    
    new_content = content[:insert_pos] + "\n# Import production enhancements\nfrom core.production_enhancer import integrate_with_main" + content[insert_pos:]
    return new_content

def insert_integration_code(content):
    """Insert the code that integrates production enhancements"""
    # Look for a good location to insert the code - after CORS middleware setup
    cors_pattern = r"app\.add_middleware\(\s*CORSMiddleware[^}]+?\)\s*\n"
    cors_matches = list(re.finditer(cors_pattern, content))
    
    if cors_matches:
        # Insert after CORS middleware
        insert_pos = cors_matches[-1].end()
        new_content = content[:insert_pos] + "\n# Integrate production enhancements\ntry:\n    integrate_with_main(app, redis_client)\n    logger.info(\"✅ Production enhancements integrated\")\nexcept Exception as e:\n    logger.error(f\"❌ Failed to integrate production enhancements: {e}\")\n" + content[insert_pos:]
        return new_content
    
    # Fallback: Look for routers being included
    router_pattern = r"app\.include_router\([^)]+\)\s*\n"
    router_matches = list(re.finditer(router_pattern, content))
    
    if router_matches:
        # Insert before the first router
        insert_pos = router_matches[0].start()
        new_content = content[:insert_pos] + "# Integrate production enhancements\ntry:\n    integrate_with_main(app, redis_client)\n    logger.info(\"✅ Production enhancements integrated\")\nexcept Exception as e:\n    logger.error(f\"❌ Failed to integrate production enhancements: {e}\")\n\n" + content[insert_pos:]
        return new_content
    
    # If all else fails, add at the end of the file
    print("Warning: Could not find ideal location to insert integration code. Adding at the end.")
    return content + "\n\n# Integrate production enhancements\ntry:\n    integrate_with_main(app, redis_client)\n    logger.info(\"✅ Production enhancements integrated\")\nexcept Exception as e:\n    logger.error(f\"❌ Failed to integrate production enhancements: {e}\")\n"

def apply_enhancements(file_path='main.py'):
    """Apply production enhancements to the main.py file"""
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        sys.exit(1)
        
    # Create backup
    backup_file(file_path)
        
    # Read the file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    # Insert the import
    content = insert_import(content)
    
    # Insert the integration code
    content = insert_integration_code(content)
    
    # Write the modified content back to the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully applied production enhancements to {file_path}")
    except Exception as e:
        print(f"Error writing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    file_path = 'main.py'
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
    apply_enhancements(file_path)