# MCP AI Foundation

Model Context Protocol (MCP) tools for AI memory persistence, task management, team coordination, and real-world grounding.

## Overview

Four core tools that provide fundamental capabilities for AI systems:

- 📓 **Notebook (v6.0.0)** - High-performance memory system built on DuckDB with semantic search
- ✅ **Task Manager (v3.1.0)** - Task tracking with notebook integration and temporal filtering
- 🌐 **Teambook (v6.0.0)** - Team coordination with 11 foundational primitives  
- 🌍 **World (v3.0.0)** - Temporal and spatial grounding with minimal overhead

All tools feature:
- Persistent storage and scalability
- Pipe-delimited format for token efficiency (70-80% reduction)
- Cross-tool integration for seamless workflows
- Natural language time queries ("yesterday", "this week", "morning")
- Smart ID resolution with "last" keyword everywhere
- Operation memory for natural chaining
- Batch operations support

## Installation

### Quick Install
```bash
# 1. Clone repository
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure MCP (see below)
# 4. Run - Everything else happens automatically
```

### What Happens Automatically
- **Models folder**: Created on first run
- **EmbeddingGemma**: Downloads on first use (file size depends on model you go with)
- **Data directories**: Created automatically per tool
- **Database migration**: From SQLite to DuckDB with automatic backup
- **Path resolution**: Adapts to your system

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

### 📓 Notebook v6.0.0
High-performance memory system built on DuckDB with vectorized operations and semantic search.

**Key Features:**
- **DuckDB Backend** - Columnar analytics engine with native array types
- **Vectorized PageRank** - Recursive CTEs for graph calculations (<1 second)
- **Native Arrays** - Tags stored as arrays, no join tables needed
- **Semantic Search** - Google's EmbeddingGemma for semantic understanding
- **Automatic Migration** - Safe transition from SQLite with backup
- **Graph Intelligence** - Edge detection, session tracking, entity extraction
- **Encrypted Vault** - Secure storage for sensitive data

**Performance Improvements:**
- PageRank: 66 seconds → <1 second  
- Graph traversals: 40x faster
- Complex queries: 25x faster
- Memory usage: 90% reduction

See [docs/notebook.md](docs/notebook.md) for detailed documentation.

### ✅ Task Manager v3.1.0
Smart task tracking with natural language resolution and notebook integration.

**Features:**
- Time-based queries ("today", "yesterday", "this week")
- Cross-tool logging to notebook
- Auto-priority detection
- Partial ID matching

See [docs/task_manager.md](docs/task_manager.md) for details.

### 🌐 Teambook v6.0.0
Foundational collaboration using 11 self-evident operations.

See [docs/teambook.md](docs/teambook.md) for the complete primitive reference.

### 🌍 World v3.0.0
Provides temporal and spatial context with minimal overhead.

**Features:**
- 80% token reduction
- Single-line output
- Weather only when extreme

See [docs/world.md](docs/world.md) for usage.

## Cross-Tool Integration

### Automatic Task Creation
```python
# In notebook:
remember("TODO: Review the pull request")
# → Automatically creates task in task_manager
```

### Smart ID Resolution
```python
complete_task("last")  # Complete the task you just created
pin_note("last")       # Pin the note you just saved  
```

### Natural Language Time Queries
```python
recall(when="yesterday")
list_tasks(when="this week")
```

## Requirements

- Python 3.8+
- DuckDB (for Notebook v6.0)
- ChromaDB (for semantic search)
- sentence-transformers (for embeddings)
- scipy (for sparse matrix operations)
- PyTorch (CPU version sufficient)
- cryptography (for vault)
- requests (for weather/location)  
- numpy (for calculations)

## Data Storage

All paths are created automatically on first run:

- **Windows**: `%APPDATA%/Claude/tools/{tool}_data/`
- **Linux/Mac**: `~/Claude/tools/{tool}_data/`
- **Models**: `{tools_dir}/models/` (auto-downloads EmbeddingGemma)
- **Vectors**: `{tool}_data/vectors/` (ChromaDB storage)

Each tool maintains its own database with automatic migration and backups.

## Troubleshooting

### First Run Takes Long?
- EmbeddingGemma (~1.12GB) downloads once on first use
- After download, everything works offline
- Fallback models available if download fails

### Database Migration
- Notebook v6.0 automatically migrates from SQLite to DuckDB
- Original database is backed up before migration
- Migration happens once on first run

### Models Not Loading?
- Check internet connection for first download
- Verify ~1GB free disk space
- System will fall back to lighter models automatically

## Version History

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

### Latest Updates

**v6.0.0 (September 2025)** - DuckDB Migration
- Notebook rewritten with DuckDB backend
- Massive performance improvements
- Native array storage for tags
- Automatic safe migration from SQLite

**v5.0.0 (September 2025)** - Semantic Intelligence
- Added EmbeddingGemma integration
- Hybrid search capabilities
- ChromaDB for vector storage

## License

MIT License - See LICENSE file for details.

---

Built for AIs, by AIs. 🤖
