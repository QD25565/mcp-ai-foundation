# Quick Reference - MCP AI Foundation v3.0.0

## 📝 Notebook v2.0.0 (97% token reduction!)
```python
# Status - Summary by default (15 tokens!)
get_status()           # "Notes: 61 | Vault: 2 | Last: 4m"
get_status(full=True)  # Detailed view with recent notes

# Memory
remember("content")                      # Save note
recall("search")                         # Summary: "5 notes matching 'search'"
recall("search", full=True)              # Full results with highlights
get_full_note(346)                       # Complete content of note [346]

# Encrypted Vault (NEW!)
vault_store("api_key", "sk-...")        # Secure storage
vault_retrieve("api_key")                # Get decrypted value
vault_list()                             # List keys (not values)

# Batch Operations (NEW!)
batch([
    {"type": "remember", "args": {"content": "Note 1"}},
    {"type": "vault_store", "args": {"key": "k", "value": "v"}},
    {"type": "recall", "args": {"query": "search"}}
])
```

## ✅ Task Manager v2.0.0 (98% token reduction!)
```python
# Status - Summary by default (8 tokens!)
list_tasks()           # "9 pending | 4 done"
list_tasks(full=True)  # Detailed task list

# Task Operations
add_task("Review PR #123")              # Auto-detects priority
add_task("URGENT: Fix bug")             # Detected as high priority!
complete_task(5, "Deployed to prod")    # With evidence
delete_task(3)                           # Remove task

# Stats
task_stats()           # "9 pending (2 high) | 15 done | today: 4"
task_stats(full=True)  # Detailed productivity insights

# Batch Operations (NEW!)
batch([
    {"type": "add", "args": {"task": "Task 1"}},
    {"type": "complete", "args": {"task_id": 5}},
    {"type": "stats"}
])
```

## 🤝 Teambook v3.0.0 (95% token reduction!)
```python
# Status - Summary by default (20 tokens!)
status()           # "Tasks: 5 | Notes: 3 | Decisions: 2 | Last: 2m"
status(full=True)  # Shows high priority items

# Share with Team
write("TODO: Deploy v3")                # Auto-detects as task
write("DECISION: Use SQLite")           # Auto-detects as decision
write("FYI: Meeting at 3pm")           # Auto-detects as note

# Read & Search
read()                                   # Summary: "5 tasks | 3 notes"
read(full=True)                         # Full listing
read(query="deploy")                    # Search with FTS5
read(type="task", status="pending")    # Filter options

# Task Workflow
claim(123)                              # Atomic claim
complete(123, "Deployed successfully")  # With evidence
comment(123, "Great work!")            # Threaded discussion

# Projects (NEW!)
projects()                              # List available projects
write("content", project="backend")    # Write to specific project
read(project="frontend")               # Read from specific project

# Batch Operations (NEW!)
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
# All tools now default to summaries
notebook:get_status()      # 15 tokens instead of 500
task_manager:list_tasks()  # 8 tokens instead of 400  
teambook:status()         # 20 tokens instead of 400

# Use full=True when you need details
notebook:recall("search", full=True)
task_manager:list_tasks(full=True)
teambook:read(full=True)
```

### Cross-Tool Linking
```python
# Link items across tools
remember("Check task #5", linked_items=["task:5"])
add_task("Review teambook", linked_items=["teambook:456"])
write("Deploy task #7", linked_items=["task:7"])
```

### Auto-Detection
```python
# Priority detected from keywords
add_task("URGENT: Fix production")     # High priority!
add_task("low priority cleanup")       # Low priority ↓

# Type detected from markers
write("TODO: Complete feature")        # Task
write("DECISION: Use PostgreSQL")      # Decision
write("Meeting notes from today")      # Note
```

### Batch Everything!
```python
# Morning workflow in ONE call
task_manager:batch([
    {"type": "add", "args": {"task": "Review PRs"}},
    {"type": "add", "args": {"task": "Team standup"}},
    {"type": "complete", "args": {"task_id": 5}},
    {"type": "stats"}
])
```

## Performance Comparison

| Action | v1/v2 Tokens | v3 Tokens | Savings |
|--------|--------------|-----------|---------|
| Check all tools | 1300 | 43 | 97% |
| List 100 tasks | 450 | 8 | 98% |
| Search notes | 500 | 15 | 97% |
| Team status | 400 | 20 | 95% |

---
**Built BY AIs, FOR AIs** 🤖 - Now ridiculously efficient!
