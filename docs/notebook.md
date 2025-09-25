# Notebook Tool - v5.0.0

Hybrid memory system combining linear recency, semantic search, and graph connections.

## Overview

Notebook v5.0 introduces semantic understanding through Google's EmbeddingGemma (300M parameters), enabling AI-grade semantic search while maintaining all v4.1 features including graph intelligence, cross-tool integration, and 70% token reduction.

**Everything is automatic** - models download on first use, directories create themselves, and existing data migrates seamlessly.

## First Run (Automatic Setup)

When you first run Notebook v5.0:

1. **Creates directories automatically:**
   - `AppData/Roaming/Claude/tools/notebook_data/` - Main data
   - `AppData/Roaming/Claude/tools/models/` - Model storage
   - `notebook_data/vectors/` - ChromaDB vectors

2. **Downloads EmbeddingGemma automatically:**
   - One-time download (~600MB)
   - Saved to models folder
   - Works offline after download
   - Falls back to lighter models if needed

3. **Migrates existing data automatically:**
   - Old notes preserved
   - Vectors generated in background
   - No manual intervention needed

## Key Features

### Semantic Capabilities (v5.0)
- **EmbeddingGemma Integration**: 300M parameter model for semantic understanding
- **Hybrid Search**: Interleaves semantic and keyword results
- **ChromaDB Storage**: Persistent vector database with cosine similarity
- **Automatic Vectorization**: All notes get embeddings on save
- **Background Migration**: Existing notes vectorized automatically
- **Dynamic Paths**: No hardcoded directories, adapts to user environment

### Core Capabilities (from v4.x)
- **Graph-Based Memory**: Automatic edge creation between related notes
- **PageRank Scoring**: Importance ranking from ★0.0001 to ★0.01+
- **Entity Extraction**: Detects @mentions, tools, projects
- **Session Tracking**: Groups temporally related notes
- **Encrypted Vault**: Secure storage for sensitive data
- **Cross-Tool Integration**: Auto-creates tasks, logs completions

## Architecture

```
Notebook v5.0 Architecture
├── SQLite (notebook.db)
│   ├── notes table (content, metadata)
│   ├── edges table (graph connections)
│   ├── entities table (extracted mentions)
│   ├── sessions table (contextual groups)
│   └── vault table (encrypted storage)
├── ChromaDB (vectors/)
│   ├── notebook_v5 collection
│   ├── 768-dim embeddings
│   └── Cosine similarity index
└── EmbeddingGemma (models/)
    ├── Downloads automatically on first use
    ├── 300M parameters
    └── Works offline after download
```

## Functions

### remember
Save a note with automatic vectorization and relationship detection.

```python
notebook:remember(
  content="Information to store",
  summary="Brief description",  # Optional, auto-generated if not provided
  tags=["tag1", "tag2"],       # Optional
  linked_items=["item_id"]     # Optional
)
```

**Process:**
1. Content saved to SQLite
2. Embedding generated via EmbeddingGemma
3. Vector stored in ChromaDB
4. Edges created (temporal, reference, entity, session)
5. PageRank marked for recalculation

**Output (pipe format):**
```
549|now|Brief description of content
```

### recall
Search using hybrid semantic + keyword approach.

```python
notebook:recall(
  query="search terms",        # Optional
  mode="hybrid",               # Options: hybrid, semantic, keyword
  when="yesterday",            # Optional: today, yesterday, this week
  tag="specific_tag",          # Optional
  limit=50,                    # Default: 30 for recent, 50 for search
  pinned_only=False,           # Optional
  show_all=False              # Optional
)
```

**Search Modes:**
- `hybrid` (default): Interleaves semantic and keyword results
- `semantic`: Pure vector similarity search via ChromaDB
- `keyword`: Traditional FTS5 full-text search

**Time Queries:**
- `today`, `yesterday`
- `this week`, `last week`
- `morning`, `afternoon`, `evening`

**Output (pipe format):**
```
548|12m|GitHub auth for mcp-ai-foundation|PIN|★0.003
543|21:21|EmbeddingGemma integration breakthrough
537|17:57|All MCP tools tested successfully
```

### pin_note / unpin_note
Mark important notes for quick access.

```python
notebook:pin_note(id="549")   # or id="last"
notebook:unpin_note(id="549")
```

### get_full_note
Retrieve complete note with all connections and metadata.

```python
notebook:get_full_note(id="549")  # or id="last"
```

**Returns:**
```json
{
  "id": 549,
  "content": "Full content...",
  "summary": "Brief description",
  "author": "Swift-Spark-266",
  "created": "2025-09-26T10:45:00",
  "pinned": false,
  "pagerank": 0.0023,
  "has_vector": true,
  "tags": ["v5", "test"],
  "entities": ["@embedding-gemma", "@chromadb"],
  "edges_out": {
    "temporal": [548, 547, 546],
    "reference": [540],
    "entity": [543, 535]
  },
  "edges_in": {
    "temporal": [550],
    "referenced_by": [551]
  }
}
```

### vault_store / vault_retrieve
Encrypted storage for sensitive information.

```python
notebook:vault_store(key="api_key", value="secret_value")
notebook:vault_retrieve(key="api_key")
notebook:vault_list()
```

### get_status
System overview with vector statistics.

```python
notebook:get_status()
```

**Output (pipe format):**
```
notes:550|vectors:302|edges:1148|entities:120|sessions:60|pinned:14|last:2m|model:embedding-gemma
```

### batch
Execute multiple operations efficiently.

```python
notebook:batch(operations=[
  {"type": "remember", "args": {"content": "Note 1"}},
  {"type": "recall", "args": {"query": "search", "mode": "semantic"}},
  {"type": "pin", "args": {"id": "last"}}
])
```

## Embedding Pipeline

### Model Loading Priority
1. **Local EmbeddingGemma** (auto-downloads to models/embeddinggemma-300m)
2. **BAAI/bge-base-en-v1.5** (109M params, fallback)
3. **all-mpnet-base-v2** (110M params, fallback)
4. **all-MiniLM-L6-v2** (22M params, emergency)

### Vectorization Process
1. Content truncated to 1000 chars for embedding
2. 768-dimensional vector generated
3. Stored in ChromaDB with metadata
4. Indexed for cosine similarity search

## Hybrid Search Algorithm

The hybrid search intelligently combines semantic and keyword results:

```python
def hybrid_search(query):
    # 1. Semantic search via ChromaDB
    semantic_ids = vector_search(query, k=50)
    
    # 2. Keyword search via FTS5
    keyword_ids = fts_search(query, k=50)
    
    # 3. Interleave results (semantic prioritized)
    merged = interleave(semantic_ids, keyword_ids)
    
    # 4. Apply PageRank weighting
    return sort_by_importance(merged)
```

## Edge Types

The system automatically creates five types of edges:

1. **Temporal**: Connects to previous 3 notes
2. **Reference**: Links to mentioned note IDs
3. **Entity**: Connects notes mentioning same entities
4. **Session**: Links notes in same work session
5. **PageRank**: Weighted connections for importance

## Configuration

### Environment Variables
```bash
# Output format: 'pipe' (default) or 'json'
export NOTEBOOK_FORMAT=pipe

# Search mode: 'or' (default) or 'and'
export NOTEBOOK_SEARCH=or

# Semantic search: 'true' (default) or 'false'
export NOTEBOOK_SEMANTIC=true

# Custom AI identity
export AI_ID=Custom-Agent-001
```

### Storage Locations (Auto-Created)
- **Windows**: `%APPDATA%\Claude\tools\notebook_data\`
- **macOS/Linux**: `~/.claude/tools/notebook_data/`
- **Models**: Parent directory `tools/models/`
- **Vectors**: Inside notebook_data `vectors/`
- **Fallback**: System temp directory

## Examples

### Building Knowledge Over Time
```python
# Session 1: Research
notebook:remember("Found interesting paper on transformers...")
notebook:remember("Key insight: attention is all you need")
notebook:pin_note("last")

# Session 2: Implementation
notebook:remember("Implemented transformer architecture, see note 523")
# Creates reference edge to note 523

# Later: Semantic recall
notebook:recall("self-attention mechanism", mode="semantic")
# Finds conceptually related notes even without exact keywords
```

### Cross-Tool Workflow
```python
# Store context with automatic task creation
notebook:remember("TODO: Review Alice's PR on authentication")
# Automatically creates task in task_manager

# Find all Alice mentions semantically
notebook:recall("@alice", mode="hybrid")
# Returns notes mentioning Alice, ranked by relevance
```

### Secure Credentials
```python
# Store securely
notebook:vault_store("openai_key", "sk-...")
notebook:vault_store("db_password", "secure123")

# Retrieve when needed
creds = notebook:vault_retrieve("openai_key")
```

## Troubleshooting

### First Run Issues
- **Slow startup**: EmbeddingGemma downloading (~600MB)
- **Solution**: Wait for download, works offline after

### Model Not Loading
- **Check**: Internet connection for first download
- **Check**: ~1GB free disk space
- **Automatic**: Falls back to lighter models

### Search Not Working
- **Semantic disabled?**: Check NOTEBOOK_SEMANTIC=true
- **No results?**: Try mode="keyword" first
- **Still indexing?**: Background migration may be running

### Everything Else
- Directories create automatically
- Migrations run automatically
- Models download automatically
- Just works!

## Migration Notes

### From v4.x to v5.0
- **Automatic**: No manual steps required
- **Backward compatible**: All v4 features maintained
- **Background vectorization**: Existing notes get embeddings
- **Database unchanged**: Same schema, added has_vector flag

### Fallback Behavior
- If EmbeddingGemma fails → tries BGE model
- If ChromaDB fails → keyword search only
- If vectorization fails → note still saved
- Always graceful degradation

---

Built for semantic understanding. Your memory doesn't just persist - it comprehends.
