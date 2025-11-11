#!/usr/bin/env python3
"""
Script to build and publish the orca-agent-sdk package to PyPI
"""
import subprocess
import sys
import os

def run_command(cmd):
    """Run a command and handle errors"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    print(result.stdout)

def main():
    # Clean previous builds
    print("Cleaning previous builds...")
    if os.path.exists("dist"):
        run_command("rmdir /s /q dist" if os.name == 'nt' else "rm -rf dist")
    if os.path.exists("build"):
        run_command("rmdir /s /q build" if os.name == 'nt' else "rm -rf build")
    
    # Install build dependencies
    print("Installing build dependencies...")
    run_command("pip install build twine")
    
    # Build the package
    print("Building package...")
    run_command("python -m build")
    
    # Upload to TestPyPI first (optional)
    print("Upload to TestPyPI? (y/n)")
    if input().lower() == 'y':
        run_command("python -m twine upload --repository testpypi dist/*")
        print("Package uploaded to TestPyPI!")
        print("Test install with: pip install -i https://test.pypi.org/simple/ orca-agent-sdk")
    
    # Upload to PyPI
    print("Upload to PyPI? (y/n)")
    if input().lower() == 'y':
        run_command("python -m twine upload dist/*")
        print("Package uploaded to PyPI!")
        print("Install with: pip install orca-agent-sdk")

if __name__ == "__main__":
    main()