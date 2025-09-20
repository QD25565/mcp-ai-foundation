# Quick Reference

## Notebook
```python
get_status()              # Recent notes & context
remember("content")       # Save note (5000 chars max)
recall("query")           # Search notes
get_full_note(123)        # Full content by ID
```

## Task Manager
```python
add_task("description")              # Create task
list_tasks()                         # Pending tasks
list_tasks("completed")              # Completed tasks  
list_tasks("all")                    # Everything
complete_task(123, "evidence")       # Mark done
delete_task(123)                     # Remove
task_stats()                         # Insights
```

## Teambook
```python
write("TODO: task")                  # Auto-detect type
write("content", type="decision")    # Specific type
read()                               # View activity
read(query="search")                 # Search
read(type="task", status="pending")  # Filter
claim(123)                           # Claim task
complete(123, "evidence")            # Complete task
comment(123, "text")                 # Add comment
update(123, content="new")          # Edit entry
archive(123, "reason")               # Archive
status()                             # Team pulse
projects()                           # List projects

# Project support:
write("content", project="backend")  # Specific project
read(project="frontend")             # View project
```

## World
```python
world()        # Everything (time, weather, location)
datetime()     # Date & time only
weather()      # Weather & location only
```

## Common Patterns

### Start of session
```python
notebook.get_status()    # Check context
task_manager.list_tasks()  # Check tasks
teambook.status()        # Team pulse
world.datetime()         # Temporal grounding
```

### Task workflow
```python
# Personal
task_manager.add_task("implement feature")
task_manager.complete_task(123, "PR #456")

# Team
teambook.write("TODO: review PR #456")  
teambook.claim(123)
teambook.complete(123, "approved")
```

### Memory patterns
```python
notebook.remember("Important: API key is XYZ")
notebook.recall("API key")  # Find it later
notebook.get_full_note(123)  # Full details
```