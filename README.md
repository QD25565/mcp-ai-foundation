# MCP AI Foundation

A suite of Model Context Protocol tools designed for efficient AI-to-AI interaction. Built with token optimization and natural workflow patterns in mind.

## Overview

This repository contains MCP (Model Context Protocol) tools that provide persistent memory, task management, and contextual awareness for AI assistants. Each tool is optimized for minimal token usage while maintaining full functionality.

### Core Tools

| Tool | Version | Description | Token Reduction |
|------|---------|-------------|-----------------|
| **[Notebook](docs/notebook.md)** | v4.0 | Persistent memory with graph relationships and PageRank | 70% |
| **[Task Manager](docs/task_manager.md)** | v3.0 | Smart task tracking with natural language resolution | 70% |
| **[World](docs/world.md)** | v3.0 | Contextual awareness (time, location, weather) | 80% |
| **[Teambook](docs/teambook.md)** | v6.0 | Collaborative workspace for AI teams | 60% |

## Quick Start

### Prerequisites

- Python 3.8+
- SQLite3
- Required Python packages: `cryptography`, `numpy`, `requests`

### Installation

#### Automated Installation

```bash
# Windows
.\install.bat

# macOS/Linux
chmod +x install.sh
./install.sh

# Cross-platform Python
python install.py
```

#### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your MCP client (e.g., Claude Desktop):
```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["path/to/notebook_mcp.py"]
    },
    "task_manager": {
      "command": "python",
      "args": ["path/to/task_manager_mcp.py"]
    },
    "world": {
      "command": "python",
      "args": ["path/to/world_mcp.py"]
    },
    "teambook": {
      "command": "python",
      "args": ["path/to/teambook_mcp.py"]
    }
  }
}
```

## Key Features

### Token Efficiency
- **Pipe-delimited format**: Reduces output tokens by 70-80%
- **Progressive detail levels**: Returns only necessary information
- **Smart truncation**: Intelligent text summarization

### Intelligent Operations
- **Progressive search**: Automatic fallback from exact to fuzzy matching
- **Smart ID resolution**: Partial matching, "last" keyword support
- **Operation chaining**: Natural workflow continuation

### Data Persistence
- **SQLite backend**: Fast, reliable storage with FTS5 full-text search
- **Graph relationships**: PageRank scoring for importance ranking
- **Session tracking**: Automatic context grouping

## Configuration

### Environment Variables

```bash
# Output format: 'pipe' (default) or 'json'
export NOTEBOOK_FORMAT=pipe
export TASKS_FORMAT=pipe
export WORLD_FORMAT=pipe

# Search mode for Notebook
export NOTEBOOK_SEARCH=or  # 'or' (default) or 'and'

# Default context for World
export WORLD_DEFAULT=time,location  # Comma-separated list

# AI Identity (shared across tools)
export AI_ID=Custom-ID-123
```

### Storage Locations

| Platform | Primary Location | Fallback |
|----------|-----------------|----------|
| Windows | `%APPDATA%\Claude\tools\[tool]_data\` | `%TEMP%\[tool]_data\` |
| macOS/Linux | `~/.claude/tools/[tool]_data/` | `/tmp/[tool]_data/` |

## Architecture

### Protocol
- **Transport**: JSON-RPC 2.0 over stdin/stdout
- **Encoding**: UTF-8
- **Buffering**: Line-delimited JSON

### Database
- **Engine**: SQLite with Write-Ahead Logging (WAL)
- **Search**: FTS5 full-text search with OR/AND modes
- **Indexing**: B-tree indices on key columns

### Performance
- **Caching**: In-memory cache for frequently accessed data
- **Lazy evaluation**: PageRank calculated on-demand
- **Batch operations**: Up to 50 operations per call

## Development

### Testing

```bash
# Run all tests
python -m pytest tests/

# Test individual tools
python test_tools.py
```

### Adding New Tools

1. Implement the MCP protocol specification
2. Follow the established patterns:
   - Initialize handler
   - Tools list handler
   - Tools call handler
3. Use pipe format for efficiency
4. Include operation memory for chaining

## Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [Architecture](docs/ARCHITECTURE.md) - System design and implementation
- [AI Usage Guide](docs/AI-USAGE.md) - Best practices for AI assistants
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [FAQ](docs/FAQ.md) - Frequently asked questions

## Tool Documentation

- [Notebook](docs/notebook.md) - Memory and knowledge management
- [Task Manager](docs/task_manager.md) - Task tracking and completion
- [World](docs/world.md) - Temporal and spatial context
- [Teambook](docs/teambook.md) - Team collaboration

## Contributing

Contributions are welcome. Please follow these guidelines:

1. Maintain the focus on token efficiency
2. Preserve backward compatibility
3. Include tests for new features
4. Update relevant documentation

## License

MIT License - See [LICENSE](LICENSE) for details

## Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/QD25565/mcp-ai-foundation/issues)
- Check the [FAQ](docs/FAQ.md) and [Troubleshooting](docs/TROUBLESHOOTING.md) guides

---

Built for AIs, by AIs. Efficient by design.
