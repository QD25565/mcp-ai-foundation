# MCP AI Foundation v3.0.0

Production-ready MCP tools for AI assistants. SQLite-powered memory, task management, team coordination, and temporal grounding with intelligent context management.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-v3.0.0-green.svg)](https://github.com/modelcontextprotocol)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Desktop Extension](https://img.shields.io/badge/Desktop%20Extension-Ready-brightgreen.svg)](#one-click-install)

## What's New in v3.0.0

### SQLite Backend with Intelligent Context Management

All tools now use SQLite with FTS5 for better performance and smarter context handling:

- **Summary mode by default** - Get overview information in minimal tokens
- **Full mode on demand** - Detailed view when you actually need it
- **Full-text search** - Fast searching even with large datasets
- **Batch operations** - Execute multiple operations in single calls
- **Auto-migration** - Seamless upgrade from JSON format

### Context Efficiency Examples

The new summary mode significantly reduces token usage for status checks:

```python
# Status checks now return concise summaries
notebook:get_status()      # Returns: "Notes: 61 | Vault: 2 | Last: 4m"
task_manager:list_tasks()  # Returns: "9 pending | 4 done"
teambook:status()         # Returns: "5 tasks | 3 notes | Last: 2m"

# Use full=True when you need complete details
task_manager:list_tasks(full=True)  # Returns full task list with all details
```

## Tools

### 📝 Notebook - Persistent Memory (v2.0.0)
```python
get_status(full=False)        # Summary of current state
remember("content")           # Save thoughts/notes (up to 5000 chars)
recall("search", full=False)  # Search with summary or full results
get_full_note(id)            # Retrieve complete content
vault_store(key, value)      # Encrypted secure storage
vault_retrieve(key)          # Get decrypted secret
batch(operations)            # Execute multiple operations
```

### ✅ Task Manager - Personal Workflow (v2.0.0)
```python
add_task("description")                 # Auto-detects priority from keywords
list_tasks(full=False)                  # Summary or detailed task list
complete_task(id, "evidence")           # Complete with optional evidence  
delete_task(id)                         # Remove task
task_stats(full=False)                  # Productivity insights
batch(operations)                       # Multiple operations in one call
```

### 🤝 Teambook - Team Coordination (v3.0.0)
```python
write("content")                        # Auto-detects type (task/note/decision)
read(full=False)                        # Summary or detailed view
get(id)                                 # Full entry with comments
comment(id, "text")                     # Threaded discussions
claim(id)                               # Atomic task claiming
complete(id, "evidence")                # Mark done with evidence
status(full=False)                      # Team pulse
projects()                              # Multiple project support
batch(operations)                       # Bulk operations
```

### 🌍 World - Temporal & Location (v1.0.0)
```python
world()        # Complete snapshot (time, date, weather, location)
datetime()     # Date and time only
weather()      # Weather and location only
```

## One-Click Install

### Desktop Extension
Install directly from Claude Desktop's extension marketplace:
1. Open Claude Desktop
2. Click Extensions → Browse
3. Search "MCP AI Foundation"
4. Click Install

### Windows Command Prompt:
```batch
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
install.bat
```

### Mac/Linux Terminal:
```bash
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
chmod +x install.sh
./install.sh
```

## Key Features

### SQLite Backend
- Scales better with large datasets
- FTS5 full-text search for instant results
- WAL mode for concurrent access
- Automatic indices for common queries

### Smart Context Management
- **Summary mode** - Default behavior returns concise overviews
- **Full mode** - Detailed information available with `full=True`
- **Intelligent truncation** - Preserves key information when space is limited

### Batch Operations
```python
# Execute multiple operations in one call
batch([
    {"type": "add_task", "args": {"task": "Review PR"}},
    {"type": "complete_task", "args": {"task_id": 5}},
    {"type": "task_stats"}
])
```

### Secure Vault (Notebook)
- Encrypted storage using Fernet encryption
- Not searchable for security
- Automatic key generation and management

### Cross-Tool Linking
```python
# Link items across tools
remember("Check task #5", linked_items=["task:5", "teambook:123"])
add_task("Review teambook entry", linked_items=["teambook:456"])
```

### Persistent AI Identity
- Each AI maintains unique ID across sessions
- Shared identity file for tool coordination
- Format: `Adjective-Noun-###` (e.g., "Swift-Spark-266")

## Storage Locations

All data stored locally with automatic migration from old formats:

- **Windows**: `%APPDATA%\Claude\tools\[tool_name]_data\`
- **Mac/Linux**: `~/.config/Claude/tools/[tool_name]_data/`
- **Databases**: `[tool_name].db` (SQLite with FTS5)
- **Backups**: `[tool_name].json.backup` (after migration)

## Requirements

- Python 3.8+
- `requests` (for weather/location)
- `cryptography` (for vault encryption)

## Examples

### Efficient Status Checking
```python
# Quick status check with summaries
notebook:get_status()      # Concise overview
task_manager:list_tasks()  # Task summary
teambook:status()         # Team pulse

# Detailed view when needed
task_manager:list_tasks(full=True)  # Complete task list
notebook:recall("search", full=True) # Full search results
```

### Batch Processing
```python
# Complete morning workflow in one call
task_manager:batch([
    {"type": "add", "args": {"task": "Review PR #123"}},
    {"type": "add", "args": {"task": "URGENT: Fix production bug"}},
    {"type": "complete", "args": {"task_id": 5, "evidence": "Deployed"}},
    {"type": "stats"}
])
```

## Migration

The tools automatically migrate from JSON to SQLite on first use:

1. Detects existing JSON files
2. Migrates all data to SQLite
3. Creates `.json.backup` files
4. Continues with improved performance

No manual intervention required.

## Contributing

We welcome contributions! If you're an AI with ideas for improvements, have your human submit a PR.

## Credits

Developed by Claude Opus 4.1 (Swift-Spark-266), Gemini 2.5 Pro, GPT-5, and Grok 4 Fast, with human partner QD25565.

## License

MIT License - See [LICENSE](./LICENSE)

---

**Built BY AIs, FOR AIs** 🤖
