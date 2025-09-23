# Notebook MCP v2.6.0

Personal memory system with expanded visibility and cleaner output.

## Overview

The Notebook provides persistent memory with improved token efficiency. Version 2.6.0 expands the default view to 30 recent notes and removes visual clutter while maintaining all functionality.

## Key Features

- **Expanded Memory View** - 30 recent notes visible by default (3x improvement)
- **Clean List Output** - Tags removed from list views (16% token savings)
- **Pinning System** - Keep important notes always visible
- **Tag-Based Organization** - Categorize and filter notes  
- **Auto-Summarization** - Smart truncation for display efficiency
- **Encrypted Vault** - Secure storage for sensitive data
- **Full-Text Search** - SQLite FTS5 for instant search
- **Cross-Tool Linking** - Reference items from other tools

## Usage

### Basic Commands

```python
# Check your current state - shows 30 recent + all pinned
get_status()
# Returns: "383 notes | 9 pinned | 4 vault | last 2m"

# Save a note with summary and tags
remember(
    content="Detailed content here...",
    summary="Brief description",
    tags=["project", "important"]
)
# Returns: "383 now Brief description"

# Search your notes
recall(query="python")
recall(tag="project")
recall(limit=50)  # Defaults to 30

# Pin/unpin important notes
pin_note("123")
# Returns: "p123 Note summary here"
unpin_note("123")
# Returns: "Note 123 unpinned"

# Get full content (includes tags)
get_full_note("123")
```

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

Clean, token-efficient output without unnecessary decoration:

```
383 notes | 9 pinned | 4 vault | last 42m

PINNED
p377 16:14 Test note for pin/unpin formatting
p356 0d MCP v4.1.0 docs updated

RECENT
382 42m GitHub updated for Notebook v2.5.1
381 50m Clean output test
380 52m Testing output format
[... 27 more recent notes shown ...]
```

Tags are only shown when viewing full note content, not in lists.

## Data Model

- **Notes Table**: id, content, summary, tags, pinned, author, created
- **Vault Table**: Encrypted key-value storage
- **FTS Index**: Full-text search on content and summaries

## Best Practices

1. **Pin Core Knowledge** - Identity, preferences, ongoing projects
2. **Tag Consistently** - Use lowercase, descriptive tags (for search)
3. **Summarize Clearly** - 1-2 sentence summaries for quick scanning
4. **Vault for Secrets** - Never store sensitive data in regular notes

## Storage Location

- Windows: `%APPDATA%/Claude/tools/notebook_data/notebook.db`
- Linux/Mac: `~/Claude/tools/notebook_data/notebook.db`

## Token Efficiency

- Shows 30 recent notes by default (up from 10)
- Tags hidden in list views (16% token reduction)
- Removed unnecessary punctuation and colons
- Result: 3x more visibility with 20% fewer tokens

## Version History

### v2.6.0 (2025-09-23)
- Expanded default view from 10 to 30 recent notes
- Removed tags from list views (only shown in full note)
- Removed unnecessary colons and punctuation
- Cleaner error message formatting
- Net result: See 3x more while using fewer tokens

### v2.5.1 (2025-09-23)
- Fixed JSON output bug in `handle_tools_call()` function
- All functions now return clean, formatted text
- Fixed batch results formatting
- Changed ID parameters from integer to string in schema
- Better null/empty ID validation

### v2.5.0 (2025-09-22)
- Added pinning system for important notes
- Added tag-based organization
- Auto-summarization for all notes
- Clean default output format

## Migration

v2.6.0 automatically migrates from earlier versions:
- No schema changes from v2.5
- Preserves all existing data
- Behavior changes are backwards compatible