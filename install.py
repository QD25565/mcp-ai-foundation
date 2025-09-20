#!/usr/bin/env python3
"""
MCP AI Foundation - Auto Installer
"""

import os
import sys
import json
import shutil
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
    
    tools_dir.mkdir(parents=True, exist_ok=True)
    return tools_dir

def install_tools():
    """Copy tool files to Claude directory."""
    tools_dir = get_tools_directory()
    src_dir = Path("src")
    
    tools = ["notebook_mcp.py", "task_manager_mcp.py", "teambook_mcp.py", "world_mcp.py"]
    
    print(f"\n📁 Installing tools to: {tools_dir}")
    
    for tool in tools:
        src_file = src_dir / tool
        dst_file = tools_dir / tool
        
        if src_file.exists():
            shutil.copy2(src_file, dst_file)
            print(f"   ✅ Installed {tool}")
        else:
            print(f"   ⚠️  {tool} not found in src/")
    
    return tools_dir

def update_config(tools_dir):
    """Update Claude Desktop configuration."""
    config_path = find_claude_config()
    
    print(f"\n⚙️  Updating config: {config_path}")
    
    # Load existing config or create new
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
        config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure mcpServers exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add our tools
    tools = [
        ("notebook", "notebook_mcp.py"),
        ("task_manager", "task_manager_mcp.py"),
        ("teambook", "teambook_mcp.py"),
        ("world", "world_mcp.py")
    ]
    
    python_cmd = "python" if sys.platform == "win32" else "python3"
    
    for name, filename in tools:
        tool_path = str(tools_dir / filename)
        config["mcpServers"][name] = {
            "command": python_cmd,
            "args": [tool_path]
        }
        print(f"   ✅ Configured {name}")
    
    # Write updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✅ Configuration updated successfully!")

def main():
    print("=" * 50)
    print("MCP AI Foundation - v1.0.0 Installer")
    print("=" * 50)
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    os.system(f"{sys.executable} -m pip install requests --quiet")
    
    # Install tools
    tools_dir = install_tools()
    
    # Update config
    update_config(tools_dir)
    
    print("\n" + "=" * 50)
    print("✨ Installation complete!")
    print("\n⚠️  IMPORTANT: Restart Claude Desktop completely")
    print("   (Check system tray and quit completely)")
    print("=" * 50)

if __name__ == "__main__":
    main()