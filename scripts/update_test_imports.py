#!/usr/bin/env python3
"""
Script to update imports in test files after moving them to the tests directory.
"""
import os
import re
from pathlib import Path

# Define the project root
PROJECT_ROOT = Path(__file__).parent

# Define the test directory
TEST_DIR = PROJECT_ROOT / 'tests'

# Define import patterns to update
IMPORT_PATTERNS = [
    # Update relative imports
    (r'from \.\.', 'from app'),
    (r'from \.\.\.', 'from app'),
    # Update absolute imports
    (r'from app\.', 'from app.'),
    # Update sys.path modifications
    (r'sys\.path\.insert\(0,.*\)', "# sys.path modification removed - use pytest's pythonpath"),
]

def update_imports(file_path):
    """Update imports in a single file."""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Update imports based on patterns
        for pattern, replacement in IMPORT_PATTERNS:
            content = re.sub(pattern, replacement, content)

        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated imports in {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Update imports in all test files."""
    updated_count = 0

    # Process all Python files in the tests directory
    for root, _, files in os.walk(TEST_DIR):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                file_path = Path(root) / file
                if update_imports(file_path):
                    updated_count += 1

    print(f"\n✅ Updated imports in {updated_count} test files")

if __name__ == "__main__":
    main()
