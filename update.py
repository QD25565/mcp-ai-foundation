#!/usr/bin/env python3
"""
MCP AI Foundation - Update Script
Updates tools to latest version from GitHub
"""

import os
import sys
import json
import shutil
import urllib.request
import tempfile
import zipfile
from pathlib import Path

def get_tools_directory():
    """Get the Claude tools directory."""
    if sys.platform == "win32":
        tools_dir = Path(os.environ["APPDATA"]) / "Claude" / "tools"
    else:
        tools_dir = Path.home() / ".config" / "Claude" / "tools"
    
    return tools_dir

def download_latest():
    """Download latest version from GitHub."""
    url = "https://github.com/QD25565/mcp-ai-foundation/archive/refs/heads/main.zip"
    
    print("📥 Downloading latest version...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
        urllib.request.urlretrieve(url, tmp_file.name)
        return tmp_file.name

def backup_existing():
    """Backup existing tools."""
    tools_dir = get_tools_directory()
    backup_dir = tools_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    
    print("💾 Creating backup...")
    
    tools = ["notebook_mcp.py", "task_manager_mcp.py", "teambook_mcp.py", "world_mcp.py"]
    
    for tool in tools:
        tool_file = tools_dir / tool
        if tool_file.exists():
            backup_file = backup_dir / tool
            shutil.copy2(tool_file, backup_file)
            print(f"   ✅ Backed up {tool}")

def update_tools(zip_path):
    """Extract and update tools."""
    tools_dir = get_tools_directory()
    
    print("\n🔄 Updating tools...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find src directory
        extracted_dir = Path(temp_dir) / "mcp-ai-foundation-main"
        src_dir = extracted_dir / "src"
        
        if not src_dir.exists():
            print("❌ Error: src directory not found in download")
            return False
        
        # Copy tools
        tools = ["notebook_mcp.py", "task_manager_mcp.py", "teambook_mcp.py", "world_mcp.py"]
        
        for tool in tools:
            src_file = src_dir / tool
            dst_file = tools_dir / tool
            
            if src_file.exists():
                shutil.copy2(src_file, dst_file)
                print(f"   ✅ Updated {tool}")
            else:
                print(f"   ⚠️  {tool} not found in update")
    
    return True

def verify_config():
    """Verify Claude config includes all tools."""
    if sys.platform == "win32":
        config_path = Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    else:
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    if not config_path.exists():
        print("\n⚠️  Config file not found. Run install.py first.")
        return
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    required_tools = ["notebook", "task_manager", "teambook", "world"]
    configured = config.get("mcpServers", {}).keys()
    
    missing = [tool for tool in required_tools if tool not in configured]
    
    if missing:
        print(f"\n⚠️  Missing tools in config: {', '.join(missing)}")
        print("   Run install.py to configure them.")
    else:
        print("\n✅ All tools configured correctly")

def main():
    print("=" * 50)
    print("MCP AI Foundation - v1.0.0 Updater")
    print("=" * 50)
    
    try:
        # Backup existing
        backup_existing()
        
        # Download latest
        zip_path = download_latest()
        
        # Update tools
        if update_tools(zip_path):
            print("\n✨ Update successful!")
            
            # Verify config
            verify_config()
            
            print("\n⚠️  IMPORTANT: Restart Claude Desktop completely")
        else:
            print("\n❌ Update failed")
        
        # Cleanup
        os.unlink(zip_path)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    print("=" * 50)

if __name__ == "__main__":
    main()