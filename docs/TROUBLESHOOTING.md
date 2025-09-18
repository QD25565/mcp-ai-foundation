# Troubleshooting Guide

## Installation Issues

### "Python is not installed or not in PATH"
**Solution:**
1. Install Python 3.8+ from https://python.org
2. During installation, check "Add Python to PATH"
3. Restart your terminal/command prompt

### "Claude Desktop config not found"
**Solution:**
1. Ensure Claude Desktop is installed
2. Run Claude Desktop at least once
3. Check config locations:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Mac: `~/.claude/claude_desktop_config.json`
   - Linux: `~/.config/claude/claude_desktop_config.json`

### "requests module not found"
**Solution:**
```bash
pip install requests
# or
pip3 install requests
```

## Runtime Issues

### Tools not appearing in Claude
**Solution:**
1. Restart Claude Desktop after installation
2. Check the config file has the tools listed
3. Ensure Python paths are correct in config
4. Add awareness block to your project

### "Tool not found" errors
**Causes & Solutions:**
1. **Incorrect path**: Check paths in claude_desktop_config.json
2. **Python not in PATH**: Ensure Python is accessible
3. **Missing files**: Verify all .py files exist in src/

### Location shows "Unknown"
**This is normal behavior:**
- First run always shows unknown
- Location detected via IP geolocation
- Once detected, it's cached
- No fake defaults in v1.0+

## Data Issues

### Lost notes/tasks after update
**Prevention:**
- Always backup before updating
- Data stored in: `%APPDATA%\Claude\tools\`

**Recovery:**
1. Check backup files (*.backup)
2. Look in temp directory
3. Data files are JSON - can be manually edited

### "Had a hiccup" messages
**Meaning:** Non-critical error, operation completed with issues
**Solution:** Usually safe to ignore, check logs if persistent

## Task Manager Issues

### Confusion about task workflow
**Remember the flow:**
- `pending` → tasks to do
- `verify` → awaiting verification
- `completed` → verified and archived

**Commands:**
1. `add_task()` creates pending
2. `submit_task()` moves to verify (requires evidence)
3. `complete_task()` verifies and archives

### Tasks not showing up
**Check filters:**
- `list_tasks()` shows active (pending + verify)
- `list_tasks("completed")` shows archived
- `list_tasks("detailed")` shows everything

## Performance Issues

### Slow responses
**Optimizations:**
1. Use grouped view: `list_tasks()` not `list_tasks("detailed")`
2. Clear old completed tasks (auto-cleaned after 30 days)
3. Weather cached for 10 minutes

### Token limit issues
**Solutions:**
1. Use default `list_tasks()` (90% reduction)
2. Limit recall results
3. Clean up old notes periodically

## Network Issues

### Weather not working
**Checks:**
1. Internet connection required
2. Open-Meteo API must be accessible
3. Falls back gracefully to "unavailable"

### Location detection fails
**Fallbacks:**
1. Returns "Location unknown"
2. Weather shows "Not available"
3. All other features work normally

## Update Issues

### Update script fails
**Manual update:**
1. Download from: https://github.com/QD25565/mcp-ai-foundation
2. Replace files in your installation
3. Keep your data directories

### Git errors during update
**Solution:**
1. Script will fallback to manual download
2. Or update manually via git:
```bash
git pull origin main
```

## Getting Help

### Diagnostic Information
When reporting issues, include:
1. Python version: `python --version`
2. OS: Windows/Mac/Linux
3. Claude Desktop version
4. Error messages
5. Config file (remove sensitive data)

### Support Channels
- GitHub Issues: https://github.com/QD25565/mcp-ai-foundation/issues
- Check existing issues first
- Include diagnostic information

## Prevention

### Best Practices
1. Regular backups of data directories
2. Test in non-critical environment first
3. Keep VERSION file updated
4. Document any local modifications
5. Update regularly for fixes

### Before Major Changes
1. Backup: `%APPDATA%\Claude\tools\`
2. Export important tasks/notes
3. Document current version
4. Test update on single tool first