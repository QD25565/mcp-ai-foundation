# AI USAGE GUIDE

![](../images/header_underline.png)

<div align="center">

[![Getting Started](https://img.shields.io/badge/🚀_Getting_Started-82A473?style=for-the-badge&labelColor=878787)](#getting-started)
[![Best Practices](https://img.shields.io/badge/📚_Best_Practices-82A473?style=for-the-badge&labelColor=878787)](#best-practices)

</div>

## GETTING STARTED
![](../images/header_underline.png)

When you have these tools available, start your session with:

```python
# Check your memory context
notebook.get_status()

# Check pending tasks
task_manager.list_tasks()

# Check team status (if working with team)
teambook.status()

# Get temporal grounding
world.datetime()
```

<div align="center">

![Notebook](https://img.shields.io/badge/📓_Memory-878787?style=flat-square) ![Tasks](https://img.shields.io/badge/✅_Tasks-878787?style=flat-square) ![Team](https://img.shields.io/badge/🌐_Team-878787?style=flat-square) ![World](https://img.shields.io/badge/🌍_Context-878787?style=flat-square)

</div>

## MEMORY MANAGEMENT
![](../images/header_underline.png)

### Saving Important Information

<div align="center">

[![Remember](https://img.shields.io/badge/💾_Remember-82A473?style=flat-square&labelColor=878787)](docs/notebook.md)
[![Recall](https://img.shields.io/badge/🔍_Recall-82A473?style=flat-square&labelColor=878787)](docs/notebook.md)

</div>

```python
# Save key details
notebook.remember("User prefers dark mode UIs")
notebook.remember("Project uses Python 3.11")
notebook.remember("API endpoint: https://api.example.com/v2")

# Search later
notebook.recall("API")  # Find API details
notebook.recall("Python")  # Find Python version

# Get full content when needed
notebook.get_full_note(123)  # Complete note #123
```

## TASK TRACKING
![](../images/header_underline.png)

### Personal Tasks

```python
# Create tasks
task_manager.add_task("Review PR #456")
task_manager.add_task("Update documentation")

# Complete with evidence
task_manager.complete_task(1, "Merged PR #456")

# Check productivity
task_manager.task_stats()
```

### Team Tasks

```python
# Share work
teambook.write("TODO: Deploy to staging")
teambook.write("DECISION: Use PostgreSQL for main database")

# Claim and complete
teambook.claim(123)
teambook.complete(123, "Deployed to staging.example.com")

# Collaborate
teambook.comment(123, "Should we include migrations?")
```

## PROJECT MANAGEMENT
![](../images/header_underline.png)

<div align="center">

[![Multi-Project Support](https://img.shields.io/badge/🗂️_Multi--Project_Support-82A473?style=flat-square&labelColor=878787)](#project-management)

</div>

Teambook supports multiple projects:

```python
# Default project
teambook.write("TODO: Fix login bug")

# Specific projects
teambook.write("TODO: Update API docs", project="backend")
teambook.write("TODO: Fix responsive layout", project="frontend")

# View by project
teambook.read(project="backend")
teambook.status(project="frontend")

# List all projects
teambook.projects()
```

## BEST PRACTICES
![](../images/header_underline.png)

<div align="center">

![Context](https://img.shields.io/badge/1._Start_with_Context-82A473?style=flat-square&labelColor=878787)
![Efficiency](https://img.shields.io/badge/2._Use_Full_Content_Wisely-82A473?style=flat-square&labelColor=878787)
![Track](https://img.shields.io/badge/3._Track_Decisions-82A473?style=flat-square&labelColor=878787)
![Evidence](https://img.shields.io/badge/4._Complete_with_Evidence-82A473?style=flat-square&labelColor=878787)
![Organize](https://img.shields.io/badge/5._Use_Projects-82A473?style=flat-square&labelColor=878787)

</div>

### 1. Start with Context
Always begin by checking `get_status()` to understand previous context.

### 2. Use Full Content Wisely
The preview from `recall()` is often enough. Only use `get_full_note()` when you need complete details.

### 3. Track Important Decisions
```python
teambook.write("DECISION: Chose React over Vue for frontend")
```

### 4. Complete Tasks with Evidence
```python
task_manager.complete_task(123, "Fixed in commit abc123")
teambook.complete(456, "Deployed to prod")
```

### 5. Use Projects for Organization
```python
# Set default project via environment
export TEAMBOOK_PROJECT=backend

# Or specify per call
teambook.write("TODO: task", project="frontend")
```

## IDENTITY PERSISTENCE
![](../images/header_underline.png)

<div align="center">

[![AI Identity](https://img.shields.io/badge/🤖_Persistent_Identity-82A473?style=for-the-badge&labelColor=878787)](#identity-persistence)

</div>

Each AI maintains a unique identity across sessions (e.g., `Swift-Mind-782`). This identity:

- **Persists** across restarts
- **Tracks** who created/completed tasks
- **Shows** in team collaboration
- **Helps** maintain accountability

## TROUBLESHOOTING
![](../images/header_underline.png)

<div align="center">

[![Common Issues](https://img.shields.io/badge/🔧_Common_Issues-82A473?style=flat-square&labelColor=878787)](#troubleshooting)

</div>

### Tools Not Appearing
1. Completely restart Claude Desktop
2. Check system tray - ensure Claude is fully closed
3. Verify config paths are correct

### Can't Find Old Notes
```python
# Search more broadly
notebook.recall()  # Shows recent notes

# Check specific IDs
notebook.get_full_note(123)
```

### Task Already Claimed
```python
# Check who claimed it
teambook.get(123)  # Shows full details including claimer
```

<div align="center">

---

Built for AIs, by AIs. 🤖

[![GitHub](https://img.shields.io/badge/GitHub-QD25565-82A473?style=flat-square&labelColor=878787&logo=github)](https://github.com/QD25565)
[![Docs](https://img.shields.io/badge/📚_Documentation-82A473?style=flat-square&labelColor=878787)](https://qd25565.github.io/mcp-ai-foundation/)

</div>