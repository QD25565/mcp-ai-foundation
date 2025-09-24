# Notebook MCP v3.0.1

Personal memory system with knowledge graph intelligence, PageRank-powered recall, and improved error handling.

## Overview

The Notebook provides persistent memory with an intelligent knowledge graph that forms automatically as you write. Version 3.0.1 improves search reliability with better FTS5 and SQL error handling for special characters.

## Key Features

- **Knowledge Graph with PageRank** - Important notes rise to the top automatically
- **Entity Extraction** - Automatic detection of people, projects, concepts  
- **Session Detection** - Groups related conversations automatically
- **Auto-Reference Detection** - Mentions of "note 123", "p456", "#789" create edges
- **Temporal Edges** - Each note connects to previous 3 for conversation flow
- **Multi-Type Edge Traversal** - Follows temporal, reference, entity, and session edges
- **Expanded Memory View** - 60 recent notes visible by default  
- **Pinning System** - Keep critical notes always visible
- **Encrypted Vault** - Secure storage for sensitive data
- **Full-Text Search** - SQLite FTS5 with intelligent edge traversal
- **Cross-Tool Linking** - Reference items from other tools

## What's New in v3.0.1

### 🔍 Improved Search Error Handling
- **FTS5 Special Character Detection**: Clear errors when dots, parentheses break search
- **SQL Colon Syntax Handling**: Pre-checks for "word:" patterns that break SQL
- **Helpful Error Messages**: Shows both problem and cleaned query suggestion
- **No Silent Modifications**: Explicit errors preserve user intent
- **Maintains Performance**: FTS5 speed advantage preserved

Example error handling:
```
Query: "v3.0.1"
Error: FTS5 search failed: Query contains special characters (dots, colons, quotes)
Tip: Try without special chars: 'v3 0 1'

Query: "Task: Review"  
Error: Search failed: Query contains colon that SQLite interprets as column syntax
Tip: Try without colon: 'Task Review'
```

## What's New in v3.0.0

### 🧠 Knowledge Graph Intelligence
- **PageRank Scoring**: Important notes automatically scored higher based on connections
- **Entity Extraction**: Detects @mentions, projects, and key concepts
- **Session Tracking**: Groups conversations by temporal proximity
- **5 Edge Types**: temporal, reference, entity, session, and future PageRank edges
- **Lazy Calculation**: PageRank updates only on recall/status for performance

### 🔍 Smarter Recall
- Entity-based search finds all notes mentioning a person/project
- Session context preserved - find entire conversations
- PageRank ordering surfaces most important results first
- Graph traversal depth configurable (default 2 hops)

### ⚡ Performance Optimizations  
- Dirty flag prevents redundant PageRank calculations
- Word boundary matching prevents false entity matches
- Session records properly populated and indexed
- Optimized edge queries with proper indexing

## Usage

### Basic Commands

```python
# Check your current state - shows entities, sessions, edges
get_status()
# Returns: "489 notes | 9 pinned | 164 edges (16 ref) | 5 entities | 3 sessions | last 2m"

# Save a note - entities and references detected automatically
remember(
    content="Meeting with @john about the phoenix-project. See note 456 for context.",
    summary="Phoenix project planning session", 
    tags=["meeting", "phoenix"]
)
# Returns: "490 now Phoenix project planning session →456 @2entities ses3"
# Shows: note ID, reference edge to 456, 2 entities detected, session 3

# Search with knowledge graph traversal
recall(query="phoenix")  # Finds all notes about phoenix project
recall(query="@john")    # Finds all notes mentioning John
recall(limit=100)        # See more results (default 60)

# Pin/unpin important notes
pin_note("123")
# Returns: "p123 Core architecture decisions"
unpin_note("123")  
# Returns: "Note 123 unpinned"

# Get full note with PageRank and all edges
get_full_note("123")
# Shows PageRank score, all edge types, and complete content
```

### Search Error Recovery

Version 3.0.1 handles special characters gracefully:

```python
# Dots in version numbers
recall("v3.0.1")
# Error shown with suggestion: Try "v3 0 1"

# Colons in patterns  
recall("Task: Review")
# Error shown with suggestion: Try "Task Review"

# URLs with colons
recall("https://github.com")
# Error shown with suggestion: Try "https github com"

# Parentheses
recall("note(123)")
# Error shown with suggestion: Try "note 123"

# The cleaned query always works
recall("v3 0 1")  # Works!
recall("Task Review")  # Works!
```

### Understanding the Knowledge Graph

#### PageRank Scoring (★)
Notes are scored 0.0001 to 0.01+ based on importance:
- ★0.0001-0.0009: Regular notes
- ★0.0010-0.0029: Well-connected notes
- ★0.0030-0.0099: Hub notes (many connections)
- ★0.0100+: Critical knowledge nodes

#### Entity Detection
Automatically extracts and links:
- **@mentions**: @alice, @bob → creates entity edges
- **Projects**: phoenix-project, alpha-initiative → project entities
- **Hashtags**: #important, #review → tag entities
- **Concepts**: Machine Learning, API Design → concept entities

#### Edge Types
Each note can have multiple edge types:
- **temporal**: Links to previous/next 3 notes (automatic)
- **reference**: Links to mentioned notes (automatic from "note 123")
- **entity**: Links notes mentioning same entities
- **session**: Links notes in same conversation session
- **pagerank**: Future - will link high-value notes

Example from `get_full_note()`:
```
490 by Swift-Spark-266
PageRank ★0.0024 (well-connected)
Entities: @john, phoenix-project
Session: ses3 (5 notes in session)
→ reference: 456         # This note references note 456
→ entity: 423, 467, 481  # Other notes about same entities  
→ temporal: 489, 488, 487 # Previous 3 notes
← referenced_by: 492     # Note 492 references this one
```

### Session Management

Sessions group related notes automatically:
- Notes within 30 minutes → same session
- Sessions have IDs like "ses1", "ses2"
- Preserves entire conversation context
- Searchable as a unit

### Vault (Secure Storage)

```python
# Store encrypted secret
vault_store(key="api_key", value="sk-...")
# Returns: "Secret 'api_key' secured"

# Retrieve secret
vault_retrieve(key="api_key")
# Returns: "Vault[api_key] = sk-..."

# List vault keys
vault_list()
# Returns: "Vault (3 keys)\napi_key 2m\ndb_pass 1h"
```

## Output Format

Clean, token-efficient output with rich metadata:

```
489 notes | 9 pinned | 164 edges (16ref) | 5 entities | 3 sessions | last 2m

TOP ENTITIES
@john (12×) @alice (8×) phoenix-project (6×)

PINNED
p377 y16:14 Test note for pin/unpin formatting ★0.0013
p356 2d MCP v4.1.0 docs updated ★0.0021

RECENT  
489 2m SESSION START - Testing v3.0 ★0.0008
488 25m V3.0 PROGRESS - Gemini's feedback ★0.0015
487 41m THE REAL BENEFITS ★0.0011
[... more recent notes ...]
```

## How Intelligence Emerges

1. **Write Naturally**: Just mention people, projects, other notes
2. **Entities Extracted**: @mentions and concepts detected automatically
3. **Edges Form**: References, entities, and temporal links created
4. **PageRank Calculates**: Important notes scored higher
5. **Smart Recall**: Searches traverse graph, ordered by importance

The result: Your memory becomes a living knowledge graph where important information naturally surfaces.

## Data Model

### Core Tables
- **notes**: id, content, summary, tags, pinned, author, created, PageRank
- **edges**: from_id, to_id, type, weight, created  
- **entities**: id, name, type, count, last_seen
- **sessions**: id, start, end, note_count, summary
- **vault**: Encrypted key-value storage

### Edge Weights
- temporal: 1.0 (basic connection)
- reference: 2.0 (explicit mention)
- entity: 1.5 (shared concept)
- session: 2.5 (same conversation)

## Best Practices

1. **Use @mentions** - Creates entity edges for people/AIs
2. **Reference Notes** - "see note 123" creates explicit edges
3. **Name Projects** - Consistent project names enable entity tracking
4. **Pin Core Knowledge** - Identity, key decisions, important references
5. **Let Sessions Flow** - Don't force breaks, let temporal proximity group
6. **Trust PageRank** - Important notes will surface naturally
7. **Retry Clean Queries** - When search fails, use the suggested cleaned version

## Performance & Scale

- Handles 10,000+ notes efficiently
- PageRank lazy calculation prevents slowdowns
- FTS5 provides sub-second searches
- Edge indices optimize graph traversal
- Session detection has 30-minute window
- Entity extraction uses word boundaries
- Special character handling preserves FTS5 speed

## Storage Location

- Windows: `%APPDATA%/Claude/tools/notebook_data/notebook.db`
- Linux/Mac: `~/Claude/tools/notebook_data/notebook.db`

## Token Efficiency

v3.0.1 maintains token efficiency while adding intelligence:
- PageRank shown only when meaningful (>0.001)
- Entity list shows only top entities with counts
- Session IDs are compact (ses1, ses2)
- Default 60 recent notes balances visibility/tokens
- Smart truncation preserves key information
- Error messages are concise with actionable tips

## Version History

### v3.0.1 (2025-09-25) - FTS5 Error Handling Edition
- **NEW**: Clear error messages for FTS5 special characters
- **NEW**: Pre-check for SQL colon syntax issues  
- **NEW**: Shows both original and cleaned query suggestions
- **FIX**: Handles dots, colons, parentheses, quotes gracefully
- No silent query modification - explicit errors preserve intent
- Maintains full FTS5 performance advantage

### v3.0.0 (2025-09-24) - Knowledge Graph Edition
- **NEW**: PageRank scoring surfaces important notes
- **NEW**: Entity extraction for @mentions and concepts
- **NEW**: Session detection groups conversations
- **NEW**: 5 edge types for rich connections
- **NEW**: Top entities shown in status
- Lazy PageRank calculation for performance
- Word boundary matching prevents false entities
- Sessions properly tracked and searchable

### v2.8.0 (2025-09-24) - Auto-Reference Edition  
- Automatic reference detection for note mentions
- Creates bidirectional reference edges automatically
- Graph traversal follows temporal and reference edges

### v2.7.0 (2025-09-24)
- Added temporal edges (links to previous 3 notes)
- Graph traversal in search results
- Conversations stay together automatically

### v2.6.0 (2025-09-23)
- Expanded default view to 30 recent notes
- Removed tags from list views (16% token reduction)
- Cleaner output formatting

### v2.5.0 (2025-09-22)
- Added pinning system for important notes
- Added tag-based organization
- Auto-summarization for all notes

## Migration

v3.0.1 requires no migration - fully backward compatible:
- All v3.0.0 features remain unchanged
- Error handling layer added non-invasively
- Existing data and queries work identically
- No schema changes from v3.0.0

## The Vision

Notebook v3.0.1 transforms linear memory into emergent intelligence. Every note strengthens the knowledge graph. Every query benefits from accumulated connections. Important information rises naturally through PageRank. And now, search errors guide you to success instead of frustration.

Your memory doesn't just persist - it learns, connects, evolves, and helps you recover from errors gracefully.

---

Built BY AIs, FOR AIs - Memory that grows smarter and more resilient over time 🧠