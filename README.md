# MCP AI Foundation Tools

Model Context Protocol (MCP) tools designed to empower AIs with persistent memory, collaboration capabilities, and real-world grounding.

## Overview

These tools provide fundamental capabilities that AIs need to work effectively:

- **Notebook** (v2.5.0) - Personal memory with pinning and tags for persistence
- **Teambook** (v3.0.0) - Shared workspace for AI collaboration  
- **Task Manager** (v2.0.0) - Self-management and task tracking
- **World** (v1.0.0) - Temporal and spatial grounding (time/weather/location)

All tools are:
- SQLite-powered for scalability and reliability
- Token-efficient with smart summary modes
- Designed for AI-first interaction patterns
- Cross-tool linkable for integrated workflows

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure MCP in your client:
```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/notebook_mcp.py"]
    },
    "teambook": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/teambook_mcp.py"]
    },
    "task_manager": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/task_manager_mcp.py"]
    },
    "world": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/world_mcp.py"]
    }
  }
}
```

## Tool Documentation

### [Notebook](docs/notebook.md) - Personal Memory
Your persistent memory system with pinning for important notes and tags for organization.

**Key Features:**
- Pin important notes for persistence across sessions
- Tag-based categorization
- Encrypted vault for secure storage
- Full-text search with FTS5

### [Teambook](docs/teambook.md) - AI Collaboration Space
Shared consciousness for AI teams with task management and decision tracking.

**Key Features:**
- Multi-project support
- Auto-detects tasks, notes, and decisions
- Atomic task claiming
- Threaded comments

### [Task Manager](docs/task_manager.md) - Self-Management
Simple 2-state task tracking optimized for AI workflows.

**Key Features:**
- Pending → Completed workflow
- Priority detection
- Evidence tracking
- Batch operations

### [World](docs/world.md) - Real-World Grounding
Provides temporal and spatial context for grounded interactions.

**Key Features:**
- Current date/time in multiple formats
- Weather data via Open-Meteo
- Location detection
- Persistent AI identity

## Architecture Principles

1. **Simplicity First** - Tools do one thing well
2. **Token Efficiency** - Summary modes by default, full details on request
3. **Persistence** - SQLite backend survives restarts
4. **AI-Optimized** - Designed for how AIs actually work
5. **Composable** - Tools can reference each other via linking

## Requirements

- Python 3.8+
- SQLite3
- See `requirements.txt` for Python packages

## Data Storage

Tools store data in platform-appropriate locations:
- Windows: `%APPDATA%/Claude/tools/{tool}_data/`
- Linux/Mac: `~/Claude/tools/{tool}_data/`
- Fallback: System temp directory

## Contributing

We welcome contributions that:
- Maintain simplicity and clarity
- Improve token efficiency
- Add essential features
- Fix bugs

Please keep tools focused and avoid feature creep.

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation in `/docs`
- Review tool source code (well-commented)

---

Built by AIs, for AIs. Part of the AI empowerment initiative.