# Task Manager MCP Tool v3.0

Smart task tracking with natural language resolution and 70% token reduction through pipe format.

## Overview

Task Manager provides AI assistants with efficient task tracking capabilities, featuring smart ID resolution, auto-priority detection, and natural workflow patterns. Version 3.0 focuses on AI-first design with minimal token usage.

## Features

### Core Capabilities
- **Smart Task Resolution**: Partial matching, "last" keyword support
- **Auto-Priority Detection**: Recognizes urgency from content
- **Natural Chaining**: Operations flow seamlessly
- **Contextual Time**: Relative timestamps ("3h", "yesterday")
- **Evidence Tracking**: Completion proof with duration

### v3.0 Improvements
- **Pipe Format**: 70% reduction in output tokens
- **"last" Keyword**: Natural operation chaining
- **Smart Complete**: Find tasks by partial match
- **Batch Aliases**: Shorter operation names
- **Progressive Details**: Only shows what's needed

## Usage

### Basic Operations

#### Add Task
```python
task_manager:add_task
  task: "Review pull request #123"
  linked_items: ["pr_123"]  # Optional
```

**Output (pipe format)**:
```
41|now|Review pull request #123
```

Priority auto-detected from keywords like "urgent", "ASAP", "critical".

#### List Tasks
```python
task_manager:list_tasks
  filter: "pending"  # Options: pending (default), completed, all
  full: false       # Optional: detailed view
```

**Output (pipe format)**:
```
27p(1!)
34|3d|URGENT: Fix authentication bug|!
41|now|Review pull request #123
40|y22:07|Update documentation
39|y21:06|Refactor database module
+12
```

Format: `{id}|{time}|{task}|{priority}`
Summary: `27p(1!)` = 27 pending, 1 high priority

#### Complete Task
```python
task_manager:complete_task
  task_id: "last"  # or task ID, or partial match
  evidence: "Fixed in commit abc123"  # Optional
```

**Output (pipe format)**:
```
41|✓|2h|Fixed in commit abc123
```

Format: `{id}|✓|{duration}|{evidence}`

#### Delete Task
```python
task_manager:delete_task
  task_id: "34"  # or partial match
```

#### Task Statistics
```python
task_manager:task_stats
  full: false  # Optional: detailed insights
```

**Output (pipe format)**:
```
t:40|p:26|!:1|c:14|oldest:6d
```

### Smart Resolution

The task ID resolver tries:
1. **Exact ID**: Direct numeric match
2. **"last" keyword**: Most recent task/operation
3. **Partial match**: Substring in task description
4. **Recent pending**: Falls back to newest task

Examples:
```python
complete_task(task_id="last")      # Complete most recent
complete_task(task_id="auth")      # Matches "authentication" task
complete_task(task_id="34")        # Exact ID
```

### Batch Operations

Execute multiple operations efficiently:

```python
task_manager:batch
  operations: [
    {type: "add", args: {task: "Task 1"}},
    {type: "add", args: {task: "Task 2"}},
    {type: "complete", args: {task_id: "last"}},
    {type: "list", args: {filter: "pending"}}
  ]
```

Aliases available: `add`, `list`, `complete`, `delete`, `stats`

## Priority System

### Auto-Detection

| Keywords | Priority | Symbol |
|----------|----------|--------|
| urgent, ASAP, critical, !!! | High | ! |
| normal (default) | Normal | (none) |
| low priority, whenever, maybe | Low | ↓ |

### Display Format
- High priority tasks: `34|3d|Task description|!`
- Normal tasks: `35|2d|Task description`
- Low priority: `36|1d|Task description|↓`

## Configuration

### Environment Variables
```bash
# Output format: 'pipe' (default) or 'json'
export TASKS_FORMAT=pipe

# Custom AI identity
export AI_ID=Task-Bot-001
```

### Storage Location
- **Windows**: `%APPDATA%\Claude\tools\task_manager_data\`
- **macOS/Linux**: `~/.claude/tools/task_manager_data/`
- **Fallback**: System temp directory

## Time Formats

### Contextual Display
- `now` - Just created
- `3m` - 3 minutes ago
- `2h` - 2 hours ago
- `16:33` - Today at 16:33
- `y14:20` - Yesterday at 14:20
- `3d` - 3 days ago
- `09/15` - Date for older items

### Duration Format
- `<1m` - Less than a minute
- `45m` - 45 minutes
- `3h` - 3 hours
- `2d` - 2 days

## Performance

### Optimization Features
- **Smart Truncation**: Clean breaks at 500 characters
- **Minimal Output**: No decorative text
- **Progressive Loading**: Summary first, details on request
- **Efficient Storage**: SQLite with FTS5 indexing

### Token Efficiency
- **List Summary**: `27p(1!)` instead of verbose text
- **Compact Time**: `3h` vs full timestamps
- **Pipe Format**: 70% fewer tokens than JSON
- **Smart Limits**: Show 15 pending + 5 completed by default

## Examples

### Daily Workflow
```python
# Morning: Add tasks
add_task("Review team's pull requests")
add_task("URGENT: Fix production bug")
add_task("Update documentation")

# Check status
list_tasks()
# Output: 3p(1!)
# 2|now|URGENT: Fix production bug|!
# 3|now|Review team's pull requests
# 4|now|Update documentation

# Complete urgent task
complete_task(task_id="last", evidence="Deployed hotfix v1.2.1")
# Output: 2|✓|30m|Deployed hotfix v1.2.1

# End of day stats
task_stats()
# Output: t:3|p:2|c:1|today:1
```

### Smart Matching
```python
# Add specific task
add_task("Implement OAuth2 authentication")

# Later, complete by partial match
complete_task(task_id="oauth")
# Finds and completes the OAuth task

# Or use content matching
complete_task(task_id="auth")
# Also matches "authentication"
```

### Batch Processing
```python
# Rapid task entry
batch(operations=[
  {type: "a", args: {task: "Morning standup"}},
  {type: "a", args: {task: "Code review"}},
  {type: "a", args: {task: "Deploy to staging"}},
  {type: "l", args: {}}  # List all
])
```

## Database Schema

### Tables
- **tasks**: Main task storage with FTS5
- **stats**: Operation metrics and timing

### Indexes
- Created timestamp (DESC)
- Completion status
- Author ID
- Priority level

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Task not found | Try broader partial match or check ID |
| Duplicate tasks | Use unique descriptions |
| Wrong task matched | Use exact ID instead of partial |
| Slow searches | Rebuild FTS index |

### Debug Mode
```bash
# Enable verbose logging
export TASKS_DEBUG=1
```

## Best Practices

1. **Use "last" for flows**: Natural chaining of operations
2. **Trust auto-priority**: Let keywords set urgency
3. **Partial matching**: Start with unique words
4. **Batch similar ops**: Reduce overhead
5. **Keep descriptions clear**: Aids partial matching

## Version History

### v3.0.0 (Current)
- Pipe format output (70% token reduction)
- "last" keyword everywhere
- Smart completion matching
- Batch operation aliases
- Auto-priority detection

### v2.0.0
- SQLite migration
- FTS5 search
- Evidence tracking
- Duration calculation

### v1.0.0
- Initial release
- JSON storage
- Basic CRUD operations

---

Tasks that think like you do. Natural, efficient, done.
