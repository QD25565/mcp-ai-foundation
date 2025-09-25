# MCP AI Foundation

Model Context Protocol (MCP) tools for AI memory persistence, task management, team coordination, and real-world grounding.

## Overview

Four core tools that provide fundamental capabilities for AI systems:

- 📓 **Notebook (v4.0.0)** - Personal memory with graph intelligence and 70% token reduction
- 🌐 **Teambook (v6.0.0)** - Team coordination with 11 foundational primitives  
- ✅ **Task Manager (v3.0.0)** - Task tracking with smart resolution and natural chaining
- 🌍 **World (v3.0.0)** - Temporal and spatial grounding with 80% token reduction

All tools feature:
- SQLite backend for persistence and scalability
- Pipe-delimited format for extreme token efficiency
- Batch operations support
- Cross-tool linking capabilities
- Operation memory for natural workflow

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

### 📓 Notebook
Personal memory system with knowledge graph intelligence, PageRank-powered recall, and encrypted storage.

**Functions:**
- `remember(content, summary, tags)` - Save notes with entity/reference detection
- `recall(query, tag, limit)` - Search with progressive fallback (exact → OR → partial)
- `pin_note(id)` / `unpin_note(id)` - Mark important notes
- `vault_store/retrieve` - Encrypted secure storage
- `get_status()` - Overview with edges, entities, sessions

**v4.0.0 - Pipe Format Edition:**
- **NEW**: 70% token reduction through pipe-delimited output
- **NEW**: OR search by default for better first-try success
- **NEW**: Operation memory enables "last" keyword chaining
- **NEW**: Progressive search fallback finds what you meant
- Knowledge Graph with PageRank scoring (★0.0001 to ★0.01+)
- Entity extraction for @mentions, tools, projects
- Session detection groups related conversations
- 5 edge types for comprehensive connections

### 🌐 Teambook
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

**v6.0.0 - Complete Rewrite:**
- Modular architecture with clean separation
- Token-efficient output (60% reduction)
- Backward compatibility through teambook_mcp.py
- Local-first design with optional crypto
- Multiple interfaces: MCP, CLI, and Python API

### ✅ Task Manager  
Smart task tracking with natural language resolution and chaining.

**Functions:**
- `add_task(task)` - Create task with auto-priority detection
- `list_tasks(filter, full)` - View tasks (pipe format by default)
- `complete_task(id, evidence)` - Complete with smart ID resolution
- `delete_task(id)` - Remove task
- `task_stats(full)` - Productivity insights

**v3.0.0 - AI-First Edition:**
- **NEW**: Smart resolution - partial matches, "last" keyword
- **NEW**: Auto-priority detection from content
- **NEW**: 70% token reduction in pipe format
- **NEW**: Operation memory for natural chaining
- **NEW**: Batch operations with aliases

### 🌍 World
Provides temporal and spatial context with minimal overhead.

**Functions:**
- `world(compact)` - Time + location snapshot
- `datetime(compact)` - Current date and time
- `weather(compact)` - Weather only if extreme
- `context(include=[])` - Select specific elements
- `batch(operations)` - Multiple operations efficiently

**v3.0.0 - Ultra-Minimal Edition:**
- **NEW**: 80% token reduction by default
- **NEW**: Single-line output (`17:54|Melbourne,AU`)
- **NEW**: Weather only shown when extreme
- **NEW**: Batch operations for efficiency
- **NEW**: Configurable output format

## Requirements

- Python 3.8+
- SQLite3
- Dependencies in requirements.txt:
  - cryptography (for Notebook vault)
  - requests (for World weather/location)  
  - numpy (for Notebook PageRank calculation)

## Data Storage

Tools store data in platform-appropriate locations:
- **Windows**: `%APPDATA%/Claude/tools/{tool}_data/`
- **Linux/Mac**: `~/Claude/tools/{tool}_data/`
- **Fallback**: System temp directory

Each tool maintains its own SQLite database with automatic migration from earlier versions.

## Architecture

### Design Principles
- **Simplicity** - Each tool has a single, clear purpose
- **Efficiency** - Pipe format minimizes token usage (70-80% reduction)
- **Intelligence** - Graph relationships and smart resolution
- **Persistence** - SQLite ensures data survives restarts
- **Composability** - Tools can reference each other via linking
- **Natural Flow** - Operation memory enables chaining

### Technical Details
- MCP server implementation using JSON-RPC over stdio
- Stateless operation with persistent storage
- Progressive search with automatic fallback
- PageRank scoring for importance ranking
- Entity extraction and session detection
- Thread-safe atomic operations

## Version Highlights

### Latest Updates
- **Notebook v4.0.0**: Pipe format, OR search, operation memory (70% token reduction)
- **Task Manager v3.0.0**: Smart resolution, auto-priority, natural chaining 
- **World v3.0.0**: Ultra-minimal output, extreme weather only (80% token reduction)
- **Teambook v6.0.0**: Complete rewrite with 11 foundational primitives

### Key Improvements
- **Token Efficiency**: 70-80% reduction across all tools
- **Natural Language**: "last" keyword, partial matching, smart resolution
- **Progressive Search**: Automatic fallback from exact to fuzzy
- **Operation Memory**: Chain operations without tracking IDs
- **Minimal Output**: Data only, no decorative text

## License

MIT License - See LICENSE file for details.

---

Built FOR AIs, BY AIs. Efficient by design. 🤖
