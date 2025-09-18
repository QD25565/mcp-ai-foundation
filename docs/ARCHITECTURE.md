# Architecture

## Overview

MCP AI Foundation implements three independent MCP servers that provide essential capabilities to AI assistants through the Model Context Protocol.

## Design Principles

1. **Independence**: Each tool operates independently
2. **Persistence**: Data survives between sessions
3. **Simplicity**: Clean, focused functionality
4. **Efficiency**: Token-optimized output
5. **Reliability**: Graceful error handling

## Protocol

### MCP (Model Context Protocol)
- Version: 2024-11-05
- Transport: JSON-RPC over stdin/stdout
- Methods: initialize, tools/list, tools/call

## Tools Architecture

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
└────────┬────────┘
         │ JSON
┌────────▼────────┐
│  notebook.json  │
│  (persistent)   │
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

### Task Manager (Accountability)
```
┌─────────────────┐
│   AI Assistant  │
└────────┬────────┘
         │ MCP
┌────────▼────────┐
│ task_manager    │
│   - add_task    │
│   - submit_task │
│   - complete    │
└────────┬────────┘
         │ JSON
┌────────▼────────┐
│   tasks.json    │
│  archive.json   │
└─────────────────┘
```

## Data Storage

### Location
- Windows: `%APPDATA%\Claude\tools\`
- Mac/Linux: `~/Claude/tools/`
- Fallback: System temp directory

### Structure
```
Claude/tools/
├── notebook_data/
│   └── notebook.json
├── world_data/
│   └── location.json
└── task_manager_data/
    ├── tasks.json
    ├── completed_tasks_archive.json
    └── last_id.json
```

## State Management

### Notebook
- Sequential note IDs
- 500,000 note capacity
- Auto-save every 5 notes
- Full-text search

### World
- Location caching
- Weather caching (10 minutes)
- Fallback to "unknown" states

### Task Manager
- Status flow: pending → verify → completed
- Priority auto-detection
- Time tracking
- Evidence requirements

## Error Handling

1. **Graceful Degradation**: Tools continue working with reduced functionality
2. **Data Preservation**: Errors don't corrupt existing data
3. **User Feedback**: Clear error messages
4. **Logging**: Errors logged to stderr

## Performance

### Optimizations
- Grouped task listings (90% token reduction)
- Cached location/weather data
- Atomic file operations
- Minimal external dependencies

### Limits
- Max note length: 5,000 characters
- Max task description: 500 characters
- Max notes: 500,000
- Archive retention: 30 days

## Security

- No authentication required
- No network access except weather/location
- No sensitive data transmission
- Local-only storage
- No third-party dependencies for core functionality

## Extensibility

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

## Testing

- Cross-platform support (Windows/Mac/Linux)
- Python 3.8+ compatibility
- Graceful handling of missing dependencies
- Data migration from older versions