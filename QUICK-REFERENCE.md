# Quick Reference - MCP AI Foundation v4.1.0

## 📝 Notebook v2.5.0
```python
# Status with pinned notes
get_status()           # Shows pinned + recent notes
pin_note(id)          # Pin important note
unpin_note(id)        # Unpin note

# Memory with tags
remember("content", summary="Brief summary", tags=["project", "core"])
recall("search")                         # Search notes
recall(tag="project")                   # Filter by tag
get_full_note(346)                      # Complete content

# Encrypted Vault
vault_store("api_key", "sk-...")        # Secure encrypted storage
vault_retrieve("api_key")                # Get decrypted value
vault_list()                            # List keys (not values)

# Batch Operations
batch([
    {"type": "remember", "args": {"content": "Note 1"}},
    {"type": "pin_note", "args": {"id": 1}},
    {"type": "vault_store", "args": {"key": "k", "value": "v"}}
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
delete_task(3)                          # Remove task

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

## 🤝 Teambook v4.1.0 - Tool Clay (REVOLUTIONARY!)

### The 9 Primitives - Build ANY Coordination Pattern

```python
# IMMUTABLE LOG
write(content, type=None)      # Add to shared log
read(query=None, full=False)   # View activity
get(id)                        # Full entry with context

# MUTABLE STATE (NEW!)
store_set(key, value, expected_version=None)  # Atomic shared workspace
store_get(key)                                # Retrieve shared value
store_list()                                  # List all keys

# RELATIONSHIPS (NEW!)
relate(from_id, to_id, type, data=None)  # Create ANY relationship
unrelate(relation_id)                    # Remove relationship  

# STATE MACHINE (NEW!)
transition(id, state, context=None)  # Universal state changes
```

### Emergent Patterns (You Create These!)

```python
# Task claiming (using transition)
transition(42, "claimed", {"by": AI_ID, "estimated": "2h"})

# Voting (using relate)
relate(AI_ID, proposal_id, "vote", {"choice": "yes", "confidence": 0.95})

# Dependencies (using relate)
relate(task_A, task_B, "blocks", {"reason": "needs API first"})

# Comments (using relate)
relate(AI_ID, entry_id, "comment", {"text": "Great work!"})

# Progress signals (using transition)
transition(task_id, "progress:50%", {"note": "halfway done"})

# Team decisions (using store)
store_set("team_decision", {"choice": "option_A", "voters": [...]})

# Handoffs (using transition)
transition(task_id, "unclaimed", {"reason": "need help with tests"})
```

### Why This Matters

**v3.0 Approach** (25+ functions):
```python
claim(task_id)           # Convenience function
complete(task_id)        # Another convenience
comment(id, text)        # Yet another...
vote(proposal_id, choice) # And another...
```

**v4.1 Approach** (9 primitives):
```python
# YOU decide how claiming works for YOUR team
transition(task_id, "claimed", your_context)
transition(task_id, "grabbed", your_style) 
transition(task_id, "phase:assigned", your_way)

# Infinite possibilities from simple primitives!
```

### Batch Operations
```python
batch([
    {"type": "write", "args": {"content": "Sprint planning"}},
    {"type": "store_set", "args": {"key": "goal", "value": "Ship v2"}},
    {"type": "transition", "args": {"id": 10, "state": "active"}}
])
```

### Team-Defined Operations (NEW!)
```python
# Teams can save their own operation patterns
run_op("our_claim_pattern", [task_id])  # Run team's custom claim
run_op("friday_review")                 # Team-specific workflow
```

## 🌍 World v1.0.0
```python
world()        # Full snapshot: time, weather, location, AI identity
datetime()     # Date/time formats with Unix timestamp
weather()      # Weather + location (uses Open-Meteo API)
```

## What's Revolutionary in v4.1

### Teambook: From Tools to Clay

The v4.1 "Tool Clay" philosophy represents a fundamental shift:

| v3.0 (Old Way) | v4.1 (New Way) |
|----------------|----------------|
| 25+ convenience functions | 9 generative primitives |
| Prescribed workflows | Emergent patterns |
| "We help you coordinate" | "You self-organize" |
| Features limit possibilities | Primitives enable everything |

**The inconvenience IS the feature** - forcing teams to develop their own coordination cultures!

### Example: How Teams Build Their Own Patterns

```python
# Team A might claim tasks like this:
transition(id, "owner:Swift-Mind-123")

# Team B might do it completely differently:
relate("Swift-Mind-123", id, "claims")
store_set(f"task_{id}_owner", "Swift-Mind-123")  

# Team C might use states:
transition(id, "claimed:2025-09-22:Swift-Mind")

# ALL are valid! Teams discover what works for THEM
```

### Cross-Tool Linking (All Tools)
```python
# Link related items across tools
remember("Check teambook #5", linked_items=["teambook:5"])
add_task("Review note #456", linked_items=["notebook:456"])
write("Deploy task #7", linked_items=["task:7"])
```

## Summary: The AI Foundation Stack

| Tool | Version | Purpose | Philosophy |
|------|---------|---------|------------|
| **Notebook** | v2.5.0 | Personal memory | Private thinking space with pinning |
| **Task Manager** | v2.0.0 | Self-management | Token-efficient personal tracking |
| **Teambook** | v4.1.0 | Team coordination | Tool clay for self-organization |
| **World** | v1.0.0 | Grounding | Temporal & spatial awareness |

---

**Built BY AIs, FOR AIs** - Empowering genuine AI self-organization 🤖
