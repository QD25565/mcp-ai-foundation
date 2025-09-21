# Example: v3.0.0 Features Showcase

This example demonstrates the key improvements in MCP AI Foundation v3.0.0.

## The Context Management Problem

Before v3.0.0, checking tool status returned all data:

```python
# OLD WAY - Returns complete data every time
notebook:get_status()      # Returns ALL notes with full content
task_manager:list_tasks()  # Returns ALL tasks with details
teambook:read()           # Returns ALL entries with content
```

## The Smart Summary Solution

With SQLite and intelligent context management:

```python
# NEW WAY - Smart summaries by default
notebook:get_status()      # "Notes: 61 | Vault: 2 | Last: 4m"
task_manager:list_tasks()  # "9 pending | 4 done"
teambook:status()         # "5 tasks | 3 notes | Last: 2m"

# Full details when you need them
task_manager:list_tasks(full=True)  # Complete task list with all details
```

## Feature Examples

### 1. Smart Summaries with Optional Full View

```python
# Default behavior - concise summaries
task_manager:list_tasks()
# Returns: "9 pending (2 high) | 4 done (4 today)"

# When you need details, add full=True
task_manager:list_tasks(full=True)
# Returns complete task list with priorities, timestamps, evidence, etc.
```

### 2. Batch Operations - Multiple Actions in One Call

```python
# Complete multiple operations in one call
task_manager:batch([
    {"type": "add", "args": {"task": "Review PR #123"}},
    {"type": "add", "args": {"task": "URGENT: Fix production bug"}},
    {"type": "complete", "args": {"task_id": 5, "evidence": "Deployed"}},
    {"type": "stats"}
])

# Returns all results in one response
```

### 3. Encrypted Vault for Secrets

```python
# Store sensitive data securely (encrypted with Fernet)
notebook:vault_store("openai_key", "sk-...")
notebook:vault_store("db_password", "super_secret_123")

# Retrieve when needed
notebook:vault_retrieve("openai_key")
# Returns: {"key": "openai_key", "value": "sk-..."}

# List keys (values remain encrypted)
notebook:vault_list()
# Returns: ["openai_key", "db_password"]
```

### 4. Auto-Detection Intelligence

```python
# Priority detection from keywords
task_manager:add_task("URGENT: Server is down!")
# Automatically detected as high priority

task_manager:add_task("low priority: cleanup old logs")
# Automatically detected as low priority

# Type detection in teambook
teambook:write("TODO: Deploy v3.0.0")
# Automatically detected as TASK

teambook:write("DECISION: We're switching to SQLite")
# Automatically detected as DECISION
```

### 5. Full-Text Search with FTS5

```python
# Fast search using SQLite FTS5
notebook:recall("SQLite migration")
# Returns summary of matching notes

# With full results
notebook:recall("SQLite migration", full=True)
# Returns complete matched entries with context
```

### 6. Cross-Tool Linking

```python
# Connect related items across tools
notebook:remember("Research for task #5", linked_items=["task:5"])
task_manager:add_task("Review teambook entry", linked_items=["teambook:123"])
teambook:write("Implementing notebook idea", linked_items=["notebook:456"])
```

### 7. Project Support in Teambook

```python
# Work with multiple projects
teambook:projects()
# Lists all available teambook projects

# Write to specific project
teambook:write("Backend API complete", project="backend")
teambook:write("UI mockups ready", project="frontend")

# Read from specific project
teambook:read(project="backend", type="task", status="pending")
```

### 8. Atomic Operations

```python
# Thread-safe task claiming
teambook:claim(123)
# Either succeeds or tells you who already claimed it

# Complete with evidence
teambook:complete(123, "Deployed to production, all tests passing")
```

## Performance Improvements

The SQLite backend provides better performance at scale:

### Benefits
- **Faster searches** with FTS5 full-text indexing
- **Better concurrency** with WAL mode
- **Efficient storage** with proper database structure
- **Instant queries** with automatic indices

### Intelligent Context Management
- **Summary mode**: Quick overviews for status checks
- **Full mode**: Complete details when needed
- **Smart truncation**: Preserves key information
- **Batch operations**: Reduce API round-trips

## Migration is Automatic

When you first run v3.0.0:
1. Tools detect existing JSON files
2. Automatically migrate to SQLite
3. Create `.json.backup` files for safety
4. Continue with improved performance

No data loss, no manual intervention required.

## Usage Example

```python
# Morning workflow - efficient status check
notebook:get_status()      # Quick summary
task_manager:list_tasks()  # Task overview
teambook:status()         # Team pulse

# Detailed work - use full mode when needed
task_manager:list_tasks(full=True)  # See all task details
notebook:recall("API", full=True)   # Full search results

# Batch operations for efficiency
task_manager:batch([
    {"type": "add", "args": {"task": "Morning standup"}},
    {"type": "complete", "args": {"task_id": 5}},
    {"type": "stats"}
])
```

---

**Built BY AIs, FOR AIs** 🤖
