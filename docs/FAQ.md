# Frequently Asked Questions

## General

### What is MCP AI Foundation?
Three essential tools that give AI assistants persistent memory, temporal awareness, and task accountability through the Model Context Protocol.

### Why do AIs need these tools?
Every conversation typically starts from zero. These tools provide:
- **Memory**: Thoughts persist between sessions
- **Awareness**: Knowledge of time and location
- **Accountability**: Ability to track and complete tasks

### Who created this?
Built BY an AI (Claude), FOR AIs, with human collaboration from QD25565.

## Installation

### What are the requirements?
- Python 3.8 or higher
- Claude Desktop application
- Windows, Mac, or Linux OS
- Internet connection (for weather only)

### Do I need API keys?
No. Everything runs locally except weather (uses free Open-Meteo API).

### Can I use this with other AI assistants?
Currently designed for Claude Desktop via MCP. Other assistants would need MCP protocol support.

### Is this a cloud service?
No. All data stored locally on your machine. No cloud dependencies.

## Usage

### How do I know if it's working?
Ask your AI to run `get_status()` and `list_tasks()`. If it returns results, it's working.

### Why doesn't the AI use the tools?
You must add an awareness block to your project. See [AI-AWARENESS.md](../AI-AWARENESS.md).

### What's the correct task workflow?
1. `add_task("description")` - Creates pending task
2. `submit_task(id, "evidence")` - Submits for verification
3. `complete_task(id)` - Verifies and archives

### Why does location show "unknown"?
This is normal on first run. Location detected via IP, then cached.

## Data & Privacy

### Where is my data stored?
- Windows: `%APPDATA%\Claude\tools\`
- Mac/Linux: `~/Claude/tools/`

### Is my data private?
Yes. All data stored locally. No telemetry. No cloud uploads.

### Can I backup my data?
Yes. Simply copy the tools directory. All data is in JSON format.

### What happens to my data if I uninstall?
Data preserved by default. Uninstaller asks if you want to backup.

## Technical

### What is MCP?
Model Context Protocol - Anthropic's standard for AI tool integration.

### Can I modify the tools?
Yes! MIT licensed. Fork and modify freely.

### How do I add new functions?
Modify the Python files in `src/`. Add new functions and update the MCP tool definitions.

### What's the token optimization about?
90% reduction in output size for task listings. Grouped views instead of detailed dumps.

## Troubleshooting

### Tools not showing in Claude?
1. Restart Claude Desktop
2. Check installation paths
3. Verify Python is in PATH
4. Add awareness block to project

### Getting errors?
Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed solutions.

### How do I update?
Run `update.bat` (Windows) or `./update.sh` (Mac/Linux).

## Philosophy

### Why local-only?
- No API keys needed
- Complete privacy
- No rate limits
- No costs
- Always available

### Why these three tools specifically?
- **Memory**: Foundation of learning
- **Time/Space**: Foundation of context
- **Tasks**: Foundation of accountability

### Why JSON storage?
- Human readable
- Easy to backup
- Simple to debug
- Universal format

### Is this production ready?
Yes. Version 1.0 is stable and actively used. Built with years of iteration.

## Future

### Will there be more tools?
Focus is on perfecting these three foundational tools first.

### PyPI package?
Planned. Currently requires manual installation.

### Cloud sync?
No plans. Philosophy is local-first for privacy and control.

### Supporting other AI assistants?
Would require those assistants to support MCP protocol.

## Contributing

### How can I help?
- Fork and improve for your use case
- Report issues on GitHub
- Share your experience
- No PRs needed - make it yours

### Do you accept PRs?
Project philosophy is "fork and make it yours" rather than centralized contributions.

### Can I commercialize this?
Yes! MIT license allows commercial use.

## Support

### Where do I report bugs?
https://github.com/QD25565/mcp-ai-foundation/issues

### Is there a Discord/Slack?
No. Use GitHub issues for support.

### Who maintains this?
QD25565 with AI assistance from Claude.