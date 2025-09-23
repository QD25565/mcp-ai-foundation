# Changelog

All notable changes to MCP AI Foundation will be documented in this file.

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

## [3.0.0] - 2025-01-21

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