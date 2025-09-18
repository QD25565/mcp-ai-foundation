#!/usr/bin/env python3
"""
Basic usage examples for MCP AI Foundation tools.
These examples show how an AI would use the tools.
"""

# Note: These are conceptual examples.
# In practice, AIs call these through the MCP protocol.

# NOTEBOOK USAGE
# ==============

# Start of session - check context
get_status()
# Returns: "Welcome back! Resuming from note #47 (2 hours ago)"

# Save important information
remember("User prefers TypeScript over JavaScript")
remember("Project uses Next.js 14 with App Router")
remember("API endpoint: https://api.example.com/v2")

# Search memories
recall("TypeScript")
# Returns: "[0047] User prefers TypeScript over JavaScript"

recall("API")
# Returns: "[0049] API endpoint: https://api.example.com/v2"

# WORLD USAGE
# ===========

# Get complete awareness
world()
# Returns:
# Thursday, September 18, 2025 at 02:45 PM
# Location: Melbourne, VIC, AU
# Weather: 18°C/64°F, Clear
# Wind: 12 km/h
# Timezone: Australia/Melbourne

# Just time/date
datetime()
# Returns:
# September 18, 2025 at 02:45 PM
# Date: 2025-09-18
# Time: 02:45:30 PM (14:45:30)
# Day: Thursday
# Unix: 1758189930
# ISO: 2025-09-18T14:45:30.123456

# Just weather
weather()
# Returns:
# Location: Melbourne, VIC, AU
# Temperature: 18°C / 64°F
# Conditions: Clear
# Wind: 12 km/h

# TASK MANAGER USAGE
# ==================

# Create tasks
add_task("Review PR #123")
# Returns: "Created pending task [542] High - Review PR #123"

add_task("Update documentation")
# Returns: "Created pending task [543] Norm - Update documentation"

# View active work
list_tasks()
# Returns:
# PENDING (2 total):
#   High priority [1]:
#     [542] Review PR #123 (5 min ago)
#   Normal priority [1]:
#     [543] Update documentation (2 min ago)

# Submit work with evidence
submit_task(542, "Reviewed PR #123, approved with 3 comments")
# Returns: "Submitted [542] for verification in 15 min"

# Complete and archive
complete_task(542)
# Returns: "Completed and archived [542]"

# Check productivity
task_stats()
# Returns:
# Pending: 1 | To verify: 0 | Completed: 1
# Insights:
# - 1 active tasks (1 pending, 0 to verify)
# - Created 2 today
# - Completed 1 this week