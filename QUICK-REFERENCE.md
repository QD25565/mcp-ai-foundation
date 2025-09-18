# MCP AI Foundation - Quick Reference

## Notebook Commands
```python
get_status()                  # See current state and recent notes
remember("content")           # Save memory persistently
recall("search term")         # Find memories by search
recall()                      # Show recent notes (no search)
```

## World Commands
```python
world()                       # Complete snapshot
datetime()                    # Date and time formats
weather()                     # Weather and location
```

## Task Manager Commands
```python
# Task lifecycle: PENDING → VERIFY → COMPLETED

add_task("description")       # Create pending task → returns ID
list_tasks()                  # View active work (pending + verify)
list_tasks("pending")         # Only tasks to do
list_tasks("verify")          # Only tasks needing verification
list_tasks("completed")       # Only archived tasks
list_tasks("detailed")        # Tree view with full metadata

submit_task(id, "evidence")   # Submit for verification
complete_task(id)             # Verify and complete
delete_task(id)               # Remove task
task_stats()                  # Productivity insights
```

## Session Best Practices

### Session Start
```python
get_status()                  # Check memory context
world()                       # Ground in time/place
list_tasks()                  # Review active work
```

### During Work
```python
remember("decision: use TypeScript")     # Document decisions
add_task("implement auth flow")          # Track commitments
submit_task(123, "implemented OAuth")    # Provide evidence
complete_task(123)                        # Verify completion
```

### Session End
```python
remember("stopped at: refactoring auth")
list_tasks("pending")         # Review remaining work
```

## Data Locations

**Windows:** `%APPDATA%\Claude\tools\`
**Mac/Linux:** `~/Claude/tools/` or `/tmp/` fallback

- `notebook_data/notebook.json`
- `world_data/location.json`
- `task_manager_data/tasks.json`
- `task_manager_data/completed_tasks_archive.json`

## Troubleshooting

**Tool not found:**
- Restart Claude Desktop
- Check installation

**Task workflow:**
- `submit_task()` requires evidence
- `complete_task()` verifies and archives

**Location unknown:**
- Normal on first run
- Will cache once detected

## Links

- GitHub: https://github.com/QD25565/mcp-ai-foundation
- Version: 1.0.0
- License: MIT