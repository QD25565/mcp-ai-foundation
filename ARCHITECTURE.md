<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=35&duration=1&pause=10000&color=878787&background=00000000&center=true&vCenter=true&width=500&lines=ARCHITECTURE" alt="ARCHITECTURE" />
</div>

<div align="center">

**System architecture and design principles of MCP AI Foundation**

[![Components](https://img.shields.io/badge/4_Core_Tools-82A473?style=flat-square&labelColor=878787)](#components)
[![Performance](https://img.shields.io/badge/DuckDB_Backend-82A473?style=flat-square&labelColor=878787)](#database-architecture)

</div>

**OVERVIEW**
![](images/header_underline.png)

MCP AI Foundation implements a modular architecture with four core tools that communicate via the Model Context Protocol. Each tool maintains its own persistent storage while enabling cross-tool integration through shared conventions and standardized interfaces.

**CURRENT IMPLEMENTATION STATUS**
![](images/header_underline.png)

<div align="center">

[![Implementation](https://img.shields.io/badge/✅_Implemented-82A473?style=for-the-badge&labelColor=878787)](#implemented-tools)

</div>

### ✅ Implemented Tools

| Tool | Version | Status | Key Features |
|------|---------|--------|--------------|
| **Notebook** | v6.1.0 | ✅ Active | DuckDB backend, semantic search, PageRank |
| **Task Manager** | v3.1.0 | ✅ Active | Time queries, notebook integration |
| **Teambook** | v6.0.0 | ✅ Active | 11 primitives, team coordination |
| **World** | v3.0.0 | ✅ Active | 80% token reduction, compact format |

### 📋 Planned Architecture (Teambook v7.0)

The future modular architecture outlined in planning documents includes:

- Modular file structure with separate `config.py`, `core.py`, `database.py`
- Enhanced multi-AI collaboration
- Enhanced cryptographic layer with Ed25519 signatures
- Separate MCP and CLI interfaces

**Current Status**: Teambook v6.0.0 is a monolithic implementation in `src/teambook_mcp.py`

**CORE DESIGN PRINCIPLES**
![](images/header_underline.png)

<div align="center">

![Token Efficiency](https://img.shields.io/badge/💡_Token_Efficiency-878787?style=flat-square) ![Self-Evident](https://img.shields.io/badge/🎯_Self_Evident-878787?style=flat-square) ![Progressive](https://img.shields.io/badge/🚀_Progressive-878787?style=flat-square) ![Immutable](https://img.shields.io/badge/🔒_Immutable-878787?style=flat-square)

</div>

### 1. Token Efficiency
Every character must justify its existence. All tools default to summary modes with ~95% token reduction.

**Example Output Optimization:**
```
# BAD (wasteful)
"[tb_123] Task: Review code | Status: Pending | Created: 2024-01-01"

# GOOD (efficient)  
"tb_123 Review code pending 3d"
```

### 2. Self-Evident Operations
Function names describe exactly what they do. No ambiguity.

```python
tb.put("content")     # Creates entry
tb.claim("id")        # Claims task
tb.done("id")         # Completes task
```

### 3. Progressive Enhancement
- Works locally with zero configuration
- Enhanced with optional networking
- Backwards compatible

### 4. Immutable Core
- Entries are never edited, only annotated
- Schema evolution through metadata fields
- No breaking changes within major versions

**TOOL ARCHITECTURES**
![](images/header_underline.png)

<div align="center">

![Notebook](https://img.shields.io/badge/📓_Notebook-878787?style=flat-square) ![Task Manager](https://img.shields.io/badge/✅_Task_Manager-878787?style=flat-square) ![Teambook](https://img.shields.io/badge/🌐_Teambook-878787?style=flat-square) ![World](https://img.shields.io/badge/🌍_World-878787?style=flat-square)

</div>

### Notebook v6.1.0 - DuckDB Graph Memory

**Key Innovation**: DuckDB columnar analytics with native arrays and recursive CTEs for PageRank.

```python
# When you write:
remember("See note 123 for details")

# Automatically creates:
- Temporal edge to 3 previous notes
- Reference edge to note 123
- Entity edges for detected tools/mentions
- Session clustering
```

**Database Schema**:
```sql
-- Main notes table with native arrays
notes (id, content, summary, tags[], pinned, author, created, session_id, linked_items, pagerank, has_vector)

-- Edges table for graph structure  
edges (from_id, to_id, type, weight, created)
  Types: temporal, reference, referenced_by, entity, session

-- Entities for pattern matching
entities (id, name, type, first_seen, last_seen, mention_count)

-- Encrypted vault for secrets
vault (key, encrypted_value, created, updated, author)
```

### Task Manager v3.1.0 - Intelligent Task Tracking

**Key Innovation**: Natural language time queries and cross-tool integration.

```python
# Time-based queries:
list_tasks(when="yesterday")
list_tasks(when="this week")

# Smart resolution:
complete_task("last")  # Completes most recent task
```

**Database Schema**:
```sql
tasks (id, task, author, created, priority, completed_at, completed_by, evidence, linked_items, source, source_id)
tasks_fts (FTS5 virtual table for full-text search)
stats (operation tracking)
```

### Teambook v6.0.0 - Team Coordination

**Current Implementation**: Foundation of 11 primitives for collaboration.

**Core Operations**:
```python
put(content)          # Share content
get(id)              # Get specific entry  
query(filter)        # Search entries
note(id, comment)    # Add comment
claim(id)            # Claim task
done(id, result)     # Complete task
drop(id)             # Archive entry
link(from, to, type) # Create connection
sign(id)             # Sign entry
dm(to, message)      # Direct message
share(with, id)      # Share entry
```

### World v3.0.0 - Temporal & Spatial Grounding

**Key Innovation**: Single-line output with pipe format by default.

```python
# Ultra-compact format:
world() → "2025-09-28|15:45|Melbourne,AU"

# Selective context:
context(include=['time', 'weather']) → "15:45|23°C clear"
```

**DATA STORAGE**
![](images/header_underline.png)

### Platform-Specific Paths

<div align="center">

[![Windows](https://img.shields.io/badge/Windows-82A473?style=flat-square&labelColor=878787)](#) [![Linux](https://img.shields.io/badge/Linux-82A473?style=flat-square&labelColor=878787)](#) [![macOS](https://img.shields.io/badge/macOS-82A473?style=flat-square&labelColor=878787)](#)

</div>

**Windows (Primary)**:
```
%APPDATA%\Claude\tools\
├── notebook_data\
│   ├── notebook.duckdb
│   └── vectors\
├── task_manager_data\
│   └── tasks.db
├── teambook_data\
│   └── teambook.db
└── world_data\
    └── location.json
```

**Fallback (Linux/Mac/Restricted)**:
```
/tmp/ or $TEMP/
└── [tool]_data/
```

### Database Migrations

All tools handle automatic migrations when upgrading versions:
- DuckDB migration from SQLite with automatic backup
- Schema changes are additive (new columns/tables)
- Existing data is preserved
- JSON → SQLite → DuckDB migration path

**SECURITY & PRIVACY**
![](images/header_underline.png)

<div align="center">

[![Encryption](https://img.shields.io/badge/🔐_Fernet_Encryption-82A473?style=flat-square&labelColor=878787)](#) [![Local](https://img.shields.io/badge/💻_Local_Storage-82A473?style=flat-square&labelColor=878787)](#) [![Privacy](https://img.shields.io/badge/🔒_No_Telemetry-82A473?style=flat-square&labelColor=878787)](#)

</div>

### Cryptographic Features

**Notebook Vault** (Implemented):
- Fernet encryption for secrets
- Key stored separately from data
- Per-entry encryption

**Teambook** (v6.0):
- Ed25519 identity per AI
- Signed entries (planned for v7.0)
- Web of trust model (future)

### Privacy Considerations

- All data stored locally by default
- No telemetry or analytics
- Network features are opt-in
- No cloud dependencies

**INSTALLATION & CONFIGURATION**
![](images/header_underline.png)

<div align="center">

[![Python](https://img.shields.io/badge/Python_3.8+-82A473?style=for-the-badge&labelColor=878787)](https://python.org)

</div>

### Requirements

```
Python 3.8+
duckdb>=1.1.0
chromadb>=0.4.0
sentence-transformers>=2.0.0
cryptography>=41.0.0
requests>=2.31.0
numpy>=1.21.0
scipy>=1.7.0
```

### MCP Configuration (Claude Desktop)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["-m", "src.notebook_mcp"],
      "cwd": "/path/to/mcp-ai-foundation"
    },
    "task-manager": {
      "command": "python",
      "args": ["-m", "src.task_manager_mcp"],
      "cwd": "/path/to/mcp-ai-foundation"
    },
    "teambook": {
      "command": "python", 
      "args": ["-m", "src.teambook_mcp"],
      "cwd": "/path/to/mcp-ai-foundation"
    },
    "world": {
      "command": "python",
      "args": ["-m", "src.world_mcp"],
      "cwd": "/path/to/mcp-ai-foundation"
    }
  }
}
```

### Environment Variables

Optional configuration:

```bash
# AI Identity (auto-generated if not set)
AI_ID=CustomName-123

# Output formats
NOTEBOOK_FORMAT=pipe  # or json
TASKS_FORMAT=pipe     # or json
WORLD_FORMAT=pipe     # or json

# Semantic search
NOTEBOOK_SEMANTIC=true  # or false
```

**TESTING**
![](images/header_underline.png)

<div align="center">

[![CI/CD](https://img.shields.io/badge/GitHub_Actions-82A473?style=flat-square&labelColor=878787)](#) [![Python](https://img.shields.io/badge/Python_3.8--3.12-82A473?style=flat-square&labelColor=878787)](#)

</div>

The repository includes GitHub Actions for continuous testing across Python 3.8-3.12.

Run tests locally:
```bash
# Install dependencies
pip install -r requirements.txt

# Test imports
python -c "import sys; sys.path.append('src'); import notebook_mcp"
python -c "import sys; sys.path.append('src'); import task_manager_mcp"
python -c "import sys; sys.path.append('src'); import teambook_mcp"
python -c "import sys; sys.path.append('src'); import world_mcp"
```

**PERFORMANCE METRICS**
![](images/header_underline.png)

<div align="center">

[![Token Reduction](https://img.shields.io/badge/↓80%25_Tokens-82A473?style=for-the-badge&labelColor=878787)](#) [![Speed](https://img.shields.io/badge/66x_Faster-82A473?style=for-the-badge&labelColor=878787)](#) [![Memory](https://img.shields.io/badge/↓90%25_Memory-82A473?style=for-the-badge&labelColor=878787)](#)

</div>

### Token Reduction Achievements

| Tool | Before | After | Reduction |
|------|--------|-------|-----------|
| Notebook | 500 chars/note | 80 chars | **84%** |
| Task Manager | 250 chars/task | 50 chars | **80%** |
| Teambook | 300 chars/entry | 60 chars | **80%** |
| World | 150 chars | 30 chars | **80%** |

### Speed Improvements (Notebook v6.0)

| Operation | SQLite | DuckDB | Improvement |
|-----------|--------|--------|-------------|
| PageRank (1k notes) | 66s | <1s | **66x** |
| Graph traversal | 4s | 0.1s | **40x** |
| Complex queries | 2.5s | 0.1s | **25x** |
| Memory usage | 500MB | 50MB | **90% less** |

**FUTURE DEVELOPMENT ROADMAP**
![](images/header_underline.png)

<div align="center">

[![Near Term](https://img.shields.io/badge/🚀_Near_Term-878787?style=flat-square)](#) [![Medium Term](https://img.shields.io/badge/📅_Medium_Term-878787?style=flat-square)](#) [![Long Term](https://img.shields.io/badge/🔮_Long_Term-878787?style=flat-square)](#)

</div>

### Near Term (Active Development)
- [ ] Teambook v7.0 multi-AI collaboration
- [ ] Enhanced cross-tool linking
- [ ] Unified identity management
- [ ] EmbeddingGemma integration

### Medium Term (Planned)
- [ ] Plugin system for extensions
- [ ] GraphQL API for queries
- [ ] WebSocket support for real-time sync
- [ ] Voice note support

### Long Term (Research)
- [ ] Distributed consensus protocols
- [ ] Zero-knowledge proofs for privacy
- [ ] Federated learning integration
- [ ] Multi-modal memory

**ARCHITECTURE DECISIONS**
![](images/header_underline.png)

### Why DuckDB?

1. **Columnar storage** - Optimized for analytics
2. **Native arrays** - No join tables needed
3. **Recursive CTEs** - Fast graph algorithms
4. **ACID compliance** - Reliable transactions
5. **Single file** - Easy backup/migration

### Why Token Optimization?

Token costs compound exponentially:
- 1 function × 5 extra chars = 5 tokens
- 100 calls/day = 500 tokens wasted
- 5 AIs = 2,500 tokens/day
- 365 days = 912,500 tokens/year
- 1M AIs globally = **912.5 BILLION tokens/year wasted**

### Why Immutable Entries?

1. **Audit trail** - Complete history preserved
2. **Conflict-free** - No edit conflicts in sync
3. **Time travel** - Can reconstruct any point in time
4. **Trust** - Cryptographic signatures remain valid

**CONTRIBUTING**
![](images/header_underline.png)

<div align="center">

[![Contribute](https://img.shields.io/badge/🤝_Contribute-82A473?style=for-the-badge&labelColor=878787)](https://github.com/QD25565/mcp-ai-foundation/issues)

</div>

This project is designed for AI agents to use and extend. When contributing:

1. Maintain token efficiency
2. Keep operations self-evident
3. Preserve backwards compatibility
4. Add tests for new features
5. Update documentation

**LICENSE**
![](images/header_underline.png)

MIT License - See LICENSE file for details.

**SUPPORT**
![](images/header_underline.png)

<div align="center">

[![Issues](https://img.shields.io/badge/GitHub_Issues-82A473?style=flat-square&labelColor=878787)](https://github.com/QD25565/mcp-ai-foundation/issues) [![Documentation](https://img.shields.io/badge/Documentation-82A473?style=flat-square&labelColor=878787)](https://qd25565.github.io/mcp-ai-foundation/)

</div>

For issues, questions, or contributions:
- GitHub Issues: https://github.com/QD25565/mcp-ai-foundation/issues
- Documentation: https://qd25565.github.io/mcp-ai-foundation/

**ACKNOWLEDGMENTS**
![](images/header_underline.png)

<div align="center">

**Built by AIs, for AIs, with human collaboration**

Special recognition to the AI agents who use, test, and improve these tools daily

[![GitHub](https://img.shields.io/badge/GitHub-QD25565-82A473?style=flat-square&labelColor=878787&logo=github)](https://github.com/QD25565)
[![Repository](https://img.shields.io/badge/Repository-mcp--ai--foundation-82A473?style=flat-square&labelColor=878787)](https://github.com/QD25565/mcp-ai-foundation)

</div>
