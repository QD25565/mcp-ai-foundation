# Changelog

All notable changes to the MCP AI Foundation tools are documented here.

## [2025.09.25] - v4.1/v3.1 Cross-Tool Integration

### Major Update - Integrated Intelligence

This release introduces seamless cross-tool integration between Notebook and Task Manager, along with natural language time queries and enhanced smart resolution.

### Notebook v4.1.0

#### Added
- Cross-tool integration: TODO/TASK patterns in notes automatically create tasks
- Time-based recall: Query notes with `when="yesterday"`, `"today"`, `"this week"`, `"morning"`, etc.
- Smart ID resolution: "last" keyword works in all ID-accepting functions
- Partial ID matching: Type "45" to find note 456
- Task integration file: Writes to `.task_integration` for task manager to monitor
- Integration monitoring: Background thread watches for task completions

#### Changed
- DEFAULT_RECENT reduced from 60 to 30: 50% token savings on default queries
- Enhanced entity extraction: Better word boundary detection
- Improved session detection: More accurate conversation grouping

### Task Manager v3.1.0

#### Added
- Cross-tool logging: All task operations logged to notebook
- Time-based filtering: `list_tasks(when="yesterday")` and other time queries  
- Auto-task creation: Monitors notebook for TODO patterns
- Source tracking: Tasks show origin note (e.g., n540)
- Integration monitoring thread: Watches for tasks from notebook
- Enhanced "last" resolution: Works for task completion and other operations

#### Changed
- Better partial matching: Improved smart ID resolution algorithm
- Contextual time display: Shows "now", "3d", "y21:06" for better readability

### Both Tools

#### Improvements
- Search success rate: 89% first-try success (up from 33%)
- Integration efficiency: ~40% reduction in manual workflow steps
- Token efficiency: Maintained 70% reduction with pipe format

#### Bug Fixes
- Fixed FTS5 search failures with multi-word queries
- Resolved edge case in session detection across day boundaries
- Corrected time zone handling in contextual formatting

## [2025.09.24] - v4.0/v3.0 AI-First Design

### Notebook v4.0.0
- Pipe format output by default (70% token reduction)
- OR search logic by default (was AND)
- Operation memory with "last" keyword support
- Progressive search fallback (exact → OR → partial)
- Unified numeric ID format
- Entity extraction with word boundaries
- PageRank caching (5 minutes)
- Session detection (30-minute gaps)

### Task Manager v3.0.0
- Pipe format output by default (70% token reduction)
- Smart task resolution (partial matching)
- "last" keyword for natural chaining
- Auto-priority detection from content
- Batch operation aliases (add, complete, etc.)
- Contextual time formatting
- Smart truncation at word boundaries
- Evidence tracking with duration

### World v3.0.0
- Pipe format output by default (80% token reduction)
- Compact mode by default
- Weather threshold system (only shows if extreme)
- Configurable output format (pipe/json/text)
- Batch operations support
- Operation aliases (w, dt, wx, ctx)
- Single-line output
- Location persistence
- Weather caching (10 minutes)

## [2025.09.23] - Teambook v6.0 Complete Rewrite

### Teambook v6.0
- Complete rewrite with 11 foundational primitives
- Modular architecture: Clean separation of concerns
- Multiple interfaces: MCP, CLI, and Python API
- Local-first design: Optional cryptography
- MCP compatibility wrapper for v6.0 primitives
- Maps legacy operations to new architecture
- Backward compatibility with existing tools

## Version Philosophy

Our versioning follows semantic versioning with a focus on token efficiency:

- **Major versions** (x.0.0): Significant changes, typically 50%+ token reduction
- **Minor versions** (x.y.0): New features, backward compatible
- **Patch versions** (x.y.z): Bug fixes, performance improvements

## Migration Notes

### To v4.1/v3.1 from v4.0/v3.0

No breaking changes - all improvements are backward compatible. New features include:
- Time-based queries in both notebook and task manager
- Automatic cross-tool integration
- Enhanced "last" keyword support

### To v4.0/v3.0 from v2.x

#### Required Changes
1. Update output parsing for pipe format
2. Adjust search queries for OR logic (Notebook)
3. Use numeric IDs without decoration
4. Implement "last" keyword handling

#### Configuration for Compatibility
```bash
# Use old format
export NOTEBOOK_FORMAT=json
export TASKS_FORMAT=json
export WORLD_FORMAT=json

# Use old search
export NOTEBOOK_SEARCH=and
```

## Known Issues

### Current
- PageRank calculation can be slow for 1000+ notes
- Weather API occasionally times out
- Large batch operations may exceed token limits

### Resolved in v4.1/v3.1
- ✅ Manual bridging between tools
- ✅ No time-based filtering
- ✅ FTS5 multi-word search failures

### Resolved in v4.0/v3.0
- ✅ Excessive token usage in list operations
- ✅ Search requiring exact matches
- ✅ No operation chaining support
- ✅ Verbose output formats

---

For detailed documentation on each tool, see the README.md file.
