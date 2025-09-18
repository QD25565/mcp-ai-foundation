#!/usr/bin/env python3
"""
MCP AI Foundation - Uninstaller
Safely removes MCP tools from Claude Desktop config.
"""

import json
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

def find_claude_config():
    """Find Claude Desktop config file."""
    
    # Windows locations
    if sys.platform == "win32":
        paths = [
            Path(os.environ.get('APPDATA', '')) / "Claude" / "claude_desktop_config.json",
            Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        ]
    
    # Mac/Linux locations
    else:
        paths = [
            Path.home() / ".claude" / "claude_desktop_config.json",
            Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / ".config")) / "claude" / "claude_desktop_config.json",
        ]
    
    for path in paths:
        if path.exists():
            return path
    
    return None

def backup_config(config_path):
    """Create backup of existing config."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.parent / f"claude_desktop_config.backup_{timestamp}.json"
    
    try:
        shutil.copy2(config_path, backup_path)
        print(f"✓ Backed up config to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"⚠ Could not backup config: {e}")
        return None

def remove_tools(config_path):
    """Remove MCP tools from Claude config."""
    
    # Load existing config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if "mcpServers" not in config:
        print("No MCP servers found in config.")
        return False
    
    # Tools to remove
    tools_to_remove = ["notebook", "world", "task-manager"]
    removed = []
    
    for tool_name in tools_to_remove:
        if tool_name in config["mcpServers"]:
            del config["mcpServers"][tool_name]
            removed.append(tool_name)
            print(f"✓ Removed {tool_name} tool")
    
    if not removed:
        print("No MCP AI Foundation tools found in config.")
        return False
    
    # Save updated config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Updated configuration saved")
    return True

def main():
    print("MCP AI Foundation Uninstaller")
    print("=============================\n")
    
    # Find Claude config
    config_path = find_claude_config()
    
    if not config_path:
        print("✗ Could not find Claude Desktop config file.")
        sys.exit(1)
    
    print(f"✓ Found Claude config: {config_path}\n")
    
    # Ask about data backup
    print("Your tool data is stored in:")
    if sys.platform == "win32":
        print("  %APPDATA%\\Claude\\tools\\")
    else:
        print("  ~/Claude/tools/")
    
    response = input("\nDo you want to backup your data before uninstalling? (y/n): ")
    
    if response.lower() == 'y':
        print("\nPlease manually backup the data directory.")
        input("Press Enter when ready to continue...")
    
    # Backup config
    backup_config(config_path)
    
    # Remove tools
    if remove_tools(config_path):
        print("\n" + "="*50)
        print("✓ Uninstall complete!")
        print("\nThe tools have been removed from Claude Desktop.")
        print("Your data has been preserved in the tools directory.")
        print("\nTo reinstall later, run install.py again.")
    else:
        print("\nNo changes made.")

if __name__ == "__main__":
    main()