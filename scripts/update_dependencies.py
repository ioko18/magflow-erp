#!/usr/bin/env python3
"""
Script to update Python dependencies to their latest stable versions.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[str, str, int]:
    """Run a shell command and return stdout, stderr, and return code."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    return result.stdout, result.stderr, result.returncode


def get_outdated_packages() -> List[Dict[str, str]]:
    """Get a list of outdated packages and their latest versions."""
    cmd = ["pip", "list", "--outdated", "--format", "json"]
    stdout, stderr, returncode = run_command(cmd)

    if returncode != 0:
        print(f"Error getting outdated packages: {stderr}")
        return []

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        print(f"Error parsing package list: {e}")
        return []


def update_package(package_name: str, version: Optional[str] = None) -> bool:
    """Update a specific package to the latest version or a specific version."""
    if version:
        cmd = ["pip", "install", "-U", f"{package_name}=={version}"]
    else:
        cmd = ["pip", "install", "-U", package_name]

    print(f"Updating {package_name}...")
    stdout, stderr, returncode = run_command(cmd)

    if returncode != 0:
        print(f"Error updating {package_name}: {stderr}")
        return False

    print(f"Successfully updated {package_name}")
    return True


def update_requirements_file(requirements_file: Path) -> bool:
    """Update the requirements file with the current package versions."""
    if not requirements_file.exists():
        print(f"Requirements file {requirements_file} not found.")
        return False

    cmd = ["pip", "freeze"]
    stdout, stderr, returncode = run_command(cmd)

    if returncode != 0:
        print(f"Error getting installed packages: {stderr}")
        return False

    try:
        with open(requirements_file, "w", encoding="utf-8") as f:
            f.write(stdout)
        print(f"Updated {requirements_file}")
        return True
    except IOError as e:
        print(f"Error writing to {requirements_file}: {e}")
        return False


def main():
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    requirements_file = project_root / "requirements.txt"

    print("Checking for outdated packages...")
    outdated_packages = get_outdated_packages()

    if not outdated_packages:
        print("All packages are up to date!")
        return

    print(f"Found {len(outdated_packages)} outdated packages:")
    for i, pkg in enumerate(outdated_packages, 1):
        print(f"{i}. {pkg['name']}: {pkg['version']} -> {pkg['latest_version']}")

    print("\nUpdating packages...")
    for pkg in outdated_packages:
        update_package(pkg["name"])

    # Update requirements.txt
    print("\nUpdating requirements file...")
    if update_requirements_file(requirements_file):
        print("Successfully updated requirements file.")
    else:
        print("Failed to update requirements file.")


if __name__ == "__main__":
    main()
