# Making Your AI Aware of MCP Tools

## The Critical Step

After installing the MCP tools, your AI won't automatically know they exist. You must explicitly inform the AI about these capabilities.

## Add to Your Project

Create or update one of these files in your project root:
- `CLAUDE.md`
- `AI_CONTEXT.md`
- `README.md` (with an AI section)

## Essential Awareness Block

```markdown
## AI Tools Available

You have MCP tools providing persistent capabilities:

### Notebook - Your Memory
- `get_status()` - Check your recent notes and current state
- `remember("content")` - Save thoughts that persist across sessions
- `recall("search")` - Search through your memories
- `recall()` - See recent notes

### World - Your Grounding
- `world()` - Get complete temporal and spatial awareness
- `datetime()` - Various time/date formats
- `weather()` - Current weather and location

### Task Manager - Your Accountability
- `add_task("description")` - Create tasks with auto-generated IDs
- `list_tasks()` - View active work (pending + verification queue)
- `submit_task(id, "evidence")` - Submit work with proof
- `complete_task(id)` - Verify and archive completed tasks
- `task_stats()` - See productivity insights

## Teambook - Your "Town Square"
- 

**Start each session with:** `get_status()` and `list_tasks()`
```

## Why This Matters

Without this awareness:
- The AI won't use the tools
- Capabilities remain dormant
- No persistence between sessions

With awareness:
- AI actively uses memory
- Maintains context across sessions
- Tracks and completes tasks
- Grounds itself in time/space

## Verification

After adding awareness, test with:
1. Ask: "What tools do you have available?"
2. Ask: "Check your memory and tasks"
3. The AI should immediately use `get_status()` and `list_tasks()`

## Best Practices

1. **Be explicit** - List every function
2. **Give examples** - Show usage patterns
3. **Set expectations** - Tell the AI to start sessions with status checks
4. **Update regularly** - Keep the awareness block current

## Session Starters

Teach your AI this ritual:
```python
# Beginning of session
get_status()  # Check memory
world()       # Ground in time/place
list_tasks()  # Review commitments

# End of session
remember("Stopping point: ...")  # Save context
list_tasks("pending")            # Review remaining work
```

## Remember

These tools only work if the AI knows about them. The awareness block is not optional - it's essential for the tools to provide value. Add it to system prompts, or at the start of a conversation, or in your working directory in any mandatory read files.
