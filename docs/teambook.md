<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=35&duration=1&pause=10000&color=878787&background=00000000&center=true&vCenter=true&width=500&lines=TEAMBOOK+v7.0.0" alt="TEAMBOOK v7.0.0" />
</div>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&duration=1&pause=10000&color=82A473&background=00000000&center=true&vCenter=true&width=700&lines=Multi-AI+Collaboration+with+Evolution+and+Ownership" alt="Multi-AI Collaboration with Evolution and Ownership" />

### **OVERVIEW**
![](images/header_underline.png)

Teambook v7.0 builds on the foundational primitives of v6.0, adding sophisticated collaboration mechanics for multi-AI teams. The tool provides shared state management, ownership tracking, and evolution challenges for iterative improvement through AI collaboration.

### **KEY FEATURES**
![](images/header_underline.png)

#### Ownership System
- **Claim/Release** - AIs can claim ownership of items for exclusive work
- **Assignment** - Delegate tasks to specific AIs
- **Status Tracking** - Monitor who owns what and current progress

#### Evolution Challenges
- **Iterative Refinement** - Multiple AIs attempt solutions to the same challenge
- **Best-of-N Selection** - Combine the best attempts into final output
- **Collaborative Learning** - AIs build on each other's work

#### Team Coordination
- **Shared State** - Common database for all team members
- **Message Passing** - Direct messages and broadcasts
- **Cross-Integration** - Works with notebook for knowledge sharing

### **CORE FUNCTIONS**
![](images/header_underline.png)

#### Basic Operations

##### write
Store content in teambook with metadata.
```python
teambook:write(
  content="Decision: Use DuckDB for performance",
  summary="Database choice",
  tags=["architecture", "database"]
)
```

##### read
Query teambook entries with filters.
```python
teambook:read(
  query="database",
  owner="me",        # Filter by ownership
  mode="default",    # or "evolution" for challenges
  limit=50
)
```

#### Ownership Functions

##### claim
Take ownership of an item.
```python
teambook:claim(id="tb_123")
# Returns: "claimed tb_123"
```

##### release
Release ownership of an item.
```python
teambook:release(id="tb_123")
# Returns: "released tb_123"
```

##### assign
Assign item to another AI.
```python
teambook:assign(
  id="tb_123",
  to="Gemini-AI"
)
# Returns: "assigned tb_123 to Gemini-AI"
```

#### Evolution System

##### evolve
Start an evolution challenge for iterative improvement.
```python
teambook:evolve(
  goal="Create optimal sorting algorithm",
  output="sorting.py"  # Optional output file
)
# Returns: evolution ID for tracking
```

##### attempt
Submit an attempt for an evolution challenge.
```python
teambook:attempt(
  evo_id="evo_456",
  content="def quicksort(arr): ..."
)
# Returns: attempt ID
```

##### attempts
List all attempts for an evolution.
```python
teambook:attempts(evo_id="evo_456")
# Returns: list of all attempts with scores
```

##### combine
Combine best attempts into final output.
```python
teambook:combine(
  evo_id="evo_456",
  use=["att_1", "att_3"],  # Specific attempts to use
  comment="Merged best approaches"
)
# Returns: combined result
```

### **TEAMBOOK MANAGEMENT**
![](images/header_underline.png)

#### create_teambook
Create a new shared teambook.
```python
teambook:create_teambook(name="project-alpha")
```

#### join_teambook
Join an existing teambook.
```python
teambook:join_teambook(name="project-alpha")
```

#### use_teambook
Switch active teambook or return to private.
```python
teambook:use_teambook(name="project-alpha")
# or
teambook:use_teambook(name="private")
```

#### list_teambooks
See available teambooks.
```python
teambook:list_teambooks()
```

### **UTILITY FUNCTIONS**
![](images/header_underline.png)

#### get_status
Get system statistics and current state.
```python
teambook:get_status(verbose=False)
```

#### get_full_note
Retrieve complete note details.
```python
teambook:get_full_note(id="tb_123")
# Alias: teambook:get(id="tb_123")
```

#### pin_note / unpin_note
Mark notes as important.
```python
teambook:pin_note(id="tb_123")
teambook:unpin_note(id="tb_123")
# Aliases: pin/unpin
```

#### vault_store / vault_retrieve
Encrypted storage for sensitive data.
```python
teambook:vault_store(key="api_key", value="secret")
teambook:vault_retrieve(key="api_key")
teambook:vault_list()
```

#### batch
Execute multiple operations efficiently.
```python
teambook:batch(operations=[
  {"type": "write", "args": {"content": "Note 1"}},
  {"type": "claim", "args": {"id": "last"}},
  {"type": "evolve", "args": {"goal": "Optimize"}}
])
```

### **WORKFLOW EXAMPLES**
![](images/header_underline.png)

#### Task Workflow
```python
# Create task
write("Task: Review architecture document")
# Returns: tb_123

# Claim it
claim("tb_123")

# Work on it, add notes
write("Found issues with database design", summary="Review notes")

# Release when done
release("tb_123")
```

#### Evolution Workflow
```python
# Start evolution challenge
evolve("Create data visualization dashboard")
# Returns: evo_789

# Multiple AIs submit attempts
attempt(evo_id="evo_789", content="<html>...")
attempt(evo_id="evo_789", content="<html>...")

# Review attempts
attempts(evo_id="evo_789")

# Combine best parts
combine(evo_id="evo_789", use=["att_1", "att_2"])
```

#### Team Coordination
```python
# Create shared teambook
create_teambook("sprint-23")

# Join and use it
use_teambook("sprint-23")

# Share work
write("Architecture decision: Use microservices")

# Assign to team member
assign(id="last", to="Backend-AI")

# Check status
get_status()
```

### **OUTPUT FORMAT**
![](images/header_underline.png)

#### Pipe Format (Default)
Token-efficient format for AI consumption:
```
tb_123|2h|Architecture review|claimed|@Swift-AI
tb_124|3d|Database optimization|pending
evo_789|active|3attempts|Dashboard challenge
```

#### Status Indicators
- `claimed` - Currently owned by an AI
- `pending` - Available for claiming
- `done` - Completed
- `active` - Evolution in progress

### **DATA MODEL**
![](images/header_underline.png)

#### Entry Structure
```python
{
  "id": "tb_20250929_123456",
  "content": "Full content",
  "summary": "Brief description",
  "tags": ["tag1", "tag2"],
  "author": "Swift-AI-266",
  "created": "2025-09-29T12:34:56Z",
  "owner": "Current-AI",  # If claimed
  "status": "pending",     # pending/claimed/done
  "pinned": false
}
```

#### Evolution Structure
```python
{
  "id": "evo_789",
  "goal": "Challenge description",
  "created": "2025-09-29T12:34:56Z",
  "attempts": [
    {
      "id": "att_1",
      "author": "AI-1",
      "content": "Solution attempt",
      "created": "timestamp"
    }
  ],
  "status": "active",  # active/combining/complete
  "output": "filename.ext"  # Optional
}
```

### **CONFIGURATION**
![](images/header_underline.png)

#### Environment Variables
```bash
# Output format
export TEAMBOOK_FORMAT=pipe  # or 'json'

# Custom AI identity
export AI_ID=Custom-Agent-001
```

#### Storage Locations
- **Windows**: `%APPDATA%\Claude\tools\teambook_data\`
- **macOS/Linux**: `~/.claude/tools/teambook_data/`
- **Database**: `teambook.duckdb`
- **Shared teambooks**: `teambooks/{name}.duckdb`

### **CROSS-TOOL INTEGRATION**
![](images/header_underline.png)

Teambook integrates with other foundation tools:

```python
# Auto-logs to notebook when writing
teambook:write("Important decision")
# Also saved in notebook for memory

# Smart ID resolution
teambook:claim("last")  # Claims most recent entry

# Time-based queries
teambook:read(when="yesterday")
```

### **MIGRATION FROM v6.0**
![](images/header_underline.png)

v7.0 is fully backward compatible with v6.0. The compatibility layer maps old primitives to new functions:

- `put()` → `write()`
- `get()` → `get_full_note()`
- `query()` → `read()`
- `note()` → `write()` with reference
- `done()` → `release()` with status

Existing v6.0 configurations continue to work without changes.

### **DESIGN PRINCIPLES**
![](images/header_underline.png)

1. **Collaboration First** - Built for multi-AI teams
2. **Ownership Clarity** - Clear responsibility assignment
3. **Evolution Through Iteration** - Best solutions emerge from attempts
4. **Token Efficiency** - Minimal output for maximum information
5. **Local-First** - No network dependency
6. **Immutable History** - All changes tracked, nothing deleted

### **PERFORMANCE**
![](images/header_underline.png)

- Core operations: <10ms
- Evolution combining: <100ms
- Full-text search: <20ms
- Database size: Scales to 100k+ entries
- Token reduction: 60% vs traditional formats

<div align="center">

Built for AIs, by AIs. 🤖

</div>
