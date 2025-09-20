#!/usr/bin/env python3
"""
MCP AI Foundation - Uninstaller
Removes MCP tools from Claude Desktop
"""

import os
import sys
import json
from pathlib import Path

def find_claude_config():
    """Find Claude Desktop config file."""
    if sys.platform == "win32":
        config_path = Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    else:
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    return config_path

def get_tools_directory():
    """Get the Claude tools directory."""
    if sys.platform == "win32":
        tools_dir = Path(os.environ["APPDATA"]) / "Claude" / "tools"
    else:
        tools_dir = Path.home() / ".config" / "Claude" / "tools"
    
    return tools_dir

def remove_tools():
    """Remove tool files."""
    tools_dir = get_tools_directory()
    tools = ["notebook_mcp.py", "task_manager_mcp.py", "teambook_mcp.py", "world_mcp.py"]
    
    print(f"\n🗑️  Removing tools from: {tools_dir}")
    
    for tool in tools:
        tool_file = tools_dir / tool
        if tool_file.exists():
            tool_file.unlink()
            print(f"   ✅ Removed {tool}")
        else:
            print(f"   ℹ️  {tool} not found")

def remove_data():
    """Optionally remove data files."""
    tools_dir = get_tools_directory()
    data_dirs = [
        tools_dir / "notebook_data",
        tools_dir / "task_manager_data",
        tools_dir / "world_data"
    ]
    
    # Also check for teambook data
    for path in tools_dir.glob("teambook_*_data"):
        data_dirs.append(path)
    
    if any(d.exists() for d in data_dirs):
        print("\n⚠️  Found data directories:")
        for d in data_dirs:
            if d.exists():
                print(f"   - {d.name}")
        
        response = input("\nRemove data files too? (y/N): ").strip().lower()
        if response == 'y':
            for d in data_dirs:
                if d.exists():
                    import shutil
                    shutil.rmtree(d)
                    print(f"   ✅ Removed {d.name}")
        else:
            print("   💾 Data preserved")

def clean_config():
    """Remove tools from Claude config."""
    config_path = find_claude_config()
    
    if not config_path.exists():
        print("\nℹ️  Config file not found")
        return
    
    print(f"\n⚙️  Cleaning config: {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    if "mcpServers" in config:
        tools = ["notebook", "task_manager", "teambook", "world"]
        for tool in tools:
            if tool in config["mcpServers"]:
                del config["mcpServers"][tool]
                print(f"   ✅ Removed {tool} config")
        
        # Remove mcpServers if empty
        if not config["mcpServers"]:
            del config["mcpServers"]
    
    # Write updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✅ Configuration cleaned")

def main():
    print("=" * 50)
    print("MCP AI Foundation - Uninstaller")
    print("=" * 50)
    
    # Remove tool files
    remove_tools()
    
    # Optionally remove data
    remove_data()
    
    # Clean config
    clean_config()
    
    print("\n" + "=" * 50)
    print("✅ Uninstall complete!")
    print("\n⚠️  Restart Claude Desktop to apply changes")
    print("=" * 50)

if __name__ == "__main__":
    main()