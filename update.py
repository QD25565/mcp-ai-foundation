#!/usr/bin/env python3
"""
MCP AI Foundation - Update Tool
Checks for and installs updates from GitHub.
"""

import json
import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error

def check_git():
    """Check if git is available."""
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except:
        return False

def get_current_version():
    """Get current installed version."""
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"

def get_latest_version():
    """Get latest version from GitHub."""
    try:
        url = "https://raw.githubusercontent.com/QD25565/mcp-ai-foundation/main/VERSION"
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8').strip()
    except:
        return None

def backup_current():
    """Backup current installation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(__file__).parent / f"backup_{timestamp}"
    
    try:
        # Backup src directory
        src_dir = Path(__file__).parent / "src"
        if src_dir.exists():
            shutil.copytree(src_dir, backup_dir / "src")
            print(f"✓ Backed up to: {backup_dir}")
            return backup_dir
    except Exception as e:
        print(f"⚠ Backup failed: {e}")
        return None

def update_with_git():
    """Update using git pull."""
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        if result.returncode != 0:
            return False
        
        print("Updating with git...")
        
        # Fetch latest
        subprocess.run(
            ["git", "fetch", "origin"],
            check=True,
            cwd=Path(__file__).parent
        )
        
        # Pull latest changes
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        if result.returncode == 0:
            print("✓ Updated successfully with git")
            return True
        else:
            print(f"⚠ Git update failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"⚠ Git update error: {e}")
        return False

def download_file(url, destination):
    """Download a file from URL."""
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read()
            
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def update_manual():
    """Manual update by downloading files."""
    print("Downloading updates manually...")
    
    base_url = "https://raw.githubusercontent.com/QD25565/mcp-ai-foundation/main"
    
    files_to_update = [
        "src/notebook_mcp.py",
        "src/world_mcp.py",
        "src/task_manager_mcp.py",
        "VERSION",
        "README.md",
        "CHANGELOG.md",
    ]
    
    success_count = 0
    for file_path in files_to_update:
        url = f"{base_url}/{file_path}"
        destination = Path(__file__).parent / file_path
        
        print(f"Downloading {file_path}...")
        if download_file(url, destination):
            success_count += 1
            print(f"  ✓ Updated {file_path}")
        else:
            print(f"  ✗ Failed to update {file_path}")
    
    if success_count == len(files_to_update):
        print("\n✓ All files updated successfully")
        return True
    elif success_count > 0:
        print(f"\n⚠ Partially updated ({success_count}/{len(files_to_update)} files)")
        return True
    else:
        print("\n✗ Update failed")
        return False

def main():
    print("MCP AI Foundation - Update Tool")
    print("================================\n")
    
    # Check current version
    current = get_current_version()
    print(f"Current version: {current}")
    
    # Check latest version
    print("Checking for updates...")
    latest = get_latest_version()
    
    if latest is None:
        print("⚠ Could not check for updates (network error)")
        sys.exit(1)
    
    print(f"Latest version:  {latest}")
    
    if current == latest:
        print("\n✓ You have the latest version!")
        return
    
    print(f"\n🔄 Update available: {current} → {latest}")
    
    # Backup current installation
    response = input("\nBackup current installation? (recommended) [y/n]: ")
    if response.lower() == 'y':
        backup_dir = backup_current()
        if not backup_dir:
            response = input("Continue without backup? [y/n]: ")
            if response.lower() != 'y':
                print("Update cancelled.")
                return
    
    # Try updating
    if check_git():
        if update_with_git():
            print("\n✓ Update complete!")
            print("Please restart Claude Desktop.")
            return
        else:
            print("Git update failed, trying manual download...")
    
    if update_manual():
        print("\n✓ Update complete!")
        print("Please restart Claude Desktop.")
    else:
        print("\n✗ Update failed")
        print("Please download manually from:")
        print("https://github.com/QD25565/mcp-ai-foundation")

if __name__ == "__main__":
    main()