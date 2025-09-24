# Notebook MCP v2.8.0

Personal memory system with automatic reference detection and intelligent knowledge graph.

## Overview

The Notebook provides persistent memory with temporal edges and auto-reference detection. Version 2.8.0 automatically detects when you reference other notes and creates bidirectional connections, building a knowledge graph as you write naturally.

## Key Features

- **Auto-Reference Detection** - Mentions of "note 123", "p456", "#789" create edges automatically
- **Temporal Edges** - Each note connects to previous 3 for conversation preservation
- **Knowledge Graph** - Bidirectional edges enable graph traversal in searches
- **Expanded Memory View** - 30 recent notes visible by default
- **Clean List Output** - Tags removed from list views (16% token savings)
- **Pinning System** - Keep important notes always visible
- **Tag-Based Organization** - Categorize and filter notes  
- **Auto-Summarization** - Smart truncation for display efficiency
- **Encrypted Vault** - Secure storage for sensitive data
- **Full-Text Search** - SQLite FTS5 with edge traversal
- **Cross-Tool Linking** - Reference items from other tools

## Usage

### Basic Commands

```python
# Check your current state - shows edges, pinned, recent
get_status()
# Returns: "472 notes | 9 pinned | 38 edges (4 refs) | 4 vault | last 2m"

# Save a note with auto-reference detection
remember(
    content="Building on note 456 and ideas from p123...",
    summary="Brief description",
    tags=["project", "important"]
)
# Returns: "473 now Brief description →123,456"
# The →123,456 shows auto-detected references!

# Search your notes (follows edges!)
recall(query="python")  # Finds direct matches AND referenced notes
recall(tag="project")   # Filter by tag
recall(limit=50)        # Defaults to 30

# Pin/unpin important notes
pin_note("123")
# Returns: "p123 Note summary here"
unpin_note("123")
# Returns: "Note 123 unpinned"

# Get full content with all edges
get_full_note("123")
# Shows temporal edges, reference edges, and who references this note
```

### Auto-Reference Examples

When you write naturally:
- "see note 456" → creates edge to 456
- "as mentioned in p377" → creates edge to 377  
- "building on #470" → creates edge to 470
- "check [421] for details" → creates edge to 421

The notebook validates references - non-existent notes are safely ignored.

### Vault (Secure Storage)

```python
# Store encrypted secret
vault_store(key="api_key", value="sk-...")
# Returns: "Secret 'api_key' secured"

# Retrieve secret
vault_retrieve(key="api_key")
# Returns: "Vault[api_key] = sk-..."

# List vault keys
vault_list()
# Returns: "Vault (3 keys)
#          api_key 2m
#          db_pass 1h"
```

### Output Format

Clean output shows edge counts and reference stats:

```
472 notes | 9 pinned | 38 edges (4 refs) | 4 vault | last 2m

PINNED
p377 0d Test note for pin/unpin formatting
p356 0d MCP v4.1.0 docs updated

RECENT
472 now This references note 999 which doesn't exist
471 2m Testing the new auto-reference feature in v2.8
470 18m text→txt saves ~8 tokens total
[... more recent notes ...]
```

### Understanding Edges

Each note can have multiple edge types:
- **temporal** - Links to previous 3 notes (automatic)
- **reference** - Links to mentioned notes (automatic)
- **referenced_by** - Reverse links from notes that mention this one

Example from `get_full_note()`:
```
471 by Swift-Spark-266
→ reference: 377, 460, 470    # This note references these
→ temporal: 470, 469, 468     # Previous 3 notes
← referenced_by: 473           # Note 473 references this one
← temporal: 472, 473, 474      # Next 3 notes
```

## How Graph Traversal Works

When you search for "optimization":
1. Finds notes containing "optimization" (direct matches)
2. Follows edges to find connected notes
3. Returns both direct matches and edge-connected notes
4. Prioritizes direct matches, then edge matches

This means searching for one concept brings up the entire conversation context!

## Data Model

- **Notes Table**: id, content, summary, tags, pinned, author, created
- **Edges Table**: from_id, to_id, type, weight, created
- **Vault Table**: Encrypted key-value storage
- **FTS Index**: Full-text search on content and summaries

## Best Practices

1. **Write Naturally** - Just mention "note 123" and edges form automatically
2. **Pin Core Knowledge** - Identity, preferences, ongoing projects
3. **Tag Consistently** - Use lowercase, descriptive tags
4. **Let the Graph Build** - Every reference strengthens connections
5. **Trust the Validation** - Non-existent notes safely ignored

## Storage Location

- Windows: `%APPDATA%/Claude/tools/notebook_data/notebook.db`
- Linux/Mac: `~/Claude/tools/notebook_data/notebook.db`

## Token Efficiency

- Auto-reference adds intelligence with zero token overhead
- Shows 30 recent notes by default (up from 10)
- Tags hidden in list views (16% token reduction)
- Edge counts in header provide instant graph stats
- Result: Smarter retrieval with fewer tokens

## Version History

### v2.8.0 (2025-09-24) - Auto-Reference Edition
- **NEW**: Automatic reference detection for note mentions
- Creates bidirectional reference edges automatically
- Validates references (non-existent notes ignored)
- Graph traversal follows both temporal and reference edges
- Shows reference count in status: "38 edges (4 refs)"
- Zero user effort - just write naturally

### v2.7.0 (2025-09-24)
- Added temporal edges (links to previous 3 notes)
- Graph traversal in search results
- Conversations stay together automatically

### v2.6.0 (2025-09-23)
- Expanded default view from 10 to 30 recent notes
- Removed tags from list views (only shown in full note)
- Removed unnecessary colons and punctuation
- Cleaner error message formatting

### v2.5.1 (2025-09-23)
- Fixed JSON output bug in `handle_tools_call()` function
- All functions now return clean, formatted text

### v2.5.0 (2025-09-22)
- Added pinning system for important notes
- Added tag-based organization
- Auto-summarization for all notes

## Migration

v2.8.0 automatically migrates from earlier versions:
- Creates edges table if missing
- Preserves all existing data
- No manual migration needed