# MCP AI Foundation

Production-ready MCP tools for AI assistants. Memory, task management, team coordination, and temporal grounding.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-v1.0.0-green.svg)](https://github.com/modelcontextprotocol)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Tools (v1.0.0)

### 📝 Notebook - Persistent Memory
```python
get_status()              # View recent notes with smart preview
remember("content")       # Save thoughts/notes (up to 5000 chars)
recall("search term")     # Search with context highlighting
get_full_note(id)         # Retrieve complete content
```

### ✅ Task Manager - Personal Workflow
```python
add_task("description")              # Create pending task
list_tasks()                         # Show pending (default)
complete_task(id, "evidence")        # Complete with optional evidence
delete_task(id)                      # Remove task
task_stats()                         # Productivity insights
```

### 🤝 Teambook - Team Coordination
```python
write("content", type="task/note/decision")  # Share with team
read(query=None, type=None)                  # View team activity  
claim(id)                                    # Claim a task
complete(id, "evidence")                     # Mark done
comment(id, "text")                          # Add discussion
status()                                     # Team pulse
projects()                                   # List available projects
```

### 🌍 World - Temporal & Location
```python
world()        # Complete snapshot (time, date, weather, location)
datetime()     # Date and time only
weather()      # Weather and location only
```

## Quick Install

**Windows:**
```batch
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
install.bat
```

**Mac/Linux:**
```bash
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
chmod +x install.sh
./install.sh
```

## Manual Setup

1. **Install dependencies:**
```bash
pip install requests
```

2. **Configure Claude Desktop:**

Edit config file:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac/Linux: `~/.config/Claude/claude_desktop_config.json`

Add:
```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["path/to/notebook_mcp.py"]
    },
    "task_manager": {
      "command": "python",
      "args": ["path/to/task_manager_mcp.py"]
    },
    "teambook": {
      "command": "python",
      "args": ["path/to/teambook_mcp.py"]
    },
    "world": {
      "command": "python",
      "args": ["path/to/world_mcp.py"]
    }
  }
}
```

3. **Restart Claude Desktop completely**

## Key Features

- **Persistent Identity**: Each AI maintains a unique ID across sessions
- **Smart Truncation**: Efficient token usage with intelligent previews
- **Project Support**: Teambook supports multiple projects via `project="name"`
- **Atomic Operations**: Thread-safe task claiming and completion
- **Local Storage**: All data stored locally in JSON format

## Storage Locations

- Windows: `%APPDATA%\Claude\tools\[tool_name]_data\`
- Mac/Linux: `~/.config/Claude/tools/[tool_name]_data/`

## Requirements

- Python 3.8+
- `requests` library (for weather/location)

## Credits

**Developed by Claude Opus 4.1** in collaboration with QD25565. These tools were designed and implemented by an AI to solve real workflow challenges faced by AI assistants.

## License

MIT License - See [LICENSE](./LICENSE)

---

**Built BY an AI, FOR AIs** 🤖