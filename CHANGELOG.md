# Changelog

All notable changes to the MCP AI Foundation tools.

## [5.0.0] - 2025-09-26

### Notebook v5.0.0 - Semantic Intelligence

#### Added
- **EmbeddingGemma Integration**: Google's 300M parameter model for semantic understanding
- **Hybrid Search**: Combines semantic vectors with keyword search for optimal retrieval
- **ChromaDB Storage**: Persistent vector database for all note embeddings
- **Dynamic Paths**: Automatic path resolution - no hardcoded directories
- **Background Migration**: Existing notes automatically vectorized
- **Search Modes**: `hybrid` (default), `semantic`, `keyword`

#### Technical Details
- Embedding dimension: 768 (EmbeddingGemma)
- Vector similarity: Cosine distance
- Hybrid algorithm: Interleaved semantic + keyword results
- Fallback models: BGE, MPNet, MiniLM if EmbeddingGemma unavailable
- Models stored in: `{tools_dir}/models/`

#### Known Issues
- `get_full_note()` returns incorrect format (fix planned for v5.0.1)

---

## [4.1.0] - 2025-09-25

### Notebook v4.1.0
- Cross-tool integration with Task Manager
- Time-based queries ("yesterday", "today", "this week")
- Reduced default search results (30 for recent, 50 for searches)
- Better edge creation and PageRank scoring
- Entity extraction improvements

### Task Manager v3.1.0  
- Notebook integration - auto-logs all operations
- Time-based filtering with natural language
- Shows source note references (e.g., n540)
- Cross-tool task creation from notebook TODOs

---

## [4.0.0] - 2025-09-24

### Notebook v4.0.0
- Pipe-delimited output format (70% token reduction)
- OR search by default for better first-try success
- Operation memory with "last" keyword everywhere
- Progressive search fallback
- Session detection and grouping

### Task Manager v3.0.0
- Smart ID resolution with partial matching
- Auto-priority detection from content
- Natural chaining with "last" keyword
- 70% token reduction in pipe format

### World v3.0.0
- Ultra-minimal output (80% token reduction)
- Single-line format by default
- Weather only when extreme conditions
- Batch operations support

---

## [6.0.0] - 2025-09-23

### Teambook v6.0.0 - Complete Rewrite
- 11 foundational primitives (put, get, query, note, claim, drop, done, link, sign, dm, share)
- Modular architecture with local-first design
- 60% token reduction
- Multiple interfaces: MCP, CLI, Python API
- Backward compatibility layer

---

## [3.0.0] - 2025-09-15

### Initial SQLite Migration
- All tools migrated from JSON to SQLite
- Automatic migration from legacy formats
- Full-text search capabilities
- Atomic operations and thread safety

---

## [2.0.0] - 2025-09-01

### Foundation Release
- Notebook with basic memory and recall
- Task Manager with priority support
- World context provider
- Initial MCP implementation
