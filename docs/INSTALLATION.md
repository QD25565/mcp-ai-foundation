# Installation Guide

## Quick Install

Choose your platform and installation method:

### Windows Command Prompt
```batch
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
install.bat
```

### Windows PowerShell
```powershell
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation

# Option 1: Run the PowerShell script
.\install.ps1

# Option 2: Run the batch file
.\install.bat

# Option 3: Run Python directly
python install.py
```

### Mac/Linux Terminal
```bash
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
chmod +x install.sh
./install.sh
```

## What the Installer Does

The automatic installer performs these steps:

1. **Verifies Python Installation**
   - Checks that Python 3.8+ is installed
   - Ensures Python is accessible from command line

2. **Installs Dependencies**
   ```bash
   pip install requests
   ```

3. **Copies Tool Files**
   - Source: `src/` directory
   - Destination:
     - Windows: `%APPDATA%\Claude\tools\`
     - Mac: `~/.config/Claude/tools/`
     - Linux: `~/.config/Claude/tools/`

4. **Updates Claude Configuration**
   - File location:
     - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
     - Mac/Linux: `~/.config/Claude/claude_desktop_config.json`
   - Adds all 4 MCP tools automatically
   - Preserves any existing configuration

5. **Creates Necessary Directories**
   - Creates Claude config directory if missing
   - Creates tools directory if missing

## Manual Installation

If you prefer to install manually:

### Step 1: Install Python Dependencies
```bash
pip install requests
```

### Step 2: Copy Tool Files

Copy these files from `src/`:
- `notebook_mcp.py`
- `task_manager_mcp.py`
- `teambook_mcp.py`
- `world_mcp.py`

To your Claude tools directory:
- Windows: `C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\tools\`
- Mac: `/Users/YOUR_USERNAME/.config/Claude/tools/`
- Linux: `/home/YOUR_USERNAME/.config/Claude/tools/`

### Step 3: Update Claude Configuration

Edit `claude_desktop_config.json`:

**Windows Path:** `C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["C:/Users/YOUR_USERNAME/AppData/Roaming/Claude/tools/notebook_mcp.py"]
    },
    "task_manager": {
      "command": "python",
      "args": ["C:/Users/YOUR_USERNAME/AppData/Roaming/Claude/tools/task_manager_mcp.py"]
    },
    "teambook": {
      "command": "python",
      "args": ["C:/Users/YOUR_USERNAME/AppData/Roaming/Claude/tools/teambook_mcp.py"]
    },
    "world": {
      "command": "python",
      "args": ["C:/Users/YOUR_USERNAME/AppData/Roaming/Claude/tools/world_mcp.py"]
    }
  }
}
```

**Mac/Linux Path:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "notebook": {
      "command": "python3",
      "args": ["/home/YOUR_USERNAME/.config/Claude/tools/notebook_mcp.py"]
    },
    "task_manager": {
      "command": "python3",
      "args": ["/home/YOUR_USERNAME/.config/Claude/tools/task_manager_mcp.py"]
    },
    "teambook": {
      "command": "python3",
      "args": ["/home/YOUR_USERNAME/.config/Claude/tools/teambook_mcp.py"]
    },
    "world": {
      "command": "python3",
      "args": ["/home/YOUR_USERNAME/.config/Claude/tools/world_mcp.py"]
    }
  }
}
```

### Step 4: Restart Claude Desktop

**Important:** Completely quit Claude Desktop:
1. Close all Claude windows
2. Check system tray (Windows) or menu bar (Mac)
3. Right-click and choose "Quit" or "Exit"
4. Start Claude Desktop again

## Verification

After installation and restart:

1. Open Claude Desktop
2. In a new conversation, type:
   ```
   notebook.get_status()
   ```
3. You should see a response showing your notebook status

## Troubleshooting

### Tools Not Appearing

1. **Check Python Installation**
   ```bash
   python --version  # Windows
   python3 --version # Mac/Linux
   ```
   Should show Python 3.8 or higher

2. **Verify Config File**
   - Make sure `claude_desktop_config.json` exists
   - Check that paths are correct for your system
   - Ensure proper JSON formatting (no trailing commas)

3. **Check File Permissions**
   - Tool files should be readable
   - Config file should be readable and writable

4. **Complete Restart**
   - Quit Claude completely (check system tray/menu bar)
   - Wait a few seconds
   - Start Claude Desktop again

### Path Issues

- Windows: Use forward slashes `/` or escaped backslashes `\\`
- Mac/Linux: Use forward slashes `/`
- Replace `YOUR_USERNAME` with your actual username

### Python Not Found

- Windows: Add Python to PATH during installation
- Mac: Install via Homebrew: `brew install python3`
- Linux: Install via package manager: `apt install python3`

## Uninstalling

### Automatic Uninstall

**Windows:**
```batch
uninstall.bat
```

**Mac/Linux:**
```bash
./uninstall.sh
```

### Manual Uninstall

1. Delete tool files from Claude tools directory
2. Remove tool entries from `claude_desktop_config.json`
3. Optionally delete data directories:
   - `notebook_data/`
   - `task_manager_data/`
   - `teambook_*_data/`
   - `world_data/`

## Updating

To update to the latest version:

**Windows:**
```batch
update.bat
```

**Mac/Linux:**
```bash
./update.sh
```

This will:
1. Backup existing tools
2. Download latest version
3. Update tool files
4. Preserve your data