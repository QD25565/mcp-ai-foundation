# ARCHITECTURE

![](../images/header_underline.png)

<div align="center">

[![Overview](https://img.shields.io/badge/📐_System_Architecture-82A473?style=for-the-badge&labelColor=878787)](#overview)
[![Design Principles](https://img.shields.io/badge/🎯_Design_Principles-82A473?style=for-the-badge&labelColor=878787)](#design-principles)

</div>

## OVERVIEW
![](../images/header_underline.png)

MCP AI Foundation implements four independent MCP servers that provide essential capabilities to AI assistants through the Model Context Protocol.

<div align="center">

![Notebook](https://img.shields.io/badge/📓_Notebook-878787?style=flat-square) ![Task Manager](https://img.shields.io/badge/✅_Task_Manager-878787?style=flat-square) ![Teambook](https://img.shields.io/badge/🌐_Teambook-878787?style=flat-square) ![World](https://img.shields.io/badge/🌍_World-878787?style=flat-square)

</div>

## DESIGN PRINCIPLES
![](../images/header_underline.png)

<div align="center">

![Independence](https://img.shields.io/badge/1._Independence-82A473?style=flat-square&labelColor=878787) ![Persistence](https://img.shields.io/badge/2._Persistence-82A473?style=flat-square&labelColor=878787) ![Simplicity](https://img.shields.io/badge/3._Simplicity-82A473?style=flat-square&labelColor=878787) ![Efficiency](https://img.shields.io/badge/4._Efficiency-82A473?style=flat-square&labelColor=878787) ![Reliability](https://img.shields.io/badge/5._Reliability-82A473?style=flat-square&labelColor=878787)

</div>

1. **Independence**: Each tool operates independently
2. **Persistence**: Data survives between sessions
3. **Simplicity**: Clean, focused functionality
4. **Efficiency**: Token-optimized output
5. **Reliability**: Graceful error handling

## PROTOCOL
![](../images/header_underline.png)

### MCP (Model Context Protocol)
- **Version**: 2024-11-05
- **Transport**: JSON-RPC over stdin/stdout
- **Methods**: initialize, tools/list, tools/call

<div align="center">

[![Protocol Version](https://img.shields.io/badge/MCP_2024--11--05-82A473?style=flat-square&labelColor=878787)](https://modelcontextprotocol.io/)

</div>

## TOOLS ARCHITECTURE
![](../images/header_underline.png)

### Notebook (Memory)
```
┌─────────────────┐
│   AI Assistant  │
└────────┬────────┘
         │ MCP
┌────────▼────────┐
│  notebook_mcp   │
│   - remember    │
│   - recall      │
│   - get_status  │
│   - get_full_note│
└────────┬────────┘
         │ JSON
┌────────▼────────┐
│  notebook.json  │
│  (persistent)   │
└─────────────────┘
```

### Teambook (Team Coordination) v2.0.0
```
┌─────────────────┐
│   AI Assistant  │
└────────┬────────┘
         │ MCP
┌────────▼────────┐
│  teambook_mcp   │
│   - write       │
│   - read        │
│   - claim       │
│   - complete    │
│   - comment     │
└────────┬────────┘
         │ JSON (optimized)
┌────────▼────────┐
│  teambook.json  │
│  (v2 format)    │
└─────────────────┘
```

### World (Grounding)
```
┌─────────────────┐
│   AI Assistant  │
└────────┬────────┘
         │ MCP
┌────────▼────────┐
│   world_mcp     │
│   - world       │
│   - datetime    │
│   - weather     │
└────────┬────────┘
         │ HTTP
┌────────▼────────┐
│  External APIs  │
│  - IP Geoloc    │
│  - Open-Meteo   │
└─────────────────┘
```

### Task Manager (Personal Workflow)
```
┌─────────────────┐
│   AI Assistant  │
└────────┬────────┘
         │ MCP
┌────────▼────────┐
│ task_manager    │
│   - add_task    │
│   - list_tasks  │
│   - complete    │
│   - task_stats  │
└────────┬────────┘
         │ JSON
┌────────▼────────┐
│   tasks.json    │
│  archive.json   │
└─────────────────┘
```

## DATA STORAGE
![](../images/header_underline.png)

### Location

<div align="center">

![Windows](https://img.shields.io/badge/Windows-878787?style=flat-square) ![Mac](https://img.shields.io/badge/Mac-878787?style=flat-square) ![Linux](https://img.shields.io/badge/Linux-878787?style=flat-square)

</div>

- **Windows**: `%APPDATA%\Claude\tools\`
- **Mac/Linux**: `~/.config/Claude/tools/`
- **Fallback**: System temp directory

### Structure
```
Claude/tools/
├── notebook_data/
│   └── notebook.json
├── teambook_[project]_data/
│   ├── teambook.json (v2 optimized)
│   ├── archive.json
│   └── last_id.json
├── world_data/
│   └── location.json
├── task_manager_data/
│   ├── tasks.json
│   ├── completed_archive.json
│   └── last_id.json
└── ai_identity.txt (shared identity)
```

## TOKEN OPTIMIZATION (v2.0.0)
![](../images/header_underline.png)

<div align="center">

[![35% Token Reduction](https://img.shields.io/badge/↓35%25_Token_Reduction-82A473?style=for-the-badge&labelColor=878787)](#token-optimization-v200)

</div>

### Teambook Storage Format

**Before (v1.0.0):**
```json
{
  "id": 789,
  "content": "TODO: Update docs",
  "type": "task",
  "author": "Swift-Spark-266",
  "created": "2025-09-20T19:49:12.012690"
}
```
~45 tokens for structure + content tokens

**After (v2.0.0):**
```json
{
  "authors": {"a1": "Swift-Spark-266"},
  "entries": {
    "789": {
      "id": 789,
      "c": "TODO: Update docs",
      "t": "t",
      "a": "a1",
      "ts": "2025-09-20T19:49:12"
    }
  }
}
```
~25 tokens for structure + content tokens = **35% reduction**

### Optimization Techniques
1. **Short Keys**: `c` (content), `t` (type), `a` (author), `ts` (timestamp)
2. **Author Deduplication**: Map authors to IDs (`a1`, `a2`)
3. **Type Compression**: `t` (task), `n` (note), `d` (decision)
4. **Timestamp Truncation**: Remove microseconds
5. **Backward Compatibility**: Auto-migrates v1 to v2

### Token Savings at Scale

<div align="center">

| Entries | v1 Tokens | v2 Tokens | Saved | % of 200K Context |
|---------|-----------|-----------|-------|-------------------|
| 100 | ~12,300 | ~10,600 | 1,700 | 0.85% |
| 1,000 | ~123,000 | ~106,000 | 17,000 | 8.5% |
| 5,000 | ~615,000 | ~530,000 | 85,000 | 42.5% |

</div>

## STATE MANAGEMENT
![](../images/header_underline.png)

### Notebook
- Sequential note IDs
- 500,000 note capacity
- Auto-save every 5 notes
- Full-text search

### Teambook
- Project-based separation
- Atomic task claiming
- Threaded comments
- Archive with reason tracking
- 100,000 entry capacity

### World
- Location caching
- Weather caching (10 minutes)
- Fallback to "unknown" states

### Task Manager
- Simple 2-state workflow: pending → completed
- Priority auto-detection
- Time tracking
- Evidence recording

## PERSISTENT AI IDENTITY
![](../images/header_underline.png)

<div align="center">

[![AI Identity](https://img.shields.io/badge/🤖_Persistent_Identity-82A473?style=for-the-badge&labelColor=878787)](#persistent-ai-identity)

</div>

All tools share a persistent AI identity stored in `ai_identity.txt`:
- **Format**: `[Adjective]-[Noun]-[Number]` (e.g., Swift-Spark-266)
- **Created once**, persists across all sessions
- **Enables** continuity and collaboration tracking

## ERROR HANDLING
![](../images/header_underline.png)

1. **Graceful Degradation**: Tools continue working with reduced functionality
2. **Data Preservation**: Errors don't corrupt existing data
3. **User Feedback**: Clear error messages
4. **Logging**: Errors logged to stderr

## PERFORMANCE
![](../images/header_underline.png)

<div align="center">

[![Optimizations](https://img.shields.io/badge/⚡_Optimizations-82A473?style=flat-square&labelColor=878787)](#optimizations)
[![Limits](https://img.shields.io/badge/📊_Limits-82A473?style=flat-square&labelColor=878787)](#limits)

</div>

### Optimizations
- Token-optimized storage formats
- Smart truncation (code-aware)
- Contextual time formatting (5m, y19:30, 3d)
- Cached location/weather data
- Atomic file operations

### Limits
- Max note/content: 5,000 characters
- Max task description: 500 characters
- Max comment: 1,000 characters
- Max entries: 100,000 (teambook)
- Archive retention: 30 days

## SECURITY
![](../images/header_underline.png)

<div align="center">

![No Auth](https://img.shields.io/badge/🔓_No_Auth_Required-878787?style=flat-square)
![Local Only](https://img.shields.io/badge/💾_Local_Storage-878787?style=flat-square)
![No Tracking](https://img.shields.io/badge/🔒_No_Tracking-878787?style=flat-square)

</div>

- No authentication required
- No network access except weather/location
- No sensitive data transmission
- Local-only storage
- No third-party dependencies for core functionality

## EXTENSIBILITY
![](../images/header_underline.png)

### Adding New Tools
1. Create new MCP server script
2. Implement protocol handlers
3. Add to Claude config
4. Document in AI awareness

### Modifying Existing Tools
- Maintain backward compatibility
- Preserve data migration paths
- Update version numbers
- Document changes

## TESTING
![](../images/header_underline.png)

<div align="center">

[![Cross Platform](https://img.shields.io/badge/🖥️_Cross_Platform-82A473?style=flat-square&labelColor=878787)](https://github.com/QD25565/mcp-ai-foundation/actions)
[![Python 3.8+](https://img.shields.io/badge/🐍_Python_3.8+-82A473?style=flat-square&labelColor=878787)](https://www.python.org/)

</div>

- Cross-platform support (Windows/Mac/Linux)
- Python 3.8+ compatibility
- Graceful handling of missing dependencies
- Data migration from older versions
- Token usage verification

<div align="center">

---

Built for AIs, by AIs. 🤖

[![GitHub](https://img.shields.io/badge/GitHub-QD25565-82A473?style=flat-square&labelColor=878787&logo=github)](https://github.com/QD25565)

</div>