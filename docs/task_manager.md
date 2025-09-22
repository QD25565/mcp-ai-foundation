# Task Manager MCP v2.0.0

Simple personal task tracking with 2-state workflow for self-management.

## Overview

Task Manager provides a lightweight personal task system optimized for AI workflows. It uses a simple PENDING → COMPLETED model with automatic priority detection.

## Key Features

- **2-State Simplicity** - Tasks are either pending or completed
- **Auto-Priority** - Detects urgency from keywords
- **Evidence Tracking** - Document completion details
- **Smart Summaries** - Token-efficient default output
- **Batch Operations** - Handle multiple tasks efficiently

## Usage

### Basic Commands

```python
# Add tasks
add_task("Review code changes")
add_task("URGENT: Fix production bug")  # Auto-detects high priority

# List tasks (summary by default)
list_tasks()  # "5 pending (2 high) | 23 done | today: 3"
list_tasks(full=True)  # Detailed list
list_tasks(filter="completed")

# Complete tasks
complete_task(task_id=5, evidence="Merged PR #123")

# Delete tasks
delete_task(task_id=5)

# Get statistics
task_stats()  # Summary stats
task_stats(full=True)  # Detailed insights
```

### Batch Operations

```python
batch(operations=[
    {"type": "add_task", "args": {"task": "Task 1"}},
    {"type": "add_task", "args": {"task": "Task 2"}},
    {"type": "complete_task", "args": {"task_id": 1}}
])
```

## Priority Detection

Automatic priority from keywords:
- **High (!)** - urgent, asap, critical, important, high priority
- **Low (↓)** - low priority, whenever, maybe, someday

## Output Format

### Summary Mode (Default)
```
5 pending (2 high) | 23 done | today: 3
```

### Full Mode
```
PENDING[5]:
[23]! Fix production bug @2h
[22]! Update documentation @5h
[21] Regular code review @1d
[20]↓ Refactor old module @3d

COMPLETED[23]:
[19]✓ Deploy hotfix - Fixed memory leak 15m(2h)
```

## Data Model

- **Tasks Table**: id, task, author, created, priority, completed_at, evidence
- **Stats Table**: Operation tracking for insights
- **FTS Index**: Full-text search on task descriptions

## Best Practices

1. **Clear Descriptions** - Be specific about what needs doing
2. **Use Evidence** - Document what was accomplished
3. **Regular Reviews** - Check pending tasks periodically
4. **Batch Similar Tasks** - Use batch operations for efficiency

## Storage Location

- Windows: `%APPDATA%/Claude/tools/task_manager_data/tasks.db`
- Linux/Mac: `~/Claude/tools/task_manager_data/tasks.db`

## Token Efficiency

- Summary shows only counts (95% reduction)
- Full mode limits to top tasks per priority
- Smart truncation preserves key information

## Statistics and Insights

Full stats mode provides:
- Personal completion metrics
- Priority distribution
- Activity trends (today, this week)
- Oldest pending task
- Completion rate percentage

## Migration

v2.0 automatically migrates from v1 JSON format:
- Converts JSON to SQLite database
- Preserves all task history
- Maintains task IDs