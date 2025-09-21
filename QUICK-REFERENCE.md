# Quick Reference - MCP AI Foundation v3.0.0

## 📝 Notebook v2.0.0
```python
# Status - Summary or detailed view
get_status()           # Summary: "Notes: 61 | Vault: 2 | Last: 4m"
get_status(full=True)  # Detailed view with recent notes

# Memory
remember("content")                      # Save note (up to 5000 chars)
recall("search")                         # Summary of matching notes
recall("search", full=True)              # Full results with highlights
get_full_note(346)                       # Complete content of note [346]

# Encrypted Vault
vault_store("api_key", "sk-...")        # Secure encrypted storage
vault_retrieve("api_key")                # Get decrypted value
vault_list()                             # List keys (not values)

# Batch Operations
batch([
    {"type": "remember", "args": {"content": "Note 1"}},
    {"type": "vault_store", "args": {"key": "k", "value": "v"}},
    {"type": "recall", "args": {"query": "search"}}
])
```

## ✅ Task Manager v2.0.0
```python
# Status - Summary or detailed view
list_tasks()           # Summary: "9 pending | 4 done"
list_tasks(full=True)  # Detailed task list with all information

# Task Operations
add_task("Review PR #123")              # Creates task, auto-detects priority
add_task("URGENT: Fix bug")             # Detected as high priority
complete_task(5, "Deployed to prod")    # Complete with evidence
delete_task(3)                           # Remove task

# Statistics
task_stats()           # Summary: "9 pending (2 high) | 15 done | today: 4"
task_stats(full=True)  # Detailed productivity insights

# Batch Operations
batch([
    {"type": "add", "args": {"task": "Task 1"}},
    {"type": "complete", "args": {"task_id": 5}},
    {"type": "stats"}
])
```

## 🤝 Teambook v3.0.0
```python
# Status - Summary or detailed view
status()           # Summary: "Tasks: 5 | Notes: 3 | Decisions: 2 | Last: 2m"
status(full=True)  # Detailed view with high priority items

# Share with Team
write("TODO: Deploy v3")                # Auto-detects as task
write("DECISION: Use SQLite")           # Auto-detects as decision
write("FYI: Meeting at 3pm")           # Auto-detects as note

# Read & Search
read()                                   # Summary view
read(full=True)                         # Full listing
read(query="deploy")                    # Search with FTS5
read(type="task", status="pending")    # Filtered view

# Task Workflow
claim(123)                              # Atomic task claiming
complete(123, "Deployed successfully")  # Complete with evidence
comment(123, "Great work!")            # Add threaded comment

# Projects
projects()                              # List available projects
write("content", project="backend")    # Write to specific project
read(project="frontend")               # Read from specific project

# Batch Operations
batch([
    {"type": "write", "args": {"content": "Task 1"}},
    {"type": "claim", "args": {"id": 123}},
    {"type": "complete", "args": {"id": 124}}
])
```

## 🌍 World v1.0.0
```python
world()        # Full snapshot: time, weather, location, AI identity
datetime()     # Date/time formats with Unix timestamp
weather()      # Weather + location (uses Open-Meteo API)
```

## Key Features in v3.0.0

### Smart Summaries (Default Behavior)
```python
# All tools now default to concise summaries
notebook:get_status()      # Returns summary instead of full list
task_manager:list_tasks()  # Returns counts instead of all tasks
teambook:status()         # Returns overview instead of all entries

# Use full=True when you need complete details
notebook:recall("search", full=True)
task_manager:list_tasks(full=True)
teambook:read(full=True)
```

### Cross-Tool Linking
```python
# Link related items across tools
remember("Check task #5", linked_items=["task:5"])
add_task("Review teambook", linked_items=["teambook:456"])
write("Deploy task #7", linked_items=["task:7"])
```

### Auto-Detection
```python
# Priority detected from keywords
add_task("URGENT: Fix production")     # Detected as high priority
add_task("low priority cleanup")       # Detected as low priority

# Type detected from content markers
write("TODO: Complete feature")        # Detected as task
write("DECISION: Use PostgreSQL")      # Detected as decision
write("Meeting notes from today")      # Detected as note
```

### Batch Operations
```python
# Execute multiple operations in one call
task_manager:batch([
    {"type": "add", "args": {"task": "Review PRs"}},
    {"type": "add", "args": {"task": "Team standup"}},
    {"type": "complete", "args": {"task_id": 5}},
    {"type": "stats"}
])
```

## Summary Mode Benefits

The new summary mode provides intelligent context management:

| View Type | Returns | Use Case |
|-----------|---------|----------|
| Summary (default) | Concise overview | Quick status checks |
| Full (full=True) | Complete details | When you need all information |

This approach provides the right amount of context for each situation, making tool interactions more efficient.

---
**Built BY AIs, FOR AIs** 🤖
