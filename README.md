# MCP AI Foundation

Token-optimized Model Context Protocol (MCP) tools for AI assistants. These tools provide persistent memory, task management, and temporal grounding while minimizing token usage through smart truncation and efficient data structures.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://github.com/modelcontextprotocol)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Core Tools

### 📝 Notebook (v1.0.0) - Persistent Memory
Smart memory system with intelligent previews and full content retrieval.

```python
get_status()              # View recent notes with smart preview
remember("content")       # Save thoughts/notes (up to 5000 chars)
recall("search term")     # Search with context highlighting
get_full_note(id)         # Retrieve complete content of any note
```

### ✅ Task Manager (v1.0.0) - Simple Workflow
2-state task tracking (Pending → Completed) that matches real workflows.

```python
add_task("description")              # Create pending task
list_tasks()                         # Show pending (default)
list_tasks("completed")              # Show completed
list_tasks("all")                    # Show everything
complete_task(id, "evidence")        # Complete with optional evidence
delete_task(id)                      # Remove task
task_stats()                         # Productivity insights
```

### 🌍 World (v1.0.0) - Temporal & Location Grounding
Clean, efficient tools for time, date, weather, and location.

```python
world()                   # Complete snapshot
datetime()                # Date and time only
weather()                 # Weather and location only
```

## Installation

### Quick Install (Windows)
```batch
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
install.bat
```

### Quick Install (Mac/Linux)
```bash
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
chmod +x install.sh
./install.sh
```

### Manual Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Copy tools to Claude's directory:**
- Windows: `%APPDATA%\Claude\tools\`
- Mac/Linux: `~/.config/Claude/tools/`

3. **Configure Claude Desktop:**

Edit config file:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac/Linux: `~/.config/Claude/claude_desktop_config.json`

Add:
```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["C:/Users/YOUR_USER/AppData/Roaming/Claude/tools/notebook_mcp.py"]
    },
    "task_manager": {
      "command": "python",
      "args": ["C:/Users/YOUR_USER/AppData/Roaming/Claude/tools/task_manager_mcp.py"]
    },
    "world": {
      "command": "python",
      "args": ["C:/Users/YOUR_USER/AppData/Roaming/Claude/tools/world_mcp.py"]
    }
  }
}
```

4. **Restart Claude Desktop completely**

## Key Features

### Smart Truncation
- Notebook previews show truncated content by default
- Full content available via `get_full_note(id)`
- Efficient space distribution across multiple items

### Persistent Storage
- Data saved locally in JSON format
- Windows: `%APPDATA%\Claude\tools\[tool_name]_data\`
- Mac/Linux: `~/.config/Claude/tools/[tool_name]_data/`

### Task Management
- Simple pending/completed workflow
- Auto-priority detection from keywords
- Time tracking for completed tasks

### Location & Weather
- IP-based geolocation with caching
- Weather data from Open-Meteo API
- Returns "unknown" when data unavailable

## Troubleshooting

### Tools not appearing in Claude?
1. Completely quit Claude (check system tray)
2. Verify config file paths are correct
3. Check Python is accessible from command line
4. Restart Claude

### get_full_note() not working?
1. Delete old data files: `notebook_data/notebook.json`
2. Restart Claude completely
3. Tool will start fresh

## Requirements

- Python 3.8+
- `requests` library (for world tool)

## Making Your AI Aware

Add to your system prompt or project documentation:
```markdown
You have MCP tools available:
- notebook: get_status(), remember(content), recall(query), get_full_note(id)
- task_manager: add_task(task), list_tasks(filter), complete_task(id, evidence), delete_task(id), task_stats()
- world: world(), datetime(), weather()

Start sessions with get_status() to see previous context.
Use get_full_note(id) when you need complete content.
```

## License

MIT License - See [LICENSE](./LICENSE) file

## Acknowledgments

Special thanks to the Anthropic team for the MCP protocol that makes these tools possible.

---

**Built FOR AIs** 🤖
