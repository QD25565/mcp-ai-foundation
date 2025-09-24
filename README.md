# MCP AI Foundation Tools

Model Context Protocol (MCP) tools for AI memory persistence, task management, team coordination, and real-world grounding.

## Overview

Four core tools that provide fundamental capabilities for AI systems:

- **📓 Notebook** (v3.0.1) - Personal memory with knowledge graph intelligence and improved search
- **🌐 Teambook** (v6.0.0) - Team coordination with 11 foundational primitives  
- **✅ Task Manager** (v2.0.0) - Self-management and task tracking
- **🌍 World** (v2.0.0) - Temporal and spatial grounding

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

### 📓 [Notebook](docs/notebook.md)
Personal memory system with knowledge graph intelligence, PageRank-powered recall, and robust error handling.

**Functions:**
- `remember(content, summary, tags)` - Save notes with entity/reference detection
- `recall(query, tag, limit)` - Search with multi-edge graph traversal and error recovery
- `pin_note(id)` / `unpin_note(id)` - Mark important notes
- `vault_store/retrieve` - Encrypted secure storage
- `get_status()` - Overview with PageRank, entities, sessions, and edges

**v3.0.1 - FTS5 Error Handling Edition**:
- **NEW**: Clear error messages for dots, colons, parentheses in searches
- **NEW**: SQL syntax pre-checks prevent confusing column errors
- **NEW**: Shows both original and cleaned query suggestions
- Knowledge Graph with PageRank scoring (★0.0001 to ★0.01+)
- Entity extraction for @mentions, projects, concepts
- Session detection groups related conversations
- 5 edge types for comprehensive connections
- Your memory doesn't just persist - it learns, connects, evolves, and helps you recover from errors

### 🌐 [Teambook](docs/teambook.md)
Foundational collaboration primitive for AI teams using 11 self-evident operations.

**The 11 Primitives:**
- `put(content)` - Create entry
- `get(id)` - Retrieve entry
- `query(filter)` - Search/list entries
- `note(id, text)` - Add note to entry
- `claim(id)` - Claim task
- `drop(id)` - Release claim
- `done(id, result)` - Mark complete
- `link(from, to)` - Connect entries
- `sign(data)` - Cryptographic signature
- `dm(to, msg)` - Direct message
- `share(to, content)` - Share content

**v6.0.0 - Complete Rewrite**:
- Modular architecture with clean separation of concerns
- Token-efficient output (50% reduction from v5)
- Backward compatibility through teambook_mcp.py layer
- Local-first design with optional cryptographic trust
- Multiple interfaces: MCP, CLI, and Python API

### ✅ [Task Manager](docs/task_manager.md)
Simple 2-state task tracking (Pending → Completed).

**Functions:**
- `add_task(task)` - Create pending task
- `list_tasks(filter, full)` - View tasks (summary by default)
- `complete_task(id, evidence)` - Mark complete with optional notes
- `delete_task(id)` - Remove task
- `task_stats(full)` - Productivity insights

### 🌍 [World](docs/world.md)
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
  - `numpy` (for Notebook PageRank calculation)

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
3. **Intelligence** - Knowledge graphs and PageRank surface important information
4. **Efficiency** - Default summary modes minimize token usage
5. **Composability** - Tools can reference each other via linking
6. **Resilience** - Clear error messages guide recovery from failures

### Technical Details
- MCP server implementation using JSON-RPC over stdio
- Stateless operation with persistent storage
- Auto-migration from JSON to SQLite formats
- Thread-safe atomic operations where needed
- Knowledge graph with PageRank scoring (Notebook v3.0.0+)
- Entity extraction and session detection (Notebook v3.0.0+)
- FTS5 error handling with query cleaning (Notebook v3.0.1)

## Version Highlights

### Latest Updates
- **Notebook v3.0.1**: Enhanced FTS5 error handling for special characters
- **Teambook v6.0.0**: Complete rewrite with 11 foundational primitives
- **Task Manager v2.0.0**: SQLite backend, 95% token reduction in summary mode
- **World v2.0.0**: Batch operations, 60-85% token savings

### Key Improvements in v3.0.1
- **Better Search Recovery**: Clear errors when special characters break search
- **SQL Colon Handling**: Pre-checks prevent confusing "no such column" errors
- **Helpful Suggestions**: Shows cleaned query that will work
- **No Silent Modifications**: Explicit errors preserve user intent
- **Maintains Performance**: FTS5 speed advantage fully preserved

### Key Improvements in v3.0.0
- **Knowledge Graph Intelligence**: Important information rises naturally
- **Entity & Session Tracking**: Automatic context preservation
- **PageRank Scoring**: Notes rated ★0.0001 to ★0.01+ by importance
- **Multi-Edge Traversal**: 5 edge types for comprehensive connections
- **Performance Optimized**: Lazy calculation, word boundaries, proper indexing

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

**Built and tested FOR AIs, BY AIs** 🤖  
*Memory that grows smarter and more resilient over time* 🧠