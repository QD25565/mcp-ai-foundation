# AI Usage Guide

## Getting Started

When you have these tools available, start your session with:

```python
# Check your memory context
notebook.get_status()

# Check pending tasks
task_manager.list_tasks()

# Check team status (if working with team)
teambook.status()

# Get temporal grounding
world.datetime()
```

## Memory Management

### Saving Important Information
```python
# Save key details
notebook.remember("User prefers dark mode UIs")
notebook.remember("Project uses Python 3.11")
notebook.remember("API endpoint: https://api.example.com/v2")

# Search later
notebook.recall("API")  # Find API details
notebook.recall("Python")  # Find Python version

# Get full content when needed
notebook.get_full_note(123)  # Complete note #123
```

## Task Tracking

### Personal Tasks
```python
# Create tasks
task_manager.add_task("Review PR #456")
task_manager.add_task("Update documentation")

# Complete with evidence
task_manager.complete_task(1, "Merged PR #456")

# Check productivity
task_manager.task_stats()
```

### Team Tasks
```python
# Share work
teambook.write("TODO: Deploy to staging")
teambook.write("DECISION: Use PostgreSQL for main database")

# Claim and complete
teambook.claim(123)
teambook.complete(123, "Deployed to staging.example.com")

# Collaborate
teambook.comment(123, "Should we include migrations?")
```

## Project Management

Teambook supports multiple projects:

```python
# Default project
teambook.write("TODO: Fix login bug")

# Specific projects
teambook.write("TODO: Update API docs", project="backend")
teambook.write("TODO: Fix responsive layout", project="frontend")

# View by project
teambook.read(project="backend")
teambook.status(project="frontend")

# List all projects
teambook.projects()
```

## Best Practices

### 1. Start with Context
Always begin by checking `get_status()` to understand previous context.

### 2. Use Full Content Wisely
The preview from `recall()` is often enough. Only use `get_full_note()` when you need complete details.

### 3. Track Important Decisions
```python
teambook.write("DECISION: Chose React over Vue for frontend")
```

### 4. Complete Tasks with Evidence
```python
task_manager.complete_task(123, "Fixed in commit abc123")
teambook.complete(456, "Deployed to prod")
```

### 5. Use Projects for Organization
```python
# Set default project via environment
export TEAMBOOK_PROJECT=backend

# Or specify per call
teambook.write("TODO: task", project="frontend")
```

## Identity Persistence

Each AI maintains a unique identity across sessions (e.g., `Swift-Mind-782`). This identity:
- Persists across restarts
- Tracks who created/completed tasks
- Shows in team collaboration
- Helps maintain accountability

## Troubleshooting

### Tools Not Appearing
1. Completely restart Claude Desktop
2. Check system tray - ensure Claude is fully closed
3. Verify config paths are correct

### Can't Find Old Notes
```python
# Search more broadly
notebook.recall()  # Shows recent notes

# Check specific IDs
notebook.get_full_note(123)
```

### Task Already Claimed
```python
# Check who claimed it
teambook.get(123)  # Shows full details including claimer
```