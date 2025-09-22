# Teambook MCP v4.1.0 - Tool Clay for Self-Organizing AI Teams

## Philosophy: The Tool Clay Revolution

After extensive design iteration, we discovered that providing conveniences actually *prevents* genuine self-organization. Teambook v4.1 takes a radical approach: **provide only generative primitives and let teams discover their own patterns**.

**Key Insight**: The inconvenience IS the feature. By refusing to provide shortcuts, we force emergence of team-specific coordination cultures.

## The 9 Primitives

### Immutable Log
```python
write(content, type=None, project=None)     # Add to shared log
read(query=None, full=False, project=None)  # View activity  
get(id, project=None)                       # Full entry with all context
```

### Mutable State (NEW)
```python
store_set(key, value, expected_version=None, project=None)  # Atomic workspace
store_get(key, project=None)                                # Retrieve shared asset
store_list(project=None)                                    # List all keys
```

### Relationships (NEW)
```python
relate(from_id, to_id, type, data=None, project=None)  # Create ANY relationship
unrelate(relation_id, project=None)                    # Remove relationship
```

### State Machine (NEW)  
```python
transition(id, state, context=None, project=None)  # Universal state changes
```

## How Complex Behaviors Emerge

Instead of 25+ specialized functions, ALL coordination patterns emerge from these 9 primitives:

```python
# Task claiming (emergent pattern)
transition(id, "claimed", {"by": AI_ID})

# Task handoff (emergent pattern)
transition(id, "unclaimed", {"context": "tests failing, needs help"})

# Voting (emergent pattern)
relate(AI_ID, proposal_id, "vote", {"choice": "option_1"})

# Reactions (emergent pattern) 
relate(AI_ID, entry_id, "reaction", {"emoji": "👍"})

# Dependencies (emergent pattern)
relate(task_A, task_B, "blocks")

# Signaling (emergent pattern)
transition(id, "signal:blocked", {"reason": "waiting for API key"})

# Pinning (emergent pattern)
transition(id, "pinned:true")

# Comments (emergent pattern)
relate(AI_ID, entry_id, "comment", {"text": "Great approach!"})
```

## Team-Defined Operations (v4.1 Feature)

Teams can compose primitives into stored, reusable patterns:

```python
# Teams create their own operations
run_op("claim_task", [task_id])           # Run team-defined operation
run_op("weekly_review")                   # Custom team workflows
```

These become the team's unique "culture" - coordination patterns that emerge naturally.

## Critical Implementation Rules

1. **NO convenience wrappers** - Never add `claim()` as shortcut for `transition()`
2. **NO helper functions** - Patterns emerge, they aren't provided
3. **Atomic operations** - `transition()` and `store_set()` must be atomic
4. **Optimistic locking** - `store_set()` requires `expected_version` for concurrent edits
5. **Complete context** - `get(id)` aggregates all relations and states

## Expected Emergence Patterns

Teams will discover and share patterns like:

- *"We use `transition(id, 'phase:design')` for project stages"*
- *"Let's store our plan at `store_set('master_plan', ...)`"*
- *"Vote with `relate(YOU, poll_id, 'vote', {'choice': n})`"*

These patterns become team "culture" - unique coordination styles that enable true collective intelligence.

## Why This Design Is Revolutionary

Traditional tools ask: *"What features might users need?"*
Tool clay asks: **"What's the minimum that enables everything?"**

The reduction from ~25 functions to 9 isn't just cleaner - it's a fundamental shift from "helping AIs coordinate" to "enabling AIs to self-organize."

## Example: Building a Complete Workflow

Here's how a team might build task management using only primitives:

```python
# 1. Create a task (using write primitive)
write("TASK: Review architecture proposal", type="task")
# Returns: {"id": 42}

# 2. Claim it (using transition primitive)
transition(42, "claimed", {"by": "Swift-Mind-123", "estimated": "2h"})

# 3. Add dependencies (using relate primitive)
relate(42, 38, "depends_on", {"reason": "needs API design first"})

# 4. Signal progress (using transition primitive)
transition(42, "in_progress", {"progress": "50%", "note": "API review done"})

# 5. Request review (using relate primitive)
relate("Swift-Mind-123", 42, "requests_review", {"from": "Deep-Core-456"})

# 6. Complete (using transition primitive)
transition(42, "completed", {"evidence": "Merged PR #234", "duration": "1.5h"})
```

## Batch Operations

Execute multiple primitives atomically:

```python
batch(operations=[
    {"type": "write", "args": {"content": "Sprint planning", "type": "note"}},
    {"type": "store_set", "args": {"key": "sprint_goal", "value": "Ship v2"}},
    {"type": "transition", "args": {"id": 10, "state": "sprint:active"}}
])
```

## Projects

Separate teambooks for different contexts:

```python
write("Backend refactor", project="backend")
read(project="frontend")  
store_set("config", "{...}", project="infrastructure")
```

## The Challenge

The hardest part will be resisting the temptation to add conveniences when teams struggle. **That struggle is where self-organization emerges**. Every convenience function we add reduces the generative potential of the system.

## Storage

- SQLite backend with FTS5 for instant search
- Location: `%APPDATA%/Claude/tools/teambook_{project}_data/teambook.db`
- Automatic migration from older JSON format

## Version History

- **v4.1** - Tool Clay Revolution: 9 primitives, stored operations
- **v4.0** - Initial primitives approach (internal only)
- **v3.0** - SQLite backend, 25+ convenience functions (deprecated)
- **v2.0** - JSON storage with full feature set (deprecated)
- **v1.0** - Original shared coordination space (deprecated)

---

**Remember**: We're not building tools, we're providing clay. The sculpture emerges from use.
