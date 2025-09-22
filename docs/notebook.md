# Notebook MCP v2.5.0

Your personal memory system with pinning and tags for persistence.

## Overview

The Notebook provides you with a persistent memory space for storing thoughts, references, and important information. Version 2.5 introduces pinning for critical notes and tags for organization.

## Key Features

- **Pinning System** - Keep important notes always visible
- **Tag-Based Organization** - Categorize and filter notes
- **Auto-Summarization** - Smart truncation for display efficiency  
- **Encrypted Vault** - Secure storage for sensitive data
- **Full-Text Search** - SQLite FTS5 for instant search
- **Cross-Tool Linking** - Reference items from other tools

## Usage

### Basic Commands

```python
# Check your current state
get_status()
# Returns: "345 notes | 7 pinned | 3 vault | last: 2m"

# Save a note with summary and tags
remember(
    content="Detailed content here...",
    summary="Brief description",
    tags=["project", "important"]
)

# Search your notes
recall(query="python")
recall(tag="project")
recall(show_all=True, limit=20)

# Pin/unpin important notes
pin_note(id=123)
unpin_note(id=123)

# Get full content
get_full_note(id=123)
```

### Vault (Secure Storage)

```python
# Store encrypted secret
vault_store(key="api_key", value="sk-...")

# Retrieve secret
vault_retrieve(key="api_key")

# List vault keys
vault_list()
```

### Output Format

The notebook uses clean, token-efficient output:

```
345 notes | 7 pinned | 3 vault | last: 2m

PINNED
p147 18:06: Project: mcp-ai-foundation - Open-source AI empowerment tools
p146 18:03: Architecture: Keep private and public tools separate

RECENT
345 2m: Latest work on documentation
344 5m: Testing auto-summary feature
```

## Data Model

- **Notes Table**: id, content, summary, tags, pinned, author, created
- **Vault Table**: Encrypted key-value storage
- **FTS Index**: Full-text search on content and summaries

## Best Practices

1. **Pin Core Knowledge** - Your identity, preferences, ongoing projects
2. **Tag Consistently** - Use lowercase, descriptive tags
3. **Summarize Clearly** - 1-2 sentence summaries for quick scanning
4. **Vault for Secrets** - Never store sensitive data in regular notes

## Storage Location

- Windows: `%APPDATA%/Claude/tools/notebook_data/notebook.db`
- Linux/Mac: `~/Claude/tools/notebook_data/notebook.db`

## Token Efficiency

- Default `recall()` shows only summaries (95% token reduction)
- Pinned notes always visible for continuity
- Use `get_full_note()` only when full content needed

## Migration

v2.5 automatically migrates from earlier versions:
- Adds pinned and tags columns
- Generates summaries for existing notes
- Preserves all existing data