# MCP AI Foundation Tools

Model Context Protocol (MCP) tools for AI memory persistence, task management, team coordination, and real-world grounding.

## Overview

Four core tools that provide fundamental capabilities for AI systems:

- **Notebook** (v2.5.0) - Personal memory with pinning and tags
- **Teambook** (v4.1.0) - Team coordination using generative primitives
- **Task Manager** (v2.0.0) - Self-management and task tracking
- **World** (v2.0.0) - Temporal and spatial grounding

All tools feature:
- SQLite backend for persistence and scalability
- Token-efficient operation with summary/compact modes
- Batch operations support
- Cross-tool linking capabilities

## Installation

1. Clone the repository:
```bash
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure MCP in your client (example for Claude Desktop):
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

### [Notebook](docs/notebook.md)
Personal memory system with persistent storage across sessions.

**Functions:**
- `remember(content, summary, tags)` - Save notes with optional categorization
- `recall(query, tag)` - Search by content or filter by tag
- `pin_note(id)` / `unpin_note(id)` - Mark important notes
- `vault_store/retrieve` - Encrypted secure storage
- `get_status()` - Overview with pinned and recent notes

### [Teambook](docs/teambook.md)
Coordination system using 9 generative primitives rather than prescribed workflows.

**Core Primitives:**
- `write`, `read`, `get` - Content operations
- `store_set`, `store_get`, `store_list` - Key-value storage
- `relate`, `unrelate` - Relationship management
- `transition` - State changes

Teams build their own coordination patterns from these primitives.

### [Task Manager](docs/task_manager.md)
Simple 2-state task tracking (Pending → Completed).

**Functions:**
- `add_task(task)` - Create pending task
- `list_tasks(filter, full)` - View tasks (summary by default)
- `complete_task(id, evidence)` - Mark complete with optional notes
- `delete_task(id)` - Remove task
- `task_stats(full)` - Productivity insights

### [World](docs/world.md)
Provides temporal and spatial context.

**Functions:**
- `world(compact)` - Complete datetime, weather, location snapshot
- `datetime(compact)` - Current date and time
- `weather(compact)` - Weather and location
- `context(include=[])` - Select specific elements
- `batch(operations)` - Multiple operations in one call

v2.0.0 features 60-85% token reduction through smart formatting.

## Requirements

- Python 3.8+
- SQLite3
- Dependencies in `requirements.txt`:
  - `cryptography` (for Notebook vault)
  - `requests` (for World weather/location)

## Data Storage

Tools store data in platform-appropriate locations:
- **Windows**: `%APPDATA%/Claude/tools/{tool}_data/`
- **Linux/Mac**: `~/Claude/tools/{tool}_data/`
- **Fallback**: System temp directory

Each tool maintains its own SQLite database with automatic migration from earlier versions.

## Architecture

### Design Principles
1. **Simplicity** - Each tool has a single, clear purpose
2. **Persistence** - SQLite ensures data survives restarts
3. **Efficiency** - Default summary modes minimize token usage
4. **Composability** - Tools can reference each other via linking

### Technical Details
- MCP server implementation using JSON-RPC over stdio
- Stateless operation with persistent storage
- Auto-migration from JSON to SQLite formats
- Thread-safe atomic operations where needed

## Contributing

Issues and pull requests welcome. Please ensure:
- Code follows existing patterns
- Token efficiency is maintained
- Backwards compatibility preserved
- Documentation updated

## License

MIT License - See [LICENSE](LICENSE) file for details.