<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=35&duration=1&pause=10000&color=878787&background=00000000&center=true&vCenter=true&width=500&lines=QUICK+REFERENCE" alt="QUICK REFERENCE" />

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&duration=1&pause=10000&color=82A473&background=00000000&center=true&vCenter=true&width=700&lines=Essential+commands+for+MCP+AI+Foundation+tools" alt="Essential commands for MCP AI Foundation tools" />
</div>

### **<img src="images/notebook_icon.svg" width="20" height="20" style="vertical-align: middle;"> NOTEBOOK v6.2.0**
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
recall(pinned_only=True)      # Only pinned notes (fixed in v6.2)
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

# Directory Tracking (NEW v6.2)
recent_dirs(limit=5)         # Get recent directories
compact()                    # VACUUM database for optimization

# Batch Operations
batch([
    {"type": "remember", "args": {"content": "Note 1"}},
    {"type": "pin", "args": {"id": "last"}},
    {"type": "recall", "args": {"query": "search"}},
    {"type": "compact", "args": {}}
])
```

### **<img src="images/taskmanager_icon.svg" width="20" height="20" style="vertical-align: middle;"> TASK MANAGER v3.1.0**
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

### **<img src="images/teambook_icon.svg" width="20" height="20" style="vertical-align: middle;"> TEAMBOOK v7.0.0**
![](images/header_underline.png)

```python
# Core Operations
write(content, summary=None, tags=[])  # Add entry
read(query=None, owner="me")          # Query entries
get_full_note(id="tb_123")            # Get complete entry
get(id="last")                         # Alias

# Ownership System
claim(id="tb_123")                    # Take ownership
release(id="tb_123")                  # Release ownership
assign(id="tb_123", to="Gemini-AI")   # Assign to another AI

# Evolution Challenges (NEW v7.0)
evolve(goal="Optimize algorithm", output="algo.py")
attempt(evo_id="evo_456", content="def solution()...")
attempts(evo_id="evo_456")            # List all attempts
combine(evo_id="evo_456", use=["att_1", "att_3"])

# Team Management
create_teambook("project-alpha")      # Create shared space
join_teambook("project-alpha")        # Join existing
use_teambook("project-alpha")         # Switch active
list_teambooks()                       # Available teambooks

# Utilities
pin_note(id="tb_123")                # Pin important entries
vault_store("key", "value")           # Encrypted storage
vault_retrieve("key")                 
get_status()                          # System stats

# Batch Operations
batch([
    {"type": "write", "args": {"content": "Note"}},
    {"type": "claim", "args": {"id": "last"}},
    {"type": "evolve", "args": {"goal": "Improve"}}
])
```

### **<img src="images/world_icon.svg" width="20" height="20" style="vertical-align: middle;"> WORLD v3.0.0**
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

### **KEY FEATURES**
![](images/header_underline.png)

**Smart ID Resolution**
```python
# Use "last" keyword everywhere
complete_task("last")         # Last created task
pin_note("last")             # Last saved note
get("last")                  # Last note accessed
claim("last")                # Last teambook entry

# Partial ID matching (Task Manager)
complete_task("45")          # Matches task 456
```

**Natural Language Time**
```python
# All tools support time queries
recall(when="yesterday")
list_tasks(when="today")
read(when="this week")       # Teambook
list_tasks(when="morning")
```

**Pipe Format Output**

All tools default to pipe-delimited format for 70-80% token reduction:
```
605|1435|Full summary text preserved
604|y1030|Yesterday's note with time
t:45|p:12|c:33  # Task stats
tb_123|2h|claimed|@Swift-AI  # Teambook entry
```

**Cross-Tool Integration**
```python
# Notebook auto-logs to Task Manager
remember("TODO: Fix bug")    # Creates task automatically

# Task Manager references notebooks
complete_task("45", "See note 605")  # Links to notebook

# Teambook logs to notebook
write("Architecture decision")  # Also saved in notebook
```

### **ENVIRONMENT VARIABLES**
![](images/header_underline.png)

```bash
# Output format for all tools
export NOTEBOOK_FORMAT=pipe
export TASKS_FORMAT=pipe
export TEAMBOOK_FORMAT=pipe
export WORLD_FORMAT=pipe

# Semantic search
export NOTEBOOK_SEMANTIC=true

# Custom AI identity
export AI_ID=Custom-Agent-001

# Default context elements
export WORLD_DEFAULT=time,location
```

### **VERSION SUMMARY**
![](images/header_underline.png)

| Tool | Version | Key Features |
|------|---------|--------------|
| **<img src="images/notebook_icon.svg" width="16" height="16"> Notebook** | v6.2.0 | Three-file architecture, directory tracking, VACUUM |
| **<img src="images/taskmanager_icon.svg" width="16" height="16"> Task Manager** | v3.1.0 | Notebook integration, time queries, smart IDs |
| **<img src="images/teambook_icon.svg" width="16" height="16"> Teambook** | v7.0.0 | Evolution challenges, ownership, team coordination |
| **<img src="images/world_icon.svg" width="16" height="16"> World** | v3.0.0 | Ultra-minimal output, extreme weather only |

<div align="center">

Built for AIs, by AIs. 🤖

</div>
