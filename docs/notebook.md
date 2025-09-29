<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=35&duration=1&pause=10000&color=878787&background=00000000&center=true&vCenter=true&width=500&lines=NOTEBOOK+v6.2.0" alt="NOTEBOOK v6.2.0" />
</div>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&duration=1&pause=10000&color=82A473&background=00000000&center=true&vCenter=true&width=700&lines=AI+Memory+System+with+DuckDB%2C+Semantic+Search+and+Modular+Architecture" alt="AI Memory System with DuckDB, Semantic Search and Modular Architecture" />

### **WHAT'S NEW IN v6.2.0**
![](images/header_underline.png)

#### Three-File Architecture
The notebook has been refactored from a single 2500+ line file into three focused modules:
- **notebook_shared.py** - Constants, configuration, and utility functions
- **notebook_storage.py** - Database operations, vector storage, and persistence
- **notebook_main.py** - Core API functions and MCP protocol handler

#### New Features
- **Directory Tracking** - Automatically tracks directories mentioned in notes for navigation clarity
- **Database Maintenance** - New `compact()` function runs VACUUM to optimize and defragment DuckDB
- **Fixed Pinned Bug** - Pinned notes now correctly always appear in recall operations
- **Recent Directories** - Track last 10 accessed directories with `recent_dirs()` function

### **ARCHITECTURE**
![](images/header_underline.png)

#### DuckDB Backend
- **Columnar Storage** - Better compression and cache efficiency
- **Native Array Types** - Tags stored as arrays, no join tables needed
- **Recursive CTEs** - Graph calculations in pure SQL
- **Vectorized Operations** - Bulk operations on entire columns
- **VACUUM Support** - Periodic maintenance keeps database optimized

#### Performance Metrics
- PageRank: <1 second (using recursive CTEs)
- Graph traversals: 40x faster than SQLite
- Complex queries: 25x faster
- Memory usage: 90% reduction
- Database can be compacted with `compact()` function

#### Migration Process (Automatic)
1. Detects SQLite database on first run
2. Creates backup: `notebook.backup_{timestamp}.db`
3. Migrates all data to DuckDB format
4. Preserves all notes, edges, tags, and vectors
5. Updates schema for native arrays

### **INSTALLATION**
![](images/header_underline.png)

#### Dependencies
```bash
pip install duckdb chromadb sentence-transformers cryptography numpy scipy
```

#### First Run
When you first run Notebook v6.2:

1. **Automatic Migration** (if upgrading):
   - Backs up existing SQLite database
   - Migrates all data to DuckDB
   - Preserves all relationships and metadata

2. **Creates Directories**:
   - `AppData/Roaming/Claude/tools/notebook_data/` - Main data
   - `AppData/Roaming/Claude/tools/models/` - Model storage
   - `notebook_data/vectors/` - ChromaDB vectors

3. **Loads Models** (if available):
   - Automatically discovers local models in models/ directory
   - Falls back to downloading if no local models found
   - Works offline after initial model setup

### **CORE FEATURES**
![](images/header_underline.png)

#### Semantic Capabilities
- **Local Model Support** - Auto-discovers models in models/ directory
- **Hybrid Search** - Combines semantic and keyword results
- **ChromaDB Storage** - Persistent vector database
- **Background Vectorization** - Existing notes get embeddings automatically

#### Graph Intelligence  
- **Vectorized PageRank** - DuckDB recursive CTEs (backend only)
- **Edge Types** - Temporal, reference, entity, session (backend only)
- **Entity Extraction** - Detects @mentions and tools
- **Session Tracking** - Groups related work (backend only)

#### Storage Features
- **Native Arrays** - Tags stored as DuckDB arrays
- **Encrypted Vault** - Secure credential storage
- **Cross-Tool Integration** - Auto-logs to task manager
- **Pinned Notes** - Permanent context always visible
- **Directory Tracking** - Remembers paths you work with

### **FUNCTIONS**
![](images/header_underline.png)

#### remember
Save a note with automatic vectorization and relationship detection.

```python
notebook:remember(
  content="Information to store",
  summary="Brief description",  # Optional
  tags=["tag1", "tag2"],       # Optional
  linked_items=["item_id"]     # Optional
)
```

Process:
1. Content saved to DuckDB
2. Embedding generated if model available
3. Vector stored in ChromaDB
4. Edges created in backend
5. PageRank recalculated using CTEs
6. Directories tracked if mentioned

#### recall
Search using hybrid semantic + keyword approach. All pinned notes always shown.

```python
notebook:recall(
  query="search terms",
  mode="hybrid",        # Options: hybrid, semantic, keyword
  when="yesterday",     # Natural language time
  tag="specific_tag",
  limit=50,
  pinned_only=False,   # Fixed in v6.2
  verbose=False        # Set to True for PageRank scores
)
```

Key Features:
- Pinned notes always appear first (bug fixed in v6.2)
- Rich summaries never truncated
- Clean timestamp format (HHMM for today)
- No edge data in output

Time Queries:
- `today`, `yesterday`
- `this week`, `last week`
- `morning`, `afternoon`, `evening`

#### pin_note / unpin_note
Mark important notes for permanent context.

```python
notebook:pin_note(id="605")   # or id="last"
notebook:unpin_note(id="605")

# Aliases available:
notebook:pin(id="605")
notebook:unpin(id="605")
```

#### get_full_note
Retrieve complete note content (no edge data).

```python
notebook:get_full_note(id="605")  # or id="last"

# Alias available:
notebook:get(id="605")
```

#### vault_store / vault_retrieve
Encrypted storage for sensitive information.

```python
notebook:vault_store(key="api_key", value="secret_value")
notebook:vault_retrieve(key="api_key")
notebook:vault_list()
```

#### recent_dirs (NEW in v6.2)
Get recently accessed directories.

```python
notebook:recent_dirs(limit=5)
# Returns list of recent directory paths
```

#### compact (NEW in v6.2)
Run VACUUM to optimize and defragment database.

```python
notebook:compact()
# Returns size reduction and performance stats
```

#### get_status
System overview with statistics.

```python
notebook:get_status(verbose=False)  # Set True for backend metrics
```

Default Returns:
- Note count
- Pinned count
- Last activity time

Verbose Returns:
- Vector count
- Edge count (backend metric)
- Entity count
- Session count
- Tag count (unique)
- Recent directories
- Database type (duckdb)
- Embedding model

#### batch
Execute multiple operations efficiently.

```python
notebook:batch(operations=[
  {"type": "remember", "args": {"content": "Note 1"}},
  {"type": "recall", "args": {"query": "search"}},
  {"type": "pin", "args": {"id": "last"}},
  {"type": "compact", "args": {}}
])
```

### **OUTPUT FORMAT**
![](images/header_underline.png)

#### Pipe Format (Default)
Optimized for token efficiency:
```
605|HHMM|Complete summary text never truncated
604|2d|Another note with full summary preserved|📌
603|20250925|1435|Older note with full timestamp
```

#### Timestamp Format
- **Today** - Just `HHMM` (e.g., `1435`)
- **Yesterday** - `y` prefix (e.g., `y1435`)
- **This week** - Days ago (e.g., `2d`)
- **Older** - Full format `YYYYMMDD|HHMM`

### **MODULAR ARCHITECTURE**
![](images/header_underline.png)

#### File Structure
```
notebook_main.py       # Core API and MCP handler
notebook_storage.py    # Database and vector operations
notebook_shared.py     # Utilities and constants
```

#### Benefits
- Easier maintenance and debugging
- Clear separation of concerns
- Reusable components
- Better testability

### **PERFORMANCE BENCHMARKS**
![](images/header_underline.png)

| Operation | SQLite v5 | DuckDB v6 | Improvement |
|-----------|-----------|-----------|-------------|
| PageRank (600 notes) | 66 seconds | <1 second | 180x |
| Graph traversal | 2.5 seconds | 60ms | 40x |
| Complex query | 800ms | 30ms | 25x |
| Memory usage | 450MB | 45MB | 90% reduction |
| Tag search | 120ms | 5ms | 24x |
| VACUUM operation | N/A | 2-3 seconds | New feature |

### **CONFIGURATION**
![](images/header_underline.png)

#### Environment Variables
```bash
# Output format: 'pipe' or 'json'
export NOTEBOOK_FORMAT=pipe

# Use semantic search: 'true' or 'false'
export NOTEBOOK_SEMANTIC=true

# Custom AI identity
export AI_ID=Custom-Agent-001
```

#### Storage Locations
- **Windows**: `%APPDATA%\Claude\tools\notebook_data\`
- **macOS/Linux**: `~/.claude/tools/notebook_data/`
- **Database**: `notebook.duckdb` (main), `notebook.wal` (write-ahead log)
- **Backup**: `notebook.backup_{timestamp}.db` (SQLite backup)
- **Vectors**: `vectors/` subdirectory (ChromaDB)
- **Models**: Parent `tools/models/` directory

### **TROUBLESHOOTING**
![](images/header_underline.png)

#### v6.2.0 Fixes
- **Pinned Notes** - Fixed bug where pinned_only filter wasn't working
- **Directory Tracking** - Automatic path detection and storage
- **Database Maintenance** - Use `compact()` to optimize performance

#### Migration Issues
- **Backup Location** - Check for `notebook.backup_*.db`
- **Restore** - Rename backup to `notebook.db` to revert
- **Verify** - Use `get_status()` to confirm migration

#### Performance Issues  
- **Database Size** - Run `compact()` to defragment and optimize
- **First PageRank** - Initial calculation may take a moment
- **Cache Warmup** - DuckDB optimizes after a few queries

<div align="center">

Built for AIs, by AIs. 🤖

</div>
