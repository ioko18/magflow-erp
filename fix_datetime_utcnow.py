#!/usr/bin/env python3
"""
Script to replace datetime.utcnow() with datetime.now(UTC) across the codebase.
This fixes the deprecated API usage for Python 3.12+ compatibility.
"""

import os
import re
from pathlib import Path


def fix_datetime_imports(content: str) -> tuple[str, bool]:
    """Add UTC to datetime imports if not present."""
    modified = False
    
    # Pattern 1: from datetime import datetime
    pattern1 = r'^from datetime import (.+)$'
    
    for match in re.finditer(pattern1, content, re.MULTILINE):
        imports = match.group(1)
        # Check if UTC is already imported
        if 'UTC' not in imports:
            # Add UTC to the import
            new_imports = imports.strip()
            if new_imports.endswith(','):
                new_imports = f"UTC, {new_imports}"
            else:
                new_imports = f"UTC, {new_imports}"
            
            old_line = match.group(0)
            new_line = f"from datetime import {new_imports}"
            content = content.replace(old_line, new_line, 1)
            modified = True
            break  # Only fix the first occurrence
    
    return content, modified


def fix_datetime_utcnow(content: str) -> tuple[str, int]:
    """Replace datetime.utcnow() with datetime.now(UTC)."""
    pattern = r'datetime\.utcnow\(\)'
    count = len(re.findall(pattern, content))
    
    if count > 0:
        content = re.sub(pattern, 'datetime.now(UTC)', content)
    
    return content, count


def process_file(filepath: Path) -> dict:
    """Process a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        
        # First, fix imports
        content, import_modified = fix_datetime_imports(content)
        
        # Then, replace datetime.utcnow()
        content, replacements = fix_datetime_utcnow(content)
        
        # Only write if changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'status': 'modified',
                'replacements': replacements,
                'import_added': import_modified
            }
        
        return {'status': 'unchanged', 'replacements': 0, 'import_added': False}
    
    except Exception as e:
        return {'status': 'error', 'error': str(e), 'replacements': 0}


def main():
    """Main function to process all Python files."""
    app_dir = Path('app')
    
    if not app_dir.exists():
        print("Error: 'app' directory not found")
        return
    
    # Find all Python files with datetime.utcnow()
    python_files = []
    for filepath in app_dir.rglob('*.py'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if 'datetime.utcnow()' in f.read():
                    python_files.append(filepath)
        except Exception:
            continue
    
    print(f"Found {len(python_files)} files with datetime.utcnow()")
    print("=" * 70)
    
    total_replacements = 0
    modified_files = []
    error_files = []
    
    for filepath in python_files:
        result = process_file(filepath)
        
        if result['status'] == 'modified':
            modified_files.append(filepath)
            total_replacements += result['replacements']
            print(f"✅ {filepath.relative_to(app_dir.parent)}: {result['replacements']} replacements")
        elif result['status'] == 'error':
            error_files.append((filepath, result['error']))
            print(f"❌ {filepath.relative_to(app_dir.parent)}: ERROR - {result['error']}")
    
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  Files processed: {len(python_files)}")
    print(f"  Files modified: {len(modified_files)}")
    print(f"  Total replacements: {total_replacements}")
    print(f"  Errors: {len(error_files)}")
    
    if error_files:
        print("\nFiles with errors:")
        for filepath, error in error_files:
            print(f"  - {filepath}: {error}")


if __name__ == '__main__':
    main()
