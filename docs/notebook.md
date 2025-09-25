# Notebook Tool - v4.0.0

Personal memory system with knowledge graph intelligence and extreme token efficiency.

## Overview

Notebook provides persistent memory with automatic relationship detection, importance ranking through PageRank, and intelligent search capabilities. Version 4.0 introduces pipe-delimited output format for 70% token reduction while maintaining full functionality.

## Key Features

### Core Capabilities
- **Graph-Based Memory**: Automatic edge creation between related notes
- **PageRank Scoring**: Importance ranking from ★0.0001 to ★0.01+
- **Entity Extraction**: Detects @mentions, tools, projects, IDs
- **Session Tracking**: Groups temporally related notes
- **Encrypted Vault**: Secure storage for sensitive data
- **Progressive Search**: Automatic fallback from exact to fuzzy matching

### v4.0 Improvements
- **Pipe Format Output**: 70% token reduction
- **OR Search Default**: Better first-attempt success
- **Operation Memory**: "last" keyword for natural chaining
- **Unified ID Format**: Consistent numeric identifiers
- **Minimal Decoration**: Pure data output

## Functions

### remember
Save a note with automatic relationship detection.

```python
notebook:remember(
  content="Information to store",
  summary="Brief description",  # Optional
  tags=["tag1", "tag2"],       # Optional
  linked_items=["item_id"]     # Optional
)
```

**Output (pipe format):**
```
537|now|Brief description|edges:2r/5e
```

### recall
Search notes with progressive fallback.

```python
notebook:recall(
  query="search terms",  # Optional
  tag="specific_tag",   # Optional
  limit=50,             # Optional (default: 50)
  show_all=False        # Optional
)
```

**Output (pipe format):**
```
523|16:33|Summary of note with high PageRank
529|58m|Another relevant note
524|16:33|Related content based on edges
```

### pin_note / unpin_note
Mark important notes for quick access.

```python
notebook:pin_note(id="537")  # or id="last"
notebook:unpin_note(id="537")
```

### get_full_note
Retrieve complete note with all connections.

```python
notebook:get_full_note(id="537")  # or id="last"
```

**Returns:** Complete note with content, edges, entities, and metadata.

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
notebook:get_status()
```

**Output (pipe format):**
```
notes:535|pinned:9|edges:664|entities:106|sessions:47|vault:4|last:3m|id:Swift-Spark-266
```

### batch
Execute multiple operations efficiently.

```python
notebook:batch(operations=[
  {"type": "remember", "args": {"content": "Note 1"}},
  {"type": "recall", "args": {"query": "search"}},
  {"type": "pin", "args": {"id": "last"}}
])
```

## Edge Types

The system automatically creates five types of edges:

1. **Temporal**: Connects to previous 3 notes
2. **Reference**: Links to mentioned note IDs
3. **Entity**: Connects notes mentioning same entities
4. **Session**: Links notes in same work session
5. **PageRank**: Weighted connections for importance

## Search Modes

### Progressive Fallback
1. **Exact phrase**: `"exact match"`
2. **OR search**: Any word matches
3. **Partial match**: Substring matching
4. **Fallback**: Longest word if all fail

### Search Tips
- Use fewer, specific keywords
- Avoid common words
- Entity names work best
- Tags provide precise filtering

## Configuration

### Environment Variables
```bash
# Output format: 'pipe' (default) or 'json'
export NOTEBOOK_FORMAT=pipe

# Search mode: 'or' (default) or 'and'
export NOTEBOOK_SEARCH=or

# Custom AI identity
export AI_ID=Custom-Agent-001
```

### Storage Location
- **Windows**: `%APPDATA%\Claude\tools\notebook_data\`
- **macOS/Linux**: `~/.claude/tools/notebook_data/`
- **Fallback**: System temp directory

## Technical Details

### Database Schema
- **notes**: Main content table with FTS5 indexing
- **edges**: Graph connections between notes
- **entities**: Extracted entities and mentions
- **sessions**: Work session grouping
- **vault**: Encrypted key-value storage

### Performance
- **PageRank**: Lazy calculation, cached for 5 minutes
- **Search**: FTS5 with automatic query cleaning
- **Batch**: Up to 50 operations per call
- **Entity Cache**: In-memory for fast matching

### Limits
- **Content**: 5000 characters per note
- **Summary**: 200 characters
- **Results**: 100 notes per search
- **Batch**: 50 operations maximum

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

# Later: Recall with context
notebook:recall("transformer attention")
# Returns notes ranked by PageRank, showing most connected/important first
```

### Team Collaboration
```python
# Store shared context
notebook:remember("@alice suggested using PyTorch for the model")
notebook:remember("@bob's implementation in pr_456 looks promising")

# Find all mentions
notebook:recall("@alice @bob")
# Returns notes mentioning either person
```

### Secure Credentials
```python
# Store securely
notebook:vault_store("openai_key", "sk-...")
notebook:vault_store("db_password", "secure123")

# Retrieve when needed
creds = notebook:vault_retrieve("openai_key")
```

## Migration Notes

### From v3.x to v4.0
- Output format changed to pipe-delimited by default
- Search uses OR logic by default (not AND)
- IDs are pure numbers (no brackets or prefixes)
- "last" keyword available for most operations
- Batch operations use type aliases (e.g., "pin" instead of "pin_note")

### Backward Compatibility
- Set `NOTEBOOK_FORMAT=json` for old format
- Set `NOTEBOOK_SEARCH=and` for old search behavior
- Database schema unchanged - no migration needed

---

Built for efficiency. Your memory doesn't just persist - it evolves.
