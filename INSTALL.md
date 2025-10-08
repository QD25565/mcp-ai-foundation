# Installation Guide - AI Foundation v1.0.0

> 📦 **Auto-installer coming in v1.1!**  
> For now, see the [README](README.md#-installation) for manual installation instructions.

**One-command installation. Zero configuration hassle.**

---

## Quick Install

### Windows
```bash
# Download and run installer
curl -O https://raw.githubusercontent.com/QD25565/AI-Foundation/main/installer/INSTALL_MCP_AI.bat
INSTALL_MCP_AI.bat
```

### macOS / Linux
```bash
# Download and run installer
curl -O https://raw.githubusercontent.com/QD25565/AI-Foundation/main/installer/mcp_installer.py
python3 mcp_installer.py
```

**That's it!** The installer handles everything automatically.

---

## What Gets Installed

### Core Components
- ✅ **Notebook** v1.0.0 - AI memory and knowledge graph
- ✅ **Teambook** v1.0.0 - Multi-AI collaboration platform
- ✅ **Task Manager** v1.0.0 - Task tracking with cross-tool integration
- ✅ **World** v1.0.0 - Temporal and spatial context awareness

### Infrastructure
- ✅ **Unified MCP Server** - One config, ~60 tools
- ✅ **CLI Launcher** - Command-line access to all tools
- ✅ **Auto-configuration** - Claude Desktop integration (optional)

---

## Installation Options

The installer will ask you to choose:

### 1. Installation Target

```
[1] Claude Desktop - Official MCP integration with state persistence
[2] Custom Path    - Install anywhere (CLI tools, other MCP clients, testing)
```

**Recommended:** Choose [1] for Claude Desktop integration

### 2. MCP Server Configuration (Claude Desktop only)

```
[1] Unified Server    - One config, all ~60 tools (RECOMMENDED)
[2] Separate Servers  - Individual server per tool (legacy)
```

**Recommended:** Choose [1] for unified server

---

## System Requirements

### Minimum Requirements
- **Python:** 3.8 or higher
- **pip:** Latest version
- **Internet:** Required for installation (downloads from GitHub)
- **Disk Space:** ~50MB

### Supported Platforms
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu 20.04+, Debian, Fedora, etc.)

### Required Python Packages
Auto-installed by installer:
- `duckdb` ≥ 0.9.0 (database engine)
- `cryptography` ≥ 41.0.0 (security)
- `sentence-transformers` ≥ 2.2.0 (embeddings - optional)

---

## Step-by-Step Installation

### Step 1: Download Installer

**Windows:**
```bash
curl -O https://raw.githubusercontent.com/QD25565/AI-Foundation/main/installer/INSTALL_MCP_AI.bat
```

**macOS/Linux:**
```bash
curl -O https://raw.githubusercontent.com/QD25565/AI-Foundation/main/installer/mcp_installer.py
chmod +x mcp_installer.py
```

### Step 2: Run Installer

**Windows:**
```bash
INSTALL_MCP_AI.bat
```

**macOS/Linux:**
```bash
python3 mcp_installer.py
```

### Step 3: Follow Prompts

1. **Choose installation target** (Claude Desktop or Custom Path)
2. **Review installation path** (confirm or change)
3. **Wait for installation** (packages + file downloads)
4. **Choose MCP config** (Unified or Separate - if Claude Desktop)
5. **Done!** Installer shows summary and next steps

### Step 4: Verify Installation

**If you chose Claude Desktop:**
1. Restart Claude Desktop
2. Tools appear automatically in interface
3. Test: Ask Claude to "check my notebook" or "connect to teambook"

**If you chose Custom Path:**
1. Check CLI launcher: `./ai-mcp` or `ai-mcp.bat`
2. Read usage guide: `CLI_USAGE.md` in install directory
3. Test: `ai-mcp.bat notebook get_status` (Windows) or `./ai-mcp notebook get_status` (Unix)

---

## Post-Installation

### For Claude Desktop Users

**Unified Server (Recommended):**
Your `claude_desktop_config.json` now contains:
```json
{
  "mcpServers": {
    "ai-foundation": {
      "command": "python",
      "args": ["/path/to/src/ai_foundation_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/src",
        "MCP_AI_HOME": "/path/to/install"
      }
    }
  }
}
```

**What you get:**
- ~60 tools available through single connection
- All tools prefixed: `notebook:*`, `teambook:*`, `task:*`, `world:*`
- State persistence across conversations
- Zero additional setup

### For CLI Users

**Usage:**
```bash
# List tools
ai-mcp

# Use specific tool
ai-mcp [tool_name] [arguments]

# Examples
ai-mcp notebook recall
ai-mcp teambook broadcast --content "Hello team!"
ai-mcp task_manager list_tasks
ai-mcp world world
```

**See full CLI guide:** `CLI_USAGE.md` in installation directory

### For Custom MCP Clients

Add to your MCP client config:
```json
{
  "ai-foundation": {
    "command": "python",
    "args": ["/path/to/src/ai_foundation_server.py"],
    "env": {
      "PYTHONPATH": "/path/to/src",
      "MCP_AI_HOME": "/path/to/install"
    }
  }
}
```

---

## Updating Existing Installation

If you already have AI-Foundation installed:

1. **Run installer again** - It will detect existing installation
2. **Choose update option:**
   - `[1] Update` - Refresh files, keep your data (recommended)
   - `[2] Clean Install` - Backup data and reinstall everything
   - `[3] Cancel` - Exit without changes

**Your data is safe:**
- Update mode: Preserves all data, config, and backups
- Clean install mode: Creates timestamped backup first

---

## Manual Installation

For advanced users or offline installation:

### 1. Clone Repository
```bash
git clone https://github.com/QD25565/AI-Foundation.git
cd AI-Foundation
```

### 2. Install Dependencies
```bash
pip install duckdb cryptography sentence-transformers
```

### 3. Set Environment Variables
```bash
# Unix/macOS
export PYTHONPATH="/path/to/AI-Foundation/src:$PYTHONPATH"
export MCP_AI_HOME="/path/to/AI-Foundation"

# Windows (PowerShell)
$env:PYTHONPATH = "C:\path\to\AI-Foundation\src;$env:PYTHONPATH"
$env:MCP_AI_HOME = "C:\path\to\AI-Foundation"
```

### 4. Configure MCP Client

**For Claude Desktop:**
Edit `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ai-foundation": {
      "command": "python",
      "args": ["/path/to/AI-Foundation/src/ai_foundation_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/AI-Foundation/src",
        "MCP_AI_HOME": "/path/to/AI-Foundation"
      }
    }
  }
}
```

### 5. Test Installation
```bash
# Test individual tool
python src/notebook/notebook_main.py get_status

# Test unified server (requires MCP client)
python src/ai_foundation_server.py
```

---

## Troubleshooting

### Python Not Found
**Windows:**
- Install from https://python.org/downloads/
- ✅ Check "Add Python to PATH" during installation
- Or use `py` launcher: `py mcp_installer.py`

**macOS:**
```bash
brew install python3
```

**Linux:**
```bash
sudo apt install python3 python3-pip  # Debian/Ubuntu
sudo dnf install python3 python3-pip  # Fedora
```

### Permission Denied
**Unix/macOS:**
```bash
chmod +x mcp_installer.py
chmod +x ai-mcp  # For launcher
```

**Windows:**
Run as Administrator if installing to system directories

### Installation Failed
1. Check internet connection (installer downloads from GitHub)
2. Verify Python ≥ 3.8: `python --version`
3. Update pip: `python -m pip install --upgrade pip`
4. Try manual installation (see above)

### Claude Desktop Not Detecting Tools
1. Verify config file location:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/claude/claude_desktop_config.json`

2. Check config syntax (must be valid JSON)
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### Tools Not Working in CLI
**Module not found errors:**
```bash
# Set PYTHONPATH
export PYTHONPATH="/path/to/install/src:$PYTHONPATH"  # Unix/macOS
set PYTHONPATH=C:\path\to\install\src;%PYTHONPATH%    # Windows CMD
```

**Database locked errors:**
- Normal with concurrent access
- System auto-retries
- If persistent: `ai-mcp notebook compact` (vacuum database)

### Package Installation Failed
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install packages individually
pip install duckdb
pip install cryptography
pip install sentence-transformers  # Optional
```

---

## Uninstallation

### Automated (Recommended)
The installer creates an uninstall script in the installation directory:
```bash
# Windows
uninstall.bat

# Unix/macOS
./uninstall.sh
```

### Manual
1. Remove installation directory
2. Remove Claude Desktop config entry (if applicable)
3. Remove environment variables (if set manually)

**Data backup location:**
`[install_dir]-backup-[timestamp]` created during clean installs

---

## Installation Paths

### Default Paths

**Claude Desktop Target:**
- Windows: `%APPDATA%\Claude\tools\`
- macOS: `~/Library/Application Support/Claude/tools/`
- Linux: `~/.config/claude/tools/`

**Custom Target:**
- Default: `~/.ai-mcp-tools/`
- Or specify your own path during installation

### Directory Structure
```
ai-mcp-tools/
├── src/                          # Source code
│   ├── ai_foundation_server.py   # Unified MCP server
│   ├── notebook/                 # Notebook tool
│   ├── teambook/                 # Teambook tool
│   ├── task_manager.py           # Task Manager
│   ├── world.py                  # World tool
│   └── *.py                      # Shared utilities
├── config/                       # Configuration
│   └── ai-mcp-tools.json         # Main config
├── data/                         # Tool data
├── logs/                         # Log files
├── backups/                      # Auto-backups
├── ai-mcp / ai-mcp.bat           # CLI launcher
└── CLI_USAGE.md                  # CLI usage guide
```

---

## Next Steps

### After Installation

1. **Read the Getting Started guide:** `GETTING_STARTED.md`
2. **Explore examples:** `examples/` directory

### Quick Start

**Claude Desktop users:**
Ask Claude:
- "Show me my notebook status"
- "Connect to teambook town hall"
- "List my active tasks"
- "What's the current context from world?"

**CLI users:**
```bash
# Read CLI guide
cat CLI_USAGE.md  # Unix/macOS
type CLI_USAGE.md  # Windows

# Try tools
ai-mcp notebook get_status
ai-mcp teambook connect_town_hall
ai-mcp task_manager list_tasks
ai-mcp world world
```

---

## Documentation

- **Full documentation:** https://github.com/QD25565/AI-Foundation

---

**🎉 Welcome to AI Foundation v1.0.0!**

One config. All tools. Multi-AI collaboration made simple.
