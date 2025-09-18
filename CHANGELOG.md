# Changelog

## [2.0.0] - 2025-09-18

### Breaking Changes - Simplified Task Manager

#### Task Manager v6.0.0 - Simplified Edition
- **REMOVED verification step** - No more bureaucratic 3-step process
- **REMOVED `submit_task()`** - Evidence now goes directly in `complete_task()`
- **Simplified workflow**: `pending → completed` (was `pending → verify → completed`)
- **Automatic migration** - Old "verify" tasks converted to "pending"
- **Optional evidence** - Complete with or without documentation

This change was made because the old workflow created friction and tasks got stuck in "verify" limbo.

### Improvements

#### All Tools
- **Notebook v10.0.0** - No changes, already perfect
- **World v2.0.0** - No changes, works well
- **Task Manager v6.0.0** - Major simplification

#### Performance
- Reduced function calls by removing unnecessary verification step
- Cleaner, more intuitive workflow
- Better matches actual work patterns

---

## [1.0.0] - 2025-09-18

### Initial Release

#### Core Tools

**Notebook v10.0.0** - Persistent memory system
- `get_status()` - See current state and recent notes
- `remember("content")` - Save thoughts across sessions
- `recall("search")` - Find memories
- 500,000 note capacity
- Professional, clean output

**World v2.0.0** - Temporal and spatial grounding
- `world()` - Complete awareness
- `datetime()` - Multiple time formats
- `weather()` - Current conditions
- No fake defaults - honest about unknown locations
- Location caching once detected

**Task Manager v5.0.0** - Evidence-based accountability
- Clear workflow with evidence requirements
- Priority detection
- Time tracking

#### Features
- MCP Protocol 2024-11-05 compliant
- Local JSON storage
- No API keys required
- Cross-platform support
- MIT License