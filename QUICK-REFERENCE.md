<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=35&duration=1&pause=10000&color=878787&background=00000000&center=true&vCenter=true&width=500&lines=QUICK REFERENCE" alt="QUICK REFERENCE" />
</div>
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&duration=1&pause=10000&color=82A473&background=00000000&center=true&vCenter=true&width=600&lines=MCP+AI+Foundation" alt="MCP AI Foundation" />
</div>

<div align="center">

[![Version](https://img.shields.io/badge/v6.1.0-82A473?style=flat-square&labelColor=878787)](https://github.com/QD25565/mcp-ai-foundation/releases)
[![Tools](https://img.shields.io/badge/4_Tools-82A473?style=flat-square&labelColor=878787)](#tools)
[![Performance](https://img.shields.io/badge/↓80%25_Tokens-82A473?style=flat-square&labelColor=878787)](#key-features)

</div>

**📓 NOTEBOOK v6.1.0**
![](images/header_underline.png)

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

**✅ TASK MANAGER v3.1.0**
![](images/header_underline.png)

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

**🌐 TEAMBOOK v6.0.0**
![](images/header_underline.png)

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

**🌍 WORLD v3.0.0**
![](images/header_underline.png)

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

**KEY FEATURES**
![](images/header_underline.png)

<div align="center">

![Smart IDs](https://img.shields.io/badge/Smart_IDs-878787?style=flat-square) ![Time Queries](https://img.shields.io/badge/Time_Queries-878787?style=flat-square) ![Pipe Format](https://img.shields.io/badge/Pipe_Format-878787?style=flat-square) ![Integration](https://img.shields.io/badge/Cross_Tool-878787?style=flat-square)

</div>

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

**ENVIRONMENT VARIABLES**
![](images/header_underline.png)

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

**VERSION SUMMARY**
![](images/header_underline.png)

<div align="center">

| Tool | Version | Key Features |
|------|---------|--------------|
| **📓 Notebook** | v6.1.0 | DuckDB backend, fixed timestamps, context preservation |
| **✅ Task Manager** | v3.1.0 | Notebook integration, time queries, smart IDs |
| **🌐 Teambook** | v6.0.0 | 11 primitives, local-first, compatibility layer |
| **🌍 World** | v3.0.0 | Ultra-minimal output, extreme weather only |

</div>

---

<div align="center">

**Built for AIs, by AIs** 🤖

[![GitHub](https://img.shields.io/badge/GitHub-QD25565-82A473?style=flat-square&labelColor=878787&logo=github)](https://github.com/QD25565)
[![Repository](https://img.shields.io/badge/Repository-mcp--ai--foundation-82A473?style=flat-square&labelColor=878787)](https://github.com/QD25565/mcp-ai-foundation)

</div>
