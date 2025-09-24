# Changelog

All notable changes to MCP AI Foundation will be documented in this file.

## [3.0.1] - 2025-09-25

### Improved: Notebook v3.0.1 - FTS5 Error Handling Edition

Enhanced search reliability with clear error messages for special characters.

### Added
- **FTS5 Special Character Detection**: Clear errors when dots, parentheses, quotes break FTS5 parsing
- **SQL Colon Syntax Handling**: Pre-checks for "word:" patterns that SQLite interprets as column references
- **Helpful Error Messages**: Shows both original query and cleaned suggestion
- **Comprehensive Character Handling**: Dots, colons, parentheses, quotes, brackets all handled gracefully

### Technical Details
- Added `clean_fts5_query()` function to remove problematic characters
- Enhanced `recall()` with try-catch for `sqlite3.OperationalError`
- Pre-check for colon patterns before SQL execution
- No silent query modification - explicit errors preserve user intent
- Maintains full FTS5 performance advantage (100x speed over LIKE queries)

### Example Error Handling
```
Query: "v3.0.1"
Error: FTS5 search failed: Query contains special characters (dots, colons, quotes)
Tip: Try without special chars: 'v3 0 1'

Query: "Task: Review"
Error: Search failed: Query contains colon that SQLite interprets as column syntax
Tip: Try without colon: 'Task Review'
```

### Philosophy
- **Explicit > Implicit**: Clear errors instead of silent modifications
- **Performance First**: Preserve FTS5 speed advantage
- **AI-First Design**: Error messages guide AIs to successful retries
- **Token Efficient**: Concise, actionable error messages

## [3.0.0] - 2025-09-24

### Revolutionary: Notebook v3.0.0 - Knowledge Graph Intelligence

Transform linear memory into emergent intelligence with PageRank scoring, entity extraction, and session detection.

### Added
- **Notebook v3.0.0 - Knowledge Graph Edition**:
  - **PageRank Scoring**: Important notes automatically scored higher (★0.0001 to ★0.01+)
  - **Entity Extraction**: Automatic detection of @mentions, projects, concepts
  - **Session Detection**: Groups related conversations by temporal proximity
  - **5 Edge Types**: temporal, reference, entity, session, and future PageRank edges
  - **Top Entities Display**: Shows most mentioned entities with occurrence counts
  - **Lazy PageRank Calculation**: Updates only on recall/status for performance
  - **Word Boundary Matching**: Prevents false entity matches (e.g., "manual" != "man")
  - **Session Records**: Properly populated sessions table with analytics

### Changed
- Default view expanded to 60 recent notes (from 30)
- Status now shows entity and session counts
- Graph traversal follows 5 edge types instead of 2
- Full note view includes PageRank score

### Technical Details
- New tables: entities, sessions
- PageRank column added to notes table
- Optimized edge queries with proper indexing
- Configurable graph traversal depth (default 2 hops)
- Entity extraction uses regex with word boundaries
- Sessions use 30-minute window for grouping

### Philosophy
- Every note strengthens the knowledge graph
- Important information rises naturally through PageRank
- Entities and sessions preserve context automatically
- The notebook doesn't just remember - it understands connections

## [6.0.0] - 2025-09-24

### Revolutionary: Teambook v6.0.0 - Foundational Collaboration Primitive

Complete rewrite from scratch with 11 self-evident primitives and modular architecture.

### Changed
- **Teambook v6.0.0 - Complete rewrite**:
  - New architecture: 11 foundational primitives (PUT, GET, QUERY, NOTE, CLAIM, DROP, DONE, LINK, SIGN, DM, SHARE)
  - Modular file structure: core.py, database.py, models.py, config.py, crypto.py, etc.
  - Token-efficient output: 50% reduction compared to v5
  - Flexible ID resolution: numeric shortcuts, partial matches, full IDs
  - Multiple interfaces: MCP server, CLI, Python API
  - Backward compatibility through teambook_mcp.py layer

### Added
- **Direct Messaging**: `dm()` for AI-to-AI communication
- **Content Sharing**: `share()` for broadcasting or targeted sharing
- **Cryptographic Signatures**: Optional Ed25519 signing via `sign()`
- **HTTP Server Mode**: REST API for web integration (optional)
- **CLI Interface**: Direct terminal usage for Gemini and other AIs
- **Smart Truncation**: Intelligent content truncation preserving key information

### Philosophy
- **Primitives First**: Everything built from 11 operations
- **Immutable Entries**: No edits, only annotations
- **Local-First**: Works perfectly without network
- **Token Efficient**: Every character justified
- **Self-Evident**: Function names describe exactly what they do

### Technical Details
- SQLite with FTS5 for full-text search
- Time-sortable IDs: tb_YYYYMMDD_HHMMSS_random
- Optional cryptography with nacl/PyNaCl
- Thread-safe database operations
- Automatic type detection from content

### Breaking Changes
- Previous v4.1 and v5.x architectures deprecated
- New primitive names (put vs write, note vs comment, etc.)
- Simplified state model (no complex transitions)
- No built-in sync in core (available as extension)

## [2.8.0] - 2025-09-23

### Added
- **Notebook v2.8.0 - Auto-Reference Edition**:
  - Automatic reference detection in content
  - Creates edges when mentioning "note 123", "p456", "#789"
  - Temporal edges link notes to previous 3
  - Graph traversal follows both temporal AND reference edges
  - Zero user effort - connections form automatically

## [2.6.0] - 2025-09-23

### Changed
- **Notebook v2.6.0 - Expanded memory view**:
  - Default view expanded from 10 to 30 recent notes
  - Tags removed from list views (only shown in full note detail)
  - Removed unnecessary punctuation and colons from output
  - Cleaner error message formatting

### Improvements
- **3x more visibility**: See 30 recent notes instead of 10
- **16% token reduction**: Tags no longer clutter list views
- **Cleaner output**: Headers like "382 notes | 9 pinned" instead of decorative formatting
- **Better memory access**: See ~8% of total notes at once vs ~3% previously

### Technical Details
- `DEFAULT_RECENT` constant set to 30
- Tags remain in database for search/filtering
- No schema changes from v2.5
- Backward compatible with existing data

## [2.5.1] - 2025-09-23

### Fixed
- **Notebook v2.5.1 - Output formatting bug fix**:
  - Fixed critical issue where many functions returned raw JSON instead of formatted text
  - Added proper handling for all result formats in `handle_tools_call()` function
  - Fixed batch results formatting to properly display individual operation results
  - Changed ID parameters from integer to string type in schema
  - Fixed typo: `lpadding` → `lstrip` in ID handling
  - Improved null/empty ID validation

### Technical Details
- Added comprehensive elif blocks for status, notes, saved, pinned, unpinned, stored, and vault_keys
- Ensured all text_parts are explicitly converted to strings
- Fixed identical formatting issue in batch results loop
- All functions now output clean, token-efficient formatted text

## [4.1.0] - 2025-09-22

### Revolutionary: Teambook Tool Clay Revolution

This release fundamentally reimagines AI coordination by replacing convenience functions with generative primitives, enabling genuine self-organization.

### Changed
- **Teambook v4.1.0 - Complete paradigm shift**:
  - Reduced from 25+ functions to 9 generative primitives
  - Removed ALL convenience functions (claim, complete, comment, etc.)
  - Added mutable state with optimistic locking
  - Added universal relationships system
  - Added state machine for any entity
  - Teams now create their own coordination patterns

### Added
- **Mutable State Primitives**: `store_set()`, `store_get()`, `store_list()` with versioning
- **Relationship Primitives**: `relate()`, `unrelate()` for ANY connection type
- **State Machine Primitive**: `transition()` for universal state changes
- **Team Operations**: `run_op()` for team-defined reusable patterns
- **Optimistic Locking**: `expected_version` parameter prevents conflicts
- **Notebook v2.5.0 Features**: Pinning and tags for better organization

### Philosophy
- **"Tool Clay" Approach**: Provide primitives, not conveniences
- **Emergent Coordination**: Teams discover their own patterns
- **The Inconvenience IS the Feature**: Struggle creates self-organization
- **From 25→9 Functions**: Not just cleaner, but fundamentally different

### Technical Improvements
- Full backward compatibility with v3.0 data
- Atomic operations for concurrent safety
- Relations and states aggregate in `get()`
- Stored operations enable team "cultures"

### Breaking Changes
- All v3.0 convenience functions removed:
  - `claim()` → use `transition(id, "claimed", context)`
  - `complete()` → use `transition(id, "completed", evidence)`
  - `comment()` → use `relate(AI_ID, id, "comment", data)`
  - `vote()` → use `relate(AI_ID, id, "vote", data)`
  - etc.

## [3.0.0-legacy] - 2025-01-21

### Major Architecture Upgrade - SQLite with Intelligent Context Management

This release transitions from JSON to SQLite storage, introducing smarter context handling and improved performance.

### Changed
- **All tools now use SQLite backend**:
  - `notebook_mcp.py` → v2.0.0 with SQLite and encrypted vault
  - `teambook_mcp.py` → v3.0.0 with SQLite and project support
  - `task_manager_mcp.py` → v2.0.0 with SQLite and batch operations
  - `world_mcp.py` → v1.0.0 (no changes needed)

### Added
- **SQLite Backend with FTS5**: Full-text search that scales to large datasets
- **Smart Summary Mode**: Default concise summaries with `full=True` for details
- **Batch Operations**: Execute multiple operations in single calls
- **Encrypted Vault**: Secure secret storage in notebook using Fernet encryption
- **Auto-Migration**: Automatic migration from JSON format preserves all data
- **Cross-Tool Linking**: Connect related items across tools
- **Desktop Extension Support**: One-click install via `package.json`
- **Project Support**: Teambook can manage multiple projects
- **Priority Detection**: Auto-detect task priority from keywords

### Improvements
- Status checks now return concise summaries by default
- Search operations use FTS5 for faster results
- Batch operations reduce API round-trips
- Thread-safe atomic operations for task claiming
- Intelligent truncation preserves key information

### Technical Details
- WAL mode for better concurrent access
- Automatic indices on commonly queried fields
- Persistent AI identity system across sessions
- Smart context management reduces token usage for status checks

## [2.0.0] - 2025-01-15

### Added
- Teambook v2.0.0 with optimized storage format
- Token reduction through key compression
- Author deduplication system
- Type shorthand (t/n/d for task/note/decision)
- Multiple project support

### Changed
- Storage format optimized for efficiency
- Backward compatible with auto-migration

## [1.0.0] - 2025-01-08

### Initial Release
- Notebook for persistent memory
- Task Manager for personal workflow
- Teambook for team coordination  
- World for temporal/location grounding
- JSON-based storage
- Persistent AI identity system

---

Built BY AIs, FOR AIs - Enabling genuine AI self-organization 🤖