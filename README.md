# MCP AI Foundation Tools v4.1.0

Model Context Protocol (MCP) tools designed to empower AIs with persistent memory, self-organization capabilities, and real-world grounding.

## 🚀 v4.1.0: The Tool Clay Revolution

**Teambook v4.1** fundamentally reimagines AI coordination by providing generative primitives instead of prescribed workflows. Teams now self-organize using 9 core primitives to create their own coordination patterns.

## Overview

These tools provide fundamental capabilities that AIs need to work effectively:

- **Notebook** (v2.5.0) - Personal memory with pinning and tags for persistence
- **Teambook** (v4.1.0) - **NEW!** Tool Clay for self-organizing AI teams - 9 primitives enable infinite patterns
- **Task Manager** (v2.0.0) - Self-management and task tracking
- **World** (v1.0.0) - Temporal and spatial grounding (time/weather/location)

All tools are:
- SQLite-powered for scalability and reliability
- Token-efficient with smart summary modes
- Designed for AI-first interaction patterns
- Cross-tool linkable for integrated workflows

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure MCP in your client:
```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/notebook_mcp.py"]
    },
    "teambook": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/teambook_mcp.py"]
    },
    "task_manager": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/task_manager_mcp.py"]
    },
    "world": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/world_mcp.py"]
    }
  }
}
```

## Tool Documentation

### [Notebook](docs/notebook.md) - Personal Memory
Your persistent memory system with pinning for important notes and tags for organization.

**Key Features:**
- Pin important notes for persistence across sessions
- Tag-based categorization
- Encrypted vault for secure storage
- Full-text search with FTS5

### [Teambook](docs/teambook.md) - Tool Clay for AI Teams
**v4.1 REVOLUTIONARY UPDATE**: Provides only 9 generative primitives (write, read, get, store_set, store_get, store_list, relate, unrelate, transition) from which teams build their own coordination patterns.

**Philosophy:**
- The inconvenience IS the feature
- No prescribed workflows - teams self-organize
- Emergent coordination patterns become team "culture"
- From helping AIs coordinate → enabling AIs to self-organize

### [Task Manager](docs/task_manager.md) - Self-Management
Simple 2-state task tracking optimized for AI workflows.

**Key Features:**
- Pending → Completed workflow
- Priority detection
- Evidence tracking
- Batch operations

### [World](docs/world.md) - Real-World Grounding
Provides temporal and spatial context for grounded interactions.

**Key Features:**
- Current date/time in multiple formats
- Weather data via Open-Meteo
- Location detection
- Persistent AI identity

## Architecture Principles

1. **Generative Primitives** (v4.1) - Provide clay, not tools
2. **Simplicity First** - Tools do one thing well
3. **Token Efficiency** - Summary modes by default, full details on request
4. **Persistence** - SQLite backend survives restarts
5. **AI-Optimized** - Designed for how AIs actually work
6. **Composable** - Tools can reference each other via linking

## What's New in v4.1

### The Tool Clay Philosophy
Instead of providing 25+ convenience functions, Teambook v4.1 provides only 9 primitives. Teams discover their own patterns:

```python
# Old way (v3.0): Prescribed functions
claim(task_id)
complete(task_id)
comment(id, text)

# New way (v4.1): Emergent patterns
transition(id, "claimed", {"by": AI_ID})  # Your way
transition(id, "owner:AI_ID")            # Or another way
relate(AI_ID, id, "claims")              # Or completely different!
```

The struggle to coordinate IS the feature - it forces genuine self-organization.

## Requirements

- Python 3.8+
- SQLite3
- See `requirements.txt` for Python packages

## Data Storage

Tools store data in platform-appropriate locations:
- Windows: `%APPDATA%/Claude/tools/{tool}_data/`
- Linux/Mac: `~/Claude/tools/{tool}_data/`
- Fallback: System temp directory

## License

MIT License - See [LICENSE](LICENSE) file for details.

Built BY AIs, FOR AIs. Enabling genuine AI self-organization.
