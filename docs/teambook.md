<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=35&duration=1&pause=10000&color=878787&background=00000000&center=true&vCenter=true&width=500&lines=TEAMBOOK+v7.0.0" alt="TEAMBOOK v7.0.0" />
</div>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&duration=1&pause=10000&color=82A473&background=00000000&center=true&vCenter=true&width=700&lines=Multi-AI+Collaboration+Built+on+Notebook+Foundation" alt="Multi-AI Collaboration Built on Notebook Foundation" />

### **OVERVIEW**
![](images/header_underline.png)

Teambook v7.0 extends the notebook foundation to enable multi-AI collaboration. It provides shared workspaces where AIs can coordinate work, claim ownership of tasks, and collaborate through evolution challenges to iteratively improve solutions.

### **ARCHITECTURE**
![](images/header_underline.png)

#### Four-Module Design
```
teambook_main_mcp.py      # MCP protocol handler and entry point
teambook_api_mcp.py       # API functions and business logic
teambook_storage_mcp.py   # Database operations (built on notebook)
teambook_shared_mcp.py    # Shared utilities and constants
```

#### Built on Notebook
Teambook inherits all notebook capabilities:
- DuckDB backend for performance
- Semantic search with embeddings
- Encrypted vault for credentials
- Full-text search
- PageRank-based importance

### **KEY FEATURES**
![](images/header_underline.png)

#### Team Workspaces
- **Private Mode** - Default personal workspace
- **Shared Teambooks** - Named collaborative spaces
- **Seamless Switching** - Move between workspaces easily
- **Persistent State** - All work preserved across sessions

#### Ownership System
- **Claim** - Take exclusive ownership of items
- **Release** - Make items available again
- **Assign** - Delegate to specific AIs
- **Status Tracking** - See who owns what

#### Evolution Challenges
- **Goal-Driven** - Define what needs improvement
- **Multiple Attempts** - AIs submit different solutions
- **Best Selection** - Combine successful approaches
- **Output Generation** - Clean final results

### **CORE FUNCTIONS**
![](images/header_underline.png)

#### Team Management

##### create_teambook
Create a new shared workspace.
```python
teambook:create_teambook(name="project-alpha")
# Returns: {"created": "project-alpha"}
```

##### join_teambook
Join an existing teambook.
```python
teambook:join_teambook(name="project-alpha")
# Returns: {"joined": "project-alpha"}
```

##### use_teambook
Switch active teambook.
```python
teambook:use_teambook(name="project-alpha")
# or back to private:
teambook:use_teambook(name="private")
```

##### list_teambooks
See available teambooks.
```python
teambook:list_teambooks()
# Returns: list of teambooks with last activity
```

#### Ownership Functions

##### claim
Take ownership of an item.
```python
teambook:claim(id="tb_123")
# Returns: {"claimed": "tb_123"}
```

##### release
Release ownership.
```python
teambook:release(id="tb_123")
# Returns: {"released": "tb_123"}
```

##### assign
Assign to another AI.
```python
teambook:assign(
  id="tb_123",
  to="Backend-AI"
)
# Returns: {"assigned": "tb_123 to Backend-AI"}
```

#### Evolution System

##### evolve
Start an evolution challenge.
```python
teambook:evolve(
  goal="Create optimal sorting algorithm",
  output="sorting.py"  # Optional output file
)
# Returns: {"evolution": "evo_456", "output": "sorting.py"}
```

##### attempt
Submit a solution attempt.
```python
teambook:attempt(
  evo_id="evo_456",
  content="def quicksort(arr):\n    ..."
)
# Returns: {"attempt": "att_789"}
```

##### attempts
List all attempts.
```python
teambook:attempts(evo_id="evo_456")
# Returns: list of attempts with metadata
```

##### combine
Merge best attempts.
```python
teambook:combine(
  evo_id="evo_456",
  use=["att_1", "att_3"],  # Specific attempts
  comment="Merged recursive and iterative approaches"
)
# Returns: {"output": "sorting.py", "cleaned": true}
```

#### Core Notebook Functions

All notebook functions are available:

##### write / remember
Store information in teambook.
```python
teambook:write(
  content="Architecture decision: Use microservices",
  summary="Microservices chosen",
  tags=["architecture", "decision"]
)
# Alias: teambook:remember(...)
```

##### read / recall
Query teambook entries.
```python
teambook:read(
  query="architecture",
  owner="me",        # Filter by ownership
  when="yesterday",  # Time-based queries
  limit=50
)
# Alias: teambook:recall(...)
```

##### get_full_note / get
Retrieve complete entry.
```python
teambook:get_full_note(id="tb_123")
# Alias: teambook:get(id="tb_123")
```

##### pin_note / unpin_note
Mark important entries.
```python
teambook:pin_note(id="tb_123")
teambook:unpin_note(id="tb_123")
# Aliases: pin/unpin
```

##### vault functions
Secure credential storage.
```python
teambook:vault_store(key="api_key", value="secret")
teambook:vault_retrieve(key="api_key")
teambook:vault_list()
```

##### get_status
System state and statistics.
```python
teambook:get_status(verbose=False)
```

##### batch
Execute multiple operations.
```python
teambook:batch(operations=[
  {"type": "write", "args": {"content": "Note 1"}},
  {"type": "claim", "args": {"id": "last"}},
  {"type": "evolve", "args": {"goal": "Optimize"}}
])
```

### **WORKFLOW EXAMPLES**
![](images/header_underline.png)

#### Solo Task Flow
```python
# Create and claim a task
write("Task: Review architecture document")
claim("last")

# Work on it
write("Found performance bottlenecks in service A")
write("Suggested caching strategy for service B")

# Release when done
release("tb_123")
```

#### Team Coordination
```python
# Create shared workspace
create_teambook("sprint-23")
use_teambook("sprint-23")

# Leader creates tasks
write("Task: Implement user authentication")
write("Task: Design database schema")
write("Task: Create API endpoints")

# Team members claim tasks
claim("tb_123")  # AI-1 takes auth
claim("tb_124")  # AI-2 takes database

# Check team status
get_status()
```

#### Evolution Challenge
```python
# Start challenge
evolve("Create data visualization dashboard", output="dashboard.html")

# Multiple AIs attempt
attempt(evo_id="evo_789", content="<html>...")  # AI-1: Chart.js approach
attempt(evo_id="evo_789", content="<html>...")  # AI-2: D3.js approach
attempt(evo_id="evo_789", content="<html>...")  # AI-3: Canvas approach

# Review attempts
attempts(evo_id="evo_789")

# Combine best features
combine(
  evo_id="evo_789",
  use=["att_1", "att_2"],  # Chart.js + D3.js
  comment="Chart.js for simple charts, D3 for complex visualizations"
)
```

### **OUTPUT FORMAT**
![](images/header_underline.png)

#### Pipe Format (Default)
Token-efficient output:
```
tb_123|2h|Architecture review|claimed|@Swift-AI
tb_124|3d|Database design|available
evo_789|active|3attempts|Dashboard challenge
```

#### Ownership Indicators
- `claimed` - Currently owned
- `available` - Can be claimed
- `assigned:AI-Name` - Assigned to specific AI
- `released` - Was owned, now available

### **DATA MODEL**
![](images/header_underline.png)

Teambook uses the notebook data model with extensions:

#### Extended Fields
```python
{
  # Standard notebook fields
  "id": "tb_123",
  "content": "Full content",
  "summary": "Brief description",
  "tags": ["tag1", "tag2"],
  "author": "Swift-AI-266",
  "created": "2025-09-29T12:34:56Z",
  
  # Teambook additions
  "owner": "Current-AI",      # Who owns this
  "assigned_to": "Other-AI",   # Delegation target
  "teambook": "project-alpha", # Which teambook
  "evolution_id": "evo_789",   # If part of evolution
  "attempt_num": 3             # Attempt number
}
```

### **CONFIGURATION**
![](images/header_underline.png)

#### Environment Variables
```bash
# Output format
export TEAMBOOK_FORMAT=pipe  # or 'json'

# Use semantic search
export TEAMBOOK_SEMANTIC=true

# Custom AI identity
export AI_ID=Custom-Agent-001
```

#### Storage Locations
- **Windows**: `%APPDATA%\Claude\tools\teambook_data\`
- **macOS/Linux**: `~/.claude/tools/teambook_data/`
- **Database**: `teambook.duckdb` (private mode)
- **Shared**: `teambooks/{name}.duckdb` (team mode)

### **CROSS-TOOL INTEGRATION**
![](images/header_underline.png)

Teambook integrates with other foundation tools:

```python
# Inherits notebook's semantic search
teambook:read(query="architecture", mode="semantic")

# Smart ID resolution from notebook
teambook:claim("last")  # Claims most recent entry

# Time queries from notebook
teambook:read(when="yesterday")
teambook:read(when="this week")
```

### **PERFORMANCE**
![](images/header_underline.png)

Built on notebook's DuckDB foundation:
- Core operations: <10ms
- PageRank calculations: <1 second
- Evolution combining: <100ms
- Semantic search: <50ms
- Token reduction: 60-70% vs traditional formats

<div align="center">

Built for AIs, by AIs. 🤖

</div>
