#!/usr/bin/env python3
"""
MCP AI Foundation - Auto Installer
Automatically configures Claude Desktop with MCP tools
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
    
    installed = []
    for tool in tools:
        src_file = src_dir / tool
        dst_file = tools_dir / tool
        
        if src_file.exists():
            shutil.copy2(src_file, dst_file)
            print(f"   ✅ Installed {tool}")
            installed.append(tool)
        else:
            print(f"   ⚠️  {tool} not found in src/")
    
    return tools_dir, installed

def update_config(tools_dir, installed_tools):
    """Update Claude Desktop configuration."""
    config_path = find_claude_config()
    
    print(f"\n⚙️  Updating config: {config_path}")
    
    # Create config directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config or create new
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print("   📖 Loaded existing config")
        except json.JSONDecodeError:
            print("   ⚠️  Existing config invalid, creating new")
            config = {}
    else:
        print("   📝 Creating new config")
        config = {}
    
    # Ensure mcpServers exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Tool configurations
    tools = [
        ("notebook", "notebook_mcp.py"),
        ("task_manager", "task_manager_mcp.py"),
        ("teambook", "teambook_mcp.py"),
        ("world", "world_mcp.py")
    ]
    
    python_cmd = "python" if sys.platform == "win32" else "python3"
    
    configured = 0
    for name, filename in tools:
        if filename in installed_tools:
            tool_path = str(tools_dir / filename)
            config["mcpServers"][name] = {
                "command": python_cmd,
                "args": [tool_path]
            }
            print(f"   ✅ Configured {name}")
            configured += 1
    
    # Write updated config
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ Configuration updated successfully! ({configured} tools)")
        return True
    except Exception as e:
        print(f"\n❌ Failed to write config: {e}")
        return False

def verify_python():
    """Verify Python is accessible."""
    python_cmd = "python" if sys.platform == "win32" else "python3"
    
    try:
        import subprocess
        result = subprocess.run([python_cmd, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Python found: {result.stdout.strip()}")
            return True
    except:
        pass
    
    print(f"   ⚠️  Python not accessible from command line")
    print(f"      Make sure Python is in your PATH")
    return False

def main():
    print("=" * 50)
    print("MCP AI Foundation - v1.0.0 Installer")
    print("=" * 50)
    
    # Verify Python
    print("\n🐍 Checking Python...")
    verify_python()
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    os.system(f"{sys.executable} -m pip install requests --quiet")
    print("   ✅ Dependencies installed")
    
    # Install tools
    tools_dir, installed = install_tools()
    
    if not installed:
        print("\n❌ No tools found to install!")
        print("   Make sure you're running from the mcp-ai-foundation directory")
        sys.exit(1)
    
    # Update config
    success = update_config(tools_dir, installed)
    
    if success:
        print("\n" + "=" * 50)
        print("✨ Installation complete!")
        print(f"\n📝 Installed {len(installed)} tools:")
        for tool in installed:
            print(f"   - {tool.replace('_mcp.py', '')}")
        print("\n⚠️  IMPORTANT: Restart Claude Desktop completely")
        print("   (Check system tray and quit completely)")
        print("\n📖 Quick test after restart:")
        print("   1. Open Claude Desktop")
        print("   2. Type: notebook.get_status()")
        print("   3. You should see your notebook status")
    else:
        print("\n⚠️  Installation partially complete")
        print("   Tools copied but config update failed")
        print("   You may need to manually edit claude_desktop_config.json")
    
    print("=" * 50)

if __name__ == "__main__":
    main()