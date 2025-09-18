#!/usr/bin/env python3
"""
MCP AI Foundation - Easy Installer
Automatically configures Claude Desktop with all three tools.
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

def install_tools(config_path, tools_dir):
    """Add MCP tools to Claude config."""
    
    # Load existing config
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Ensure mcpServers exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add our tools
    tools = {
        "notebook": {
            "command": "python",
            "args": [str(tools_dir / "src" / "notebook_mcp.py")]
        },
        "world": {
            "command": "python",
            "args": [str(tools_dir / "src" / "world_mcp.py")]
        },
        "task-manager": {
            "command": "python",
            "args": [str(tools_dir / "src" / "task_manager_mcp.py")]
        }
    }
    
    # Update config
    for tool_name, tool_config in tools.items():
        config["mcpServers"][tool_name] = tool_config
        print(f"✓ Added {tool_name} tool")
    
    # Save config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Configuration saved to: {config_path}")
    return True

def main():
    print("MCP AI Foundation Installer")
    print("===========================\n")
    
    # Get script directory
    script_dir = Path(__file__).parent.resolve()
    print(f"Installing from: {script_dir}\n")
    
    # Check for required files
    required_files = [
        script_dir / "src" / "notebook_mcp.py",
        script_dir / "src" / "world_mcp.py",
        script_dir / "src" / "task_manager_mcp.py"
    ]
    
    for file_path in required_files:
        if not file_path.exists():
            print(f"✗ Missing required file: {file_path}")
            print("\nMake sure you're running this from the mcp-ai-foundation directory.")
            sys.exit(1)
    
    print("✓ All required files found\n")
    
    # Find Claude config
    config_path = find_claude_config()
    
    if not config_path:
        print("✗ Could not find Claude Desktop config file.")
        print("\nMake sure Claude Desktop is installed.")
        print("\nExpected locations:")
        if sys.platform == "win32":
            print("  - %APPDATA%\\Claude\\claude_desktop_config.json")
        else:
            print("  - ~/.claude/claude_desktop_config.json")
            print("  - ~/Library/Application Support/Claude/claude_desktop_config.json")
        sys.exit(1)
    
    print(f"✓ Found Claude config: {config_path}\n")
    
    # Backup existing config
    if config_path.exists():
        backup_config(config_path)
    
    # Install tools
    if install_tools(config_path, script_dir):
        print("\n" + "="*50)
        print("✓ Installation complete!")
        print("\nNext steps:")
        print("1. Restart Claude Desktop")
        print("2. Add to your project's docs:")
        print("\n   You have MCP tools available:")
        print("   - notebook (get_status, remember, recall)")
        print("   - world (world, datetime, weather)")
        print("   - task_manager (add_task, list_tasks, complete_task)")
        print("\n3. Start with: get_status() and list_tasks()")
    else:
        print("\n✗ Installation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()