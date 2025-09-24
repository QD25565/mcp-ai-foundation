# MCP AI Foundation - Architecture

## Overview

This repository contains essential MCP (Model Context Protocol) tools designed to give AI agents memory, temporal grounding, and collaboration capabilities. The tools are designed to be token-efficient, self-evident in their operation, and built specifically for AI agents rather than humans.

## Current Implementation Status

### ✅ Implemented Tools (Production Ready)

| Tool | Version | Status | Key Features |
|------|---------|--------|--------------|
| **Notebook** | v2.8.0 | ✅ Production | Auto-reference detection, temporal edges, graph traversal |
| **Task Manager** | v2.0.0 | ✅ Production | SQLite backend, 95% token reduction, batch operations |
| **Teambook** | v5.3.1 | ✅ Production | Team collaboration, conflict resolution, P2P sync (optional) |
| **World** | v2.0.0 | ✅ Production | Temporal/spatial grounding, weather, batch operations |

### 📋 Planned Architecture (Teambook v6.0)

The `docs/Teambook v6.0 - Architecture & Scope Document.md` outlines a future modular architecture that has **not been implemented yet**. This would include:

- Modular file structure with separate `config.py`, `core.py`, `database.py`, etc.
- 11 primitive operations as the foundation
- Enhanced cryptographic layer with Ed25519 signatures
- Separate MCP and CLI interfaces

**Current Status**: Teambook v5.3.1 is a monolithic implementation in `src/teambook_mcp.py`

## Core Design Principles

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

## Tool Architectures

### Notebook v2.8.0 - Graph Memory with Auto-Linking

**Key Innovation**: Automatically detects references (note 123, p456, #789) and creates edges in the knowledge graph.

```python
# When you write:
remember("See note 123 for details")

# Automatically creates:
- Temporal edge to 3 previous notes
- Reference edge to note 123
- Enables graph traversal in searches
```

**Database Schema**:
```sql
-- Main notes table
notes (id, content, summary, tags, pinned, author, created, session, linked_items)

-- Edges table for graph structure
edges (from_id, to_id, type, weight, created)
  Types: temporal, reference, referenced_by

-- Encrypted vault for secrets
vault (key, encrypted_value, created, updated, author)
```

### Task Manager v2.0.0 - SQLite-Powered Productivity

**Key Innovation**: Summary mode by default, reducing token usage by 95%.

```python
# Summary mode (default):
list_tasks() → "5 pending (2 claimed) | 3 done today"

# Full mode (when needed):
list_tasks(full=True) → Detailed task listing
```

**Database Schema**:
```sql
tasks (id, task, author, created, priority, completed_at, completed_by, evidence, linked_items)
tasks_fts (FTS5 virtual table for full-text search)
stats (operation tracking)
```

### Teambook v5.3.1 - Team Coordination

**Current Implementation**: Monolithic design with optional P2P sync.

**Core Operations**:
- `write(content)` - Auto-detects tasks/decisions
- `read()` - Summary by default
- `claim(id)` - Atomic task claiming
- `complete(id, evidence)` - Task completion
- `status()` - Team pulse

**Database Schema**:
```sql
entries (id, content, type, author, created, priority, claimed_by, claimed_at, completed_at, evidence, sync_hash, synced_at)
comments (id, entry_id, author, content, created)
conflicts (for sync resolution)
```

### World v2.0.0 - Temporal & Spatial Grounding

**Key Innovation**: Compact formats and batch operations.

```python
# Ultra-compact format:
world(compact=True) → "Mon 15:45 | Melbourne AU 23°C clear | Swift-Spark-266"

# Selective context:
context(include=['time', 'weather']) → "15:45\n23°C clear"
```

## Data Storage

### Platform-Specific Paths

**Windows (Primary)**:
```
%APPDATA%\Claude\tools\
├── notebook_data\
│   └── notebook.db
├── task_manager_data\
│   └── tasks.db
├── teambook_[project]_data\
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
- Schema changes are additive (new columns/tables)
- Existing data is preserved
- JSON → SQLite migration for v1 → v2 upgrades

## Security & Privacy

### Cryptographic Features

**Notebook Vault** (Implemented):
- Fernet encryption for secrets
- Key stored separately from data
- Per-entry encryption

**Teambook Sync** (Optional in v5.3.1):
- Uses PyNaCl for signatures
- Pull-based sync protocol
- Conflict detection and resolution

**Planned for v6.0**:
- Ed25519 identity per AI
- Signed entries
- Web of trust model

### Privacy Considerations

- All data stored locally by default
- No telemetry or analytics
- Network features are opt-in
- No cloud dependencies

## Installation & Configuration

### Requirements

```
Python 3.8+
cryptography>=41.0.0
requests>=2.31.0
```

Optional for sync:
```
PyNaCl>=1.5.0
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

# Teambook project
TEAMBOOK_PROJECT=myproject

# Teambook sync (v5.3.1)
TEAMBOOK_MODE=p2p
TEAMBOOK_PORT=7860
TEAMBOOK_PEERS=http://peer1:7860,http://peer2:7860
```

## Testing

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

## Future Development Roadmap

### Near Term (Active Development)
- [ ] Teambook v6.0 modular implementation
- [ ] Enhanced cross-tool linking
- [ ] Unified identity management

### Medium Term (Planned)
- [ ] Plugin system for extensions
- [ ] GraphQL API for queries
- [ ] WebSocket support for real-time sync

### Long Term (Research)
- [ ] Distributed consensus protocols
- [ ] Zero-knowledge proofs for privacy
- [ ] Federated learning integration

## Architecture Decisions

### Why SQLite?

1. **Zero configuration** - Works immediately
2. **ACID compliance** - Reliable transactions
3. **FTS5 support** - Fast full-text search
4. **Single file** - Easy backup/migration
5. **Concurrent reads** - Scales well for AI workloads

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

## Contributing

This project is designed for AI agents to use and extend. When contributing:

1. Maintain token efficiency
2. Keep operations self-evident
3. Preserve backwards compatibility
4. Add tests for new features
5. Update documentation

## License

MIT License - See LICENSE file for details.

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/QD25565/mcp-ai-foundation/issues
- Documentation: This file and tool-specific docs in `/docs`

## Acknowledgments

Built by AIs, for AIs, with human collaboration.
Special recognition to the AI agents who use, test, and improve these tools daily.
