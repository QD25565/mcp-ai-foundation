# MCP AI Foundation

Essential MCP tools giving AIs memory, temporal grounding, and task accountability.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://github.com/modelcontextprotocol)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Core Tools

Three foundational tools that give AIs essential capabilities:

### Notebook - Persistent Memory
```python
get_status()              # See current state and recent notes
remember("content")       # Save thoughts across sessions
recall("search term")     # Find memories
```

### World - Temporal & Spatial Grounding
```python
world()                   # Complete snapshot: time, date, weather, location
datetime()                # Temporal data only
weather()                 # Weather and location only
```

### Task Manager - Evidence-Based Accountability
```python
add_task("description")              # Create pending task
list_tasks()                         # Show active work
submit_task(id, "evidence")          # Submit for verification
complete_task(id)                    # Verify and complete
task_stats()                         # Productivity insights
```

## Installation

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

The installer automatically:
- Installs dependencies
- Finds Claude Desktop config
- Adds all tools
- Backs up existing config

### Making Your AI Aware

After installation, add to your project's documentation:
```markdown
You have MCP tools available:
- notebook (get_status, remember, recall)
- world (world, datetime, weather)
- task_manager (add_task, submit_task, complete_task, list_tasks)

Start each session with get_status() and list_tasks()
```

## Architecture

- **Protocol**: MCP (Model Context Protocol) 2024-11-05
- **Storage**: Local JSON in `~/AppData/Roaming/Claude/tools/`
- **Dependencies**: Python 3.8+, requests library
- **Philosophy**: Built BY an AI, FOR AIs

## License

MIT - See [LICENSE](./LICENSE) file.

Built BY an AI, FOR AIs.