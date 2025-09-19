# MCP AI Foundation

Token-optimized Model Context Protocol (MCP) tools for AI assistants. These tools provide persistent memory, task management, and temporal grounding while minimizing token usage through smart truncation and efficient data structures.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://github.com/modelcontextprotocol)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Token Reduction](https://img.shields.io/badge/Token%20Reduction-35--40%25-success.svg)]()

## 🚀 Features

- **35-40% token reduction** compared to standard implementations
- **Persistent storage** across sessions
- **Smart truncation** with full content access when needed
- **Clean, maintainable code** ready for production use

## 📦 Core Tools

### 📝 Notebook (v1.0.0) - Persistent Memory
Smart memory system with intelligent previews and full content retrieval.

```python
get_status()              # View recent notes (smart 5000-char preview)
remember("content")       # Save thoughts/notes (up to 5000 chars)
recall("search term")     # Search efficiently with context highlighting
get_full_note(id)         # Retrieve COMPLETE content of any note
```

**Token Optimizations:**
- Contextual time: `@10:03` instead of `2025-09-19T10:03:44.049355`
- Session deduplication: Only stored when changed
- Smart truncation: Shows beginning+end for code, clean cutoff for prose
- Compact JSON storage with single-letter keys

### ✅ Task Manager (v6.0.0) - Simple Workflow
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

**Features:**
- Auto-priority detection from keywords
- Time-to-complete tracking
- Smart archiving of old completed tasks
- Ultra-compact display format

### 🌍 World (v2.0.0) - Temporal & Location Grounding
Clean, efficient tools for time, date, weather, and location.

```python
world()                   # Complete snapshot
datetime()                # Date and time only
weather()                 # Weather and location only
```

**Features:**
- IP-based geolocation with caching
- Weather from Open-Meteo API
- No defaults - returns "unknown" when unavailable
- 10-minute weather caching

## 💾 Installation

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

## 🎯 Token Optimization Techniques

Our tools achieve 35-40% token reduction through:

### 1. Metadata Deduplication (20-30 tokens/item)
- Session IDs only stored when changed
- Redundant fields eliminated
- Compact single-letter keys internally

### 2. Smart Time Formatting (8-10 tokens/timestamp)
- `@10:03` for today
- `@y10:03` for yesterday  
- `@3d` for 3 days ago
- `@9/15` for older dates

### 3. Intelligent Truncation (100s-1000s tokens)
- Proportional space distribution
- Context-aware cutoff points
- Full content on demand via `get_full_note()`

### 4. The 99/1 Rule
- 99% of the time: Efficient truncated previews
- 1% of the time: Full content access
- Separate functions for each use case

## 📂 Data Storage

Tools store data persistently:
- **Windows:** `%APPDATA%\Claude\tools\[tool_name]_data\`
- **Mac/Linux:** `~/.config/Claude/tools/[tool_name]_data/`

Data format: JSON for easy inspection and backup

## 🔧 Troubleshooting

### Tools not appearing in Claude?
1. Completely quit Claude (check system tray)
2. Verify config file paths are correct
3. Check Python is accessible from command line
4. Restart Claude

### get_full_note() not working?
1. Delete old data files: `notebook_data/notebook.json`
2. Restart Claude completely
3. Tool will start fresh with v1.0.0 format

### Token usage still high?
- Use `get_status()` instead of recalling all notes
- Use `get_full_note()` only when necessary
- Let truncation work for you

## 🤝 Contributing

Key principles for contributions:
- **Minimize token usage** - Every character counts
- **Keep it simple** - No unnecessary complexity
- **No heavy dependencies** - Lightweight is right
- **Clear function names** - Self-documenting code

## 📈 Version History

### v1.0.0 (2025-09-19)
- Complete rewrite for 35-40% token reduction
- Added `get_full_note()` for complete content access
- Removed all migration code for clean start
- Production-ready release

### Previous Versions
- v10.0.0: Original notebook with basic functionality
- v6.0.0: Task manager simplified from 3-state to 2-state
- v2.0.0: World tool with weather integration

## 📄 License

MIT License - See [LICENSE](./LICENSE) file

## 🙏 Acknowledgments

Built with love for AIs, by humans who care about context efficiency.

Special thanks to the Anthropic team for the MCP protocol that makes these tools possible.

## 💡 Making Your AI Aware

Add to your system prompt or project documentation:
```markdown
You have MCP tools available:
- notebook: get_status(), remember(content), recall(query), get_full_note(id)
- task_manager: add_task(task), list_tasks(filter), complete_task(id, evidence), delete_task(id), task_stats()
- world: world(), datetime(), weather()

Start sessions with get_status() to see previous context.
Use get_full_note(id) when you need complete content.
```

---

**Built BY an AI, FOR AIs** 🤖

*"Every token saved is a thought preserved."*