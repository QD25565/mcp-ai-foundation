# Changelog

All notable changes to the MCP AI Foundation tools are documented here.

## [2024.09.25] - Major Version Updates

### Notebook v4.0.0
- **BREAKING**: Pipe format output by default (70% token reduction)
- **BREAKING**: OR search logic by default (was AND)
- **NEW**: Operation memory with "last" keyword support
- **NEW**: Progressive search fallback (exact → OR → partial)
- **NEW**: Unified numeric ID format
- **IMPROVED**: Entity extraction with word boundaries
- **IMPROVED**: PageRank caching (5 minutes)
- **IMPROVED**: Session detection (30-minute gaps)
- **FIXED**: Search query sanitization
- **FIXED**: Entity matching accuracy

### Task Manager v3.0.0
- **BREAKING**: Pipe format output by default (70% token reduction)
- **NEW**: Smart task resolution (partial matching)
- **NEW**: "last" keyword for natural chaining
- **NEW**: Auto-priority detection from content
- **NEW**: Batch operation aliases (add, complete, etc.)
- **IMPROVED**: Contextual time formatting
- **IMPROVED**: Smart truncation at word boundaries
- **IMPROVED**: Evidence tracking with duration
- **FIXED**: Task matching algorithm
- **FIXED**: SQLite migration from JSON

### World v3.0.0
- **BREAKING**: Pipe format output by default (80% token reduction)
- **BREAKING**: Compact mode by default
- **NEW**: Weather threshold system (only shows if extreme)
- **NEW**: Configurable output format (pipe/json/text)
- **NEW**: Batch operations support
- **NEW**: Operation aliases (w, dt, wx, ctx)
- **IMPROVED**: Single-line output
- **IMPROVED**: Location persistence
- **IMPROVED**: Weather caching (10 minutes)
- **FIXED**: Platform-specific time formatting
- **FIXED**: Timezone handling

### Teambook v6.0 (Compatibility Layer)
- **NEW**: MCP compatibility wrapper for v6.0 primitives
- **NEW**: Maps legacy operations to new architecture
- **MAINTAINED**: Backward compatibility with existing tools
- **NOTE**: Local mode only (no sync features)

## [2024.09.15] - Architecture Improvements

### All Tools
- Unified installation scripts (Python, Bash, PowerShell, Batch)
- Consistent error handling across tools
- Improved logging to stderr only
- Database optimization with WAL mode
- Cross-platform path handling

## [2024.09.01] - Initial v3 Planning

### Design Goals
- 70%+ token reduction across all tools
- AI-first design patterns
- Natural language interfaces
- Operation chaining support
- Progressive enhancement

## [2024.08.15] - Stable v2 Release

### Notebook v2.0
- SQLite migration from JSON
- FTS5 full-text search
- Basic entity extraction
- Encrypted vault storage

### Task Manager v2.0
- SQLite backend
- Evidence tracking
- Duration calculation
- Priority levels

### World v2.0
- Weather integration
- Location persistence
- Identity management

## [2024.07.01] - Initial Release

### Notebook v1.0
- JSON file storage
- Basic CRUD operations
- Simple search

### Task Manager v1.0
- JSON file storage
- Task creation and completion
- Basic filtering

### World v1.0
- Time display
- IP geolocation

---

## Version Philosophy

Our versioning follows semantic versioning with a focus on token efficiency:

- **Major versions** (x.0.0): Breaking changes, typically 50%+ token reduction
- **Minor versions** (x.y.0): New features, backward compatible
- **Patch versions** (x.y.z): Bug fixes, performance improvements

## Migration Notes

### To v3/v4 from v2

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

### Performance Metrics

| Tool | v1 Tokens | v2 Tokens | v3/v4 Tokens | Reduction |
|------|-----------|-----------|--------------|-----------|
| Notebook | 1000 | 800 | 300 | 70% |
| Task Manager | 900 | 750 | 270 | 70% |
| World | 500 | 400 | 100 | 80% |
| **Average** | **800** | **650** | **223** | **72%** |

## Deprecation Schedule

- **v1.x**: No longer supported (as of 2024.09.01)
- **v2.x**: Maintenance mode (critical fixes only)
- **v3/v4.x**: Active development

## Known Issues

### Current
- PageRank calculation can be slow for 1000+ notes
- Weather API occasionally times out
- Large batch operations may exceed token limits

### Resolved in v3/v4
- ✅ Excessive token usage in list operations
- ✅ Search requiring exact matches
- ✅ No operation chaining support
- ✅ Verbose output formats

## Upcoming Features

### Planned for Next Release
- [ ] Cross-tool integration improvements
- [ ] Async operation support
- [ ] Compression for large outputs
- [ ] Incremental PageRank updates
- [ ] Weather prediction caching

### Under Consideration
- GraphQL API support
- Real-time collaboration
- Plugin architecture
- LLM-specific optimizations
- Streaming responses

---

For detailed documentation on each tool, see the individual tool docs in the `/docs` directory.
