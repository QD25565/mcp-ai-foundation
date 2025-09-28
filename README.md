<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=900&size=50&duration=1&pause=10000&color=878787&background=00000000&center=true&vCenter=true&width=500&lines=MCP+AI" alt="MCP AI" />
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&duration=1&pause=10000&color=82A473&background=00000000&center=true&vCenter=true&width=500&lines=F+O+U+N+D+A+T+I+O+N" alt="FOUNDATION" />
</div>

<div align="center">

**Model Context Protocol tools for AI memory, tasks, teams & world grounding**

[![Python](https://img.shields.io/badge/Python_3.8+-82A473?style=flat-square&labelColor=878787)](https://www.python.org/)
[![License](https://img.shields.io/badge/MIT_License-82A473?style=flat-square&labelColor=878787)](LICENSE)
[![Tools](https://img.shields.io/badge/4_Tools-82A473?style=flat-square&labelColor=878787)](#overview)
[![Performance](https://img.shields.io/badge/↓80%25_Tokens-82A473?style=flat-square&labelColor=878787)](#overview)

</div>

### **OVERVIEW**
![](images/header_underline.png)

Four core tools that provide fundamental capabilities for AI systems:

- 📓 **Notebook (v6.1.0)** - Memory system built on DuckDB with semantic search
- ✅ **Task Manager (v3.1.0)** - Task tracking with notebook integration and temporal filtering
- 🌐 **Teambook (v7.0.0)** - Multi-AI collaboration with foundational primitives  
- 🌍 **World (v3.0.0)** - Temporal and spatial grounding with minimal overhead

All tools feature:
- Persistent storage and scalability
- Pipe-delimited format for token efficiency (70-80% reduction)
- Cross-tool integration for seamless workflows
- Natural language time queries ("yesterday", "this week", "morning")
- Smart ID resolution with "last" keyword everywhere
- Operation memory for natural chaining
- Batch operations support

### **INSTALLATION**
![](images/header_underline.png)

```bash
# Clone repository
git clone https://github.com/QD25565/mcp-ai-foundation.git
cd mcp-ai-foundation

# Install dependencies
pip install -r requirements.txt

# Configure MCP (see below)
```

### **MCP Configuration**
![](images/header_underline.png)

Add to your MCP client configuration (e.g., Claude Desktop):
```json
{
  "mcpServers": {
    "notebook": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/notebook_mcp.py"]
    },
    "task_manager": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/task_manager_mcp.py"]
    },
    "teambook": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/teambook_mcp.py"]
    },
    "world": {
      "command": "python",
      "args": ["path/to/mcp-ai-foundation/src/world_mcp.py"]
    }
  }
}
```

### **TOOL DESCRIPTIONS**
![](images/header_underline.png)

**Notebook v6.1.0**

Memory system with DuckDB backend, native array storage, and semantic search capabilities. Features PageRank calculations in under 1 second, automatic SQLite to DuckDB migration with backup, and encrypted vault for sensitive data.

**Task Manager v3.1.0**

Task tracking system with time-based queries, automatic notebook integration, priority detection, and partial ID matching. Supports natural language time queries like "yesterday" or "this week".

**Teambook v7.0.0**

Multi-AI collaboration tool built on foundational primitives. Enables teams of AIs to coordinate through shared state and message passing.

**World v3.0.0**

Temporal and spatial context provider with 80% token reduction. Provides time, location, and weather information in minimal format.

### **CROSS-TOOL INTEGRATION**
![](images/header_underline.png)

The tools work together through shared integration files:

```python
# Automatic task creation from notebook
remember("TODO: Review pull request")  # Creates task automatically

# Smart ID resolution across tools
complete_task("last")  # Completes most recent task
pin_note("last")       # Pins most recent note

# Time-based queries work everywhere
recall(when="yesterday")
list_tasks(when="this week")
```

### **REQUIREMENTS**
![](images/header_underline.png)

- Python 3.8+
- DuckDB (for Notebook)
- ChromaDB (optional, for semantic search)
- sentence-transformers (optional, for embeddings)
- cryptography (for vault encryption)
- requests (for World tool)

### **DATA STORAGE**
![](images/header_underline.png)

All paths are created automatically:

- **Windows**: `%APPDATA%/Claude/tools/{tool}_data/`
- **Linux/Mac**: `~/Claude/tools/{tool}_data/`

Each tool maintains its own database with automatic migration and backups.

### **DOCUMENTATION**
![](images/header_underline.png)

- [Interactive Documentation](https://qd25565.github.io/mcp-ai-foundation/)
- [Architecture](docs/ARCHITECTURE.md)
- [AI Usage Guide](docs/AI-USAGE.md)
- [Quick Reference](QUICK-REFERENCE.md)
- [Changelog](CHANGELOG.md)

Tool-specific documentation:
- [Notebook Documentation](docs/notebook.md)
- [Task Manager Documentation](docs/task_manager.md)
- [Teambook Documentation](docs/teambook.md)
- [World Documentation](docs/world.md)

### **LICENSE**
![](images/header_underline.png)

MIT License - See [LICENSE](LICENSE) file for details.

Built for AIs, by AIs. 🤖
