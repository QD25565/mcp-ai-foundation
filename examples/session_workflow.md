# Typical AI Session Workflow

## Session Start

Every session should begin with context establishment:

```python
# 1. Check memory state
get_status()
# "Welcome back! Resuming from note #234 (3 hours ago)"
# Recent notes:
# [234] Stopped at: implementing OAuth flow
# [233] Decision: Use NextAuth for authentication
# [232] User prefers dark mode UI

# 2. Ground in time and space
world()
# Thursday, September 18, 2025 at 10:30 AM
# Location: Melbourne, VIC, AU
# Weather: 22°C/72°F, Partly cloudy

# 3. Review commitments
list_tasks()
# PENDING (3 total):
#   High priority [1]:
#     [156] Fix critical auth bug
#   Normal priority [2]:
#     [157] Update API documentation
#     [158] Refactor user service
```

## During Work

### Documenting Decisions
```python
remember("Decided to use Redis for session storage")
remember("Rate limiting set to 100 requests per minute")
```

### Creating Tasks
```python
add_task("Implement Redis session storage")
# Created pending task [159] Norm

add_task("URGENT: Fix production memory leak")
# Created pending task [160] High (auto-detected priority)
```

### Completing Tasks
```python
# First submit with evidence
submit_task(156, "Fixed auth bug in PR #234, added tests")
# Submitted [156] for verification

# Then verify and archive
complete_task(156)
# Completed and archived [156]
```

### Searching Memory
```python
recall("Redis")
# [235] Decided to use Redis for session storage

recall("rate limit")
# [236] Rate limiting set to 100 requests per minute
```

## Session End

```python
# Save stopping point
remember("Stopped at: Redis configuration, need to set up clustering")

# Review remaining work
list_tasks("pending")
# PENDING (3 total):
#   High priority [1]:
#     [160] URGENT: Fix production memory leak
#   Normal priority [2]:
#     [157] Update API documentation
#     [159] Implement Redis session storage

# Quick stats check
task_stats()
# Pending: 3 | To verify: 0 | Completed: 1
# Completed 1 today
```

## Best Practices

### Memory Management
- Remember decisions and rationale
- Remember user preferences
- Remember stopping points
- Remember key information (URLs, credentials, etc.)

### Task Management
- Always provide evidence when submitting
- Use descriptive task names
- Let priority auto-detect from keywords
- Complete tasks promptly after verification

### Search Patterns
- Use specific keywords for better recall
- Search before making assumptions
- Check for existing decisions before proposing new ones

### Time Awareness
- Check world() when time-sensitive decisions needed
- Use datetime() for timestamp generation
- Reference weather() for location-aware features