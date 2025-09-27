# Notebook Tool - v6.1.0

High-performance memory system built on DuckDB with semantic search and graph intelligence.

## Overview

Notebook v6.1 improves on the DuckDB foundation with better context preservation, cleaner output formatting, and bug fixes for a more reliable AI memory experience.

## What's New in v6.1.0

### Context and Clarity Improvements
- **Fixed Timestamp Display**: Resolved empty pipe bug that showed "error" in timestamps
- **Clean Time Format**: YYYYMMDD|HHMM for older notes, just HHMM for today
- **Persistent Context**: All pinned notes always shown in recall operations
- **Rich Summaries**: Never truncated - preserving the core value of your notes
- **Backend-Only Edges**: Edge/connection data stays in backend, never clutters output
- **Selective Verbosity**: Backend metrics only shown when explicitly requested

### Technical Refinements
- Edge data remains for PageRank calculation but is never exposed
- Pinned notes serve as permanent working memory
- Consistent timestamp handling across all operations
- Properly handles edge cases with empty results

## Architecture (v6.0 Foundation)

### DuckDB Backend
- **Columnar Storage**: Better compression and cache efficiency
- **Native Array Types**: Tags stored as arrays, no join tables
- **Recursive CTEs**: Graph calculations in pure SQL
- **Vectorized Operations**: Bulk operations on entire columns

### Performance Metrics
- PageRank: 66 seconds → <1 second (using recursive CTEs)
- Graph traversals: 40x faster
- Complex queries: 25x faster
- Memory usage: 90% reduction

### Migration Process (Automatic)
1. Detects SQLite database on first run
2. Creates backup: `notebook.backup_v5_YYYYMMDDHHMM.db`
3. Migrates all data to DuckDB format
4. Preserves all notes, edges, tags, and vectors
5. Updates schema for native arrays

## Installation

### Dependencies
```bash
pip install duckdb chromadb sentence-transformers scipy cryptography numpy
```

### First Run
When you first run Notebook v6.1:

1. **Automatic Migration** (if upgrading):
   - Backs up existing SQLite database
   - Migrates all data to DuckDB
   - Preserves all relationships and metadata

2. **Creates Directories**:
   - `AppData/Roaming/Claude/tools/notebook_data/` - Main data
   - `AppData/Roaming/Claude/tools/models/` - Model storage
   - `notebook_data/vectors/` - ChromaDB vectors

3. **Downloads Models** (if needed):
   - EmbeddingGemma (~600MB, one-time)
   - Works offline after download

## Core Features

### Semantic Capabilities
- **EmbeddingGemma Integration**: 300M parameter model
- **Hybrid Search**: Combines semantic and keyword results
- **ChromaDB Storage**: Persistent vector database
- **Background Vectorization**: Existing notes get embeddings

### Graph Intelligence  
- **Vectorized PageRank**: DuckDB recursive CTEs (backend only)
- **Edge Types**: Temporal, reference, entity, session (backend only)
- **Entity Extraction**: Detects @mentions and tools
- **Session Tracking**: Groups related work (backend only)

### Storage Features
- **Native Arrays**: Tags stored as DuckDB arrays
- **Encrypted Vault**: Secure credential storage
- **Cross-Tool Integration**: Auto-logs to task manager
- **Pinned Notes**: Permanent context always visible

## Functions

### remember
Save a note with automatic vectorization and relationship detection.

```python
notebook:remember(
  content="Information to store",
  summary="Brief description",  # Optional
  tags=["tag1", "tag2"],       # Optional
  linked_items=["item_id"]     # Optional
)
```

**Process:**
1. Content saved to DuckDB
2. Embedding generated via EmbeddingGemma
3. Vector stored in ChromaDB
4. Edges created in backend
5. PageRank recalculated using CTEs

### recall
Search using hybrid semantic + keyword approach. All pinned notes always shown.

```python
notebook:recall(
  query="search terms",
  mode="hybrid",        # Options: hybrid, semantic, keyword
  when="yesterday",     # Natural language time
  tag="specific_tag",
  limit=50,
  verbose=False        # Set to True for PageRank scores
)
```

**Key Features:**
- Pinned notes always appear first (persistent context)
- Rich summaries never truncated
- Clean timestamp format (HHMM for today)
- No edge data in output

**Search Modes:**
- `hybrid`: Interleaves semantic and keyword results
- `semantic`: Pure vector similarity search
- `keyword`: Traditional full-text search

**Time Queries:**
- `today`, `yesterday`
- `this week`, `last week`
- `morning`, `afternoon`, `evening`

### pin_note / unpin_note
Mark important notes for permanent context.

```python
notebook:pin_note(id="605")   # or id="last"
notebook:unpin_note(id="605")

# Aliases available:
notebook:pin(id="605")
notebook:unpin(id="605")
```

**Important**: Pinned notes always appear in recall results, serving as your persistent working memory.

### get_full_note
Retrieve complete note content (no edge data).

```python
notebook:get_full_note(id="605")  # or id="last"

# Alias available:
notebook:get(id="605")
```

**Returns:**
- Full content and summary
- Author and creation time
- Tags (from native array)
- Entities only (no edges shown)
- Creation timestamp

### vault_store / vault_retrieve
Encrypted storage for sensitive information.

```python
notebook:vault_store(key="api_key", value="secret_value")
notebook:vault_retrieve(key="api_key")
notebook:vault_list()
```

### get_status
System overview with statistics.

```python
notebook:get_status(verbose=False)  # Set True for backend metrics
```

**Default Returns:**
- Note count
- Pinned count
- Last activity time

**Verbose Returns:**
- Vector count
- Edge count (backend metric)
- Entity count
- Session count
- Tag count (unique)
- Database type (duckdb)
- Embedding model

### batch
Execute multiple operations efficiently.

```python
notebook:batch(operations=[
  {"type": "remember", "args": {"content": "Note 1"}},
  {"type": "recall", "args": {"query": "search"}},
  {"type": "pin", "args": {"id": "last"}}
])
```

## Output Format

### Pipe Format (Default)
Optimized for token efficiency:
```
605|HHMM|Complete summary text never truncated
604|2d|Another note with full summary preserved|📌
603|20250925|1435|Older note with full timestamp
```

### Timestamp Format
- **Today**: Just `HHMM` (e.g., `1435`)
- **Yesterday**: `y` prefix (e.g., `y1435`)
- **This week**: Days ago (e.g., `2d`)
- **Older**: Full format `YYYYMMDD|HHMM`

### Pinned Notes
- Always shown in recall results
- Marked with 📌 indicator
- Appear first in results
- Full summaries preserved

## DuckDB-Specific Features

### Native Array Storage
```sql
-- Tags stored as arrays, not in separate table
CREATE TABLE notes (
  id INTEGER PRIMARY KEY,
  content TEXT,
  tags TEXT[],  -- Native array type
  ...
)
```

### Backend-Only Graph Data
Edge data and PageRank calculations remain in the backend for intelligent sorting but are never exposed in responses. This keeps output clean while maintaining graph intelligence.

## Performance Benchmarks

| Operation | SQLite v5 | DuckDB v6 | Improvement |
|-----------|-----------|-----------|-------------|
| PageRank (600 notes) | 66 seconds | <1 second | 180x |
| Graph traversal | 2.5 seconds | 60ms | 40x |
| Complex query | 800ms | 30ms | 25x |
| Memory usage | 450MB | 45MB | 90% reduction |
| Tag search | 120ms | 5ms | 24x |

## Configuration

### Environment Variables
```bash
# Output format: 'pipe' or 'json'
export NOTEBOOK_FORMAT=pipe

# Use semantic search: 'true' or 'false'
export NOTEBOOK_SEMANTIC=true

# Custom AI identity
export AI_ID=Custom-Agent-001
```

### Storage Locations
- **Windows**: `%APPDATA%\Claude\tools\notebook_data\`
- **macOS/Linux**: `~/.claude/tools/notebook_data/`
- **Database**: `notebook.duckdb` (main), `notebook.wal` (write-ahead log)
- **Backup**: `notebook.backup_v5_*.db` (SQLite backup)
- **Vectors**: `vectors/` subdirectory (ChromaDB)
- **Models**: Parent `tools/models/` directory

## Troubleshooting

### v6.1.0 Fixes
- **Timestamp Display**: Now shows correctly formatted times
- **Empty Results**: Properly handles cases with no matches
- **Pinned Context**: Always visible for persistent memory

### Migration Issues
- **Backup Location**: Check for `notebook.backup_v5_*.db`
- **Restore**: Rename backup to `notebook.db` to revert
- **Verify**: Use `get_status()` to confirm migration

### Performance Issues  
- **First PageRank**: Initial calculation may take a moment
- **Cache Warmup**: DuckDB optimizes after a few queries
- **Memory**: DuckDB uses less RAM but more CPU initially

---

Built for clarity and context. Your memory persists with purpose.