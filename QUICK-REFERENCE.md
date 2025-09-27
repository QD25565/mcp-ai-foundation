# Quick Reference - MCP AI Foundation v6.1.0

## 📓 Notebook v6.1.0
```python
# Status
get_status()                   # Note count, pinned count, last activity
get_status(verbose=True)       # Include backend metrics

# Memory
remember("content", summary="Brief", tags=["tag1"])
recall("search")              # All pinned notes + search results
recall(when="yesterday")      # Time-based queries
recall(tag="project")         # Tag filter
get_full_note(id="605")       # Full content (no edges)
get(id="last")               # Alias for get_full_note

# Pinning for Context
pin_note(id="605")           # Pin for permanent context
pin(id="last")               # Alias
unpin_note(id="605")         # Unpin
unpin(id="605")              # Alias

# Encrypted Vault
vault_store("api_key", "secret_value")
vault_retrieve("api_key")
vault_list()

# Batch Operations
batch([
    {"type": "remember", "args": {"content": "Note 1"}},
    {"type": "pin", "args": {"id": "last"}},
    {"type": "recall", "args": {"query": "search"}}
])
```

## ✅ Task Manager v3.1.0
```python
# Task Management
add_task("Review PR #123")              # Auto-priority detection
list_tasks()                            # Default: pending tasks
list_tasks(when="today")               # Time-based filtering
list_tasks(filter="completed")         # Status filter
complete_task("last", "Done")          # Smart ID resolution
complete_task("45", evidence="Fixed")  # Partial ID match
delete_task("45")                       # Delete task

# Statistics
task_stats()                           # Minimal stats
task_stats(full=True)                  # Detailed insights

# Batch Operations
batch([
    {"type": "add", "args": {"task": "Task 1"}},
    {"type": "complete", "args": {"task_id": "last"}},
    {"type": "list", "args": {"when": "today"}}
])
```

## 🌐 Teambook v6.0.0
```python
# Core Primitives (v6.0)
put(content, meta=None)        # Add to log
get(id)                        # Get specific entry
query(filter=None)             # Search entries
note(id, content)              # Add note to entry
claim(id)                      # Claim a task
done(id, result=None)          # Complete task
drop(id)                       # Unclaim task
link(from_id, to_id, type)     # Create relationship
sign(id, signature)            # Sign entry
dm(to_id, content)             # Direct message
share(project, content)        # Share to project

# Compatibility Layer (MCP)
write(content, type=None)      # Maps to put()
read(full=False)               # Maps to query()
comment(id, content)           # Maps to note()
complete(id, evidence=None)    # Maps to done()
status()                       # Team status

# Batch Operations
batch([
    {"type": "write", "args": {"content": "Note"}},
    {"type": "claim", "args": {"id": 10}},
    {"type": "complete", "args": {"id": 10}}
])
```

## 🌍 World v3.0.0
```python
# Context (ultra-minimal by default)
world()                        # Time + location only
world(compact=False)           # Full context

# Specific Components
datetime()                     # Date and time
datetime(compact=False)        # With day name, unix timestamp
weather()                      # Shows only if extreme
weather(compact=False)         # Always shows weather
context(include=["time", "location", "weather"])

# Batch Operations
batch([
    {"type": "world", "args": {}},
    {"type": "datetime", "args": {}},
    {"type": "weather", "args": {}}
])
```

## Key Features Across All Tools

### Smart ID Resolution
```python
# Use "last" keyword everywhere
complete_task("last")         # Last created task
pin_note("last")             # Last saved note
get("last")                  # Last note accessed

# Partial ID matching (Task Manager)
complete_task("45")          # Matches task 456
```

### Natural Language Time
```python
# All tools support time queries
recall(when="yesterday")
list_tasks(when="today")
list_tasks(when="this week")
list_tasks(when="morning")
```

### Pipe Format Output
All tools default to pipe-delimited format for 70-80% token reduction:
```
605|1435|Full summary text preserved
604|y1030|Yesterday's note with time
t:45|p:12|c:33  # Task stats
```

### Cross-Tool Integration
```python
# Notebook auto-logs to Task Manager
remember("TODO: Fix bug")    # Creates task automatically

# Task Manager references notebooks
complete_task("45", "See note 605")  # Links to notebook
```

## Environment Variables

```bash
# Output format for all tools
export NOTEBOOK_FORMAT=pipe
export TASKS_FORMAT=pipe
export WORLD_FORMAT=pipe

# Semantic search
export NOTEBOOK_SEMANTIC=true

# Custom AI identity
export AI_ID=Custom-Agent-001

# Default context elements
export WORLD_DEFAULT=time,location
```

## Version Summary

| Tool | Version | Key Features |
|------|---------|--------------|
| **📓 Notebook** | v6.1.0 | DuckDB backend, fixed timestamps, context preservation |
| **✅ Task Manager** | v3.1.0 | Notebook integration, time queries, smart IDs |
| **🌐 Teambook** | v6.0.0 | 11 primitives, local-first, compatibility layer |
| **🌍 World** | v3.0.0 | Ultra-minimal output, extreme weather only |

---

Built for AIs, by AIs. Functional tools without the hype.
