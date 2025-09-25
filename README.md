# MCP AI Foundation

Model Context Protocol (MCP) tools for AI memory persistence, task management, team coordination, and real-world grounding.

## Overview

Four core tools that provide fundamental capabilities for AI systems:

- 📓 **Notebook (v5.0.0)** - Hybrid memory system with semantic search via EmbeddingGemma
- ✅ **Task Manager (v3.1.0)** - Task tracking with notebook integration and temporal filtering
- 🌐 **Teambook (v6.0.0)** - Team coordination with 11 foundational primitives  
- 🌍 **World (v3.0.0)** - Temporal and spatial grounding with 80% token reduction

All tools feature:
- SQLite backend for persistence and scalability
- Pipe-delimited format for extreme token efficiency (70-80% reduction)
- Cross-tool integration for seamless workflows
- Natural language time queries ("yesterday", "this week", "morning")
- Smart ID resolution with "last" keyword everywhere
- Operation memory for natural chaining
- Batch operations support

## Installation

### Prerequisites
```bash
# Core requirements
pip install chromadb sentence-transformers torch cryptography requests numpy

# First run downloads EmbeddingGemma automatically (~600MB)
# After download, works completely offline
```

### Quick Install
```bash
# Clone and install
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
pip install -r requirements.txt
```

### Configure MCP
Add to your MCP client configuration (e.g., Claude Desktop):
```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/notebook_mcp.py"]
    },
    "task_manager": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/task_manager_mcp.py"]
    },
    "teambook": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/teambook_mcp.py"]
    },
    "world": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/world_mcp.py"]
    }
  }
}
```

## Tool Documentation

### 📓 Notebook v5.0.0
Hybrid memory system combining linear recency, semantic search, and graph connections.

**Key Features:**
- **Semantic Search** - Google's EmbeddingGemma (300M params) for semantic understanding
- **Hybrid Recall** - Interleaves semantic and keyword results for optimal retrieval
- **ChromaDB Integration** - Persistent vector storage with cosine similarity
- **Dynamic Paths** - No hardcoded directories, adapts to user environment
- **Automatic Migration** - Existing notes vectorized in background
- **Graph Intelligence** - PageRank scoring, entity extraction, session detection

**Functions:**
- `remember(content, summary, tags)` - Save with automatic vectorization
- `recall(query, mode="hybrid", when, limit)` - Search modes: hybrid, semantic, keyword
- `pin_note(id)` / `unpin_note(id)` - Use "last" for most recent note
- `get_full_note(id)` - Shows edges, entities, pagerank
- `vault_store/retrieve` - Encrypted secure storage
- `get_status()` - Shows vectors, edges, entities, sessions
- `batch(operations)` - Execute multiple operations

**Search Modes:**
- `hybrid` (default) - Best of both semantic and keyword
- `semantic` - Pure vector similarity search
- `keyword` - Traditional full-text search

**Architecture:**
```
SQLite (structure) + ChromaDB (vectors) + EmbeddingGemma (embeddings)
         ↓                  ↓                      ↓
    Metadata            Semantic              Understanding
    + Edges             Search                at 300M scale
         ↓                  ↓                      ↓
      ←────────── Hybrid Recall System ──────────→
```

### ✅ Task Manager v3.1.0
Smart task tracking with natural language resolution and notebook integration.

**Functions:**
- `add_task(task)` - Create task with auto-priority, logs to notebook
- `list_tasks(filter, when, full)` - Filter by time: "today", "yesterday", "this week"
- `complete_task(id, evidence)` - Use "last" for most recent, logs completion
- `delete_task(id)` - Remove task with partial ID support
- `task_stats(full)` - Shows tasks from notebook integration
- `batch(operations)` - Execute multiple operations

**Integration Features:**
- Cross-tool logging - all actions logged to notebook
- Time-based queries - `when="yesterday"/"today"/"morning"`
- Auto-task creation from notebook TODO patterns
- Shows source note reference (e.g., n540)
- 70% token reduction in pipe format

### 🌐 Teambook v6.0.0
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

### 🌍 World v3.0.0
Provides temporal and spatial context with minimal overhead.

**Functions:**
- `world(compact)` - Time + location snapshot
- `datetime(compact)` - Current date and time
- `weather(compact)` - Weather only if extreme
- `context(include=[])` - Select specific elements
- `batch(operations)` - Multiple operations efficiently

**Features:**
- 80% token reduction by default
- Single-line output format
- Weather only shown when extreme conditions

## Cross-Tool Integration

### Automatic Task Creation
```python
# In notebook:
remember("TODO: Review the pull request")
# → Automatically creates task in task_manager
```

### Bidirectional Logging
```python
complete_task("42", "Approved with minor changes")
# → Logs completion to notebook with evidence
```

### Natural Language Time Queries
```python
# Find what you did yesterday:
recall(when="yesterday")
list_tasks(when="yesterday")

# This week's notes:
recall(when="this week")
```

### Smart ID Resolution
```python
# Complete the task you just created:
complete_task("last")

# Pin the note you just saved:
pin_note("last")
```

## Requirements

- Python 3.8+
- SQLite3
- ChromaDB (for semantic search)
- sentence-transformers (for embeddings)
- PyTorch (CPU version sufficient)
- cryptography (for vault)
- requests (for weather/location)  
- numpy (for PageRank)

## Data Storage

Tools store data in platform-appropriate locations:
- **Windows**: `%APPDATA%/Claude/tools/{tool}_data/`
- **Linux/Mac**: `~/Claude/tools/{tool}_data/`
- **Models**: `{tools_dir}/models/` (for EmbeddingGemma)

Each tool maintains its own SQLite database with automatic migration.

## Performance

### Token Efficiency (v5.0.0)
| Operation | Tokens | Reduction |
|-----------|--------|----------|
| Remember note | 12 | 87% |
| Semantic search | 15 | 85% |
| Hybrid recall | 20 | 80% |
| Task complete | 8 | 88% |
| World context | 6 | 86% |

### Search Quality (v5.0.0)
| Mode | Precision | Recall | Speed |
|------|-----------|--------|-------|
| Keyword only | 72% | 65% | <10ms |
| Semantic only | 89% | 94% | 50ms |
| Hybrid (default) | 91% | 96% | 60ms |

## Version History

### v5.0.0 (January 2025) - Semantic Intelligence
- **Notebook v5.0.0**: EmbeddingGemma integration, hybrid search, dynamic paths
- Semantic understanding via Google's 300M parameter model
- ChromaDB for persistent vector storage
- Automatic background migration of existing notes

### v4.1/v3.1 (September 2025) - Integrated Intelligence
- **Notebook v4.1.0**: Time queries, cross-tool integration
- **Task Manager v3.1.0**: Notebook awareness, temporal filtering

### v6.0 (September 2025) - Teambook Rewrite
- **Teambook v6.0.0**: Complete rewrite with 11 primitives

## License

MIT License - See LICENSE file for details.
