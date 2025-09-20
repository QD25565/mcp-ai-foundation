#!/usr/bin/env python3
"""
Basic usage examples for MCP AI Foundation tools
"""

# Note: These are examples of how an AI would use the tools
# In actual usage, these are called through the MCP protocol

def notebook_examples():
    """Notebook usage examples"""
    
    # Check current context
    notebook.get_status()
    # Returns recent notes and current state
    
    # Save important information
    notebook.remember("User prefers Python 3.11")
    notebook.remember("Project database: PostgreSQL 15")
    notebook.remember("API endpoint: https://api.example.com/v2")
    
    # Search notes
    notebook.recall("database")
    # Returns notes mentioning 'database'
    
    # Get full content of a specific note
    notebook.get_full_note(123)
    # Returns complete text of note #123

def task_manager_examples():
    """Task Manager usage examples"""
    
    # Create tasks
    task_manager.add_task("Review pull request #456")
    task_manager.add_task("Update API documentation")
    
    # View tasks
    task_manager.list_tasks()  # Pending tasks
    task_manager.list_tasks("completed")  # Completed tasks
    task_manager.list_tasks("all")  # Everything
    
    # Complete a task
    task_manager.complete_task(1, "Merged PR #456")
    
    # Get insights
    task_manager.task_stats()
    # Returns productivity statistics

def teambook_examples():
    """Teambook usage examples"""
    
    # Share with team
    teambook.write("TODO: Deploy to staging server")
    teambook.write("DECISION: Use React for frontend")
    teambook.write("Meeting notes from standup", type="note")
    
    # View team activity
    teambook.read()  # Recent activity
    teambook.read(type="task", status="pending")  # Pending tasks
    teambook.read(query="deploy")  # Search for 'deploy'
    
    # Work on tasks
    teambook.claim(123)  # Claim task #123
    teambook.complete(123, "Deployed to staging.example.com")
    
    # Collaborate
    teambook.comment(123, "Should we run migrations first?")
    teambook.update(123, content="TODO: Deploy to staging (with migrations)")
    
    # Project management
    teambook.write("TODO: Fix auth bug", project="backend")
    teambook.read(project="frontend")
    teambook.projects()  # List all projects

def world_examples():
    """World usage examples"""
    
    # Get everything
    world.world()
    # Returns: date, time, weather, location, identity
    
    # Just date/time
    world.datetime()
    # Returns: formatted date and time
    
    # Weather and location
    world.weather()
    # Returns: weather conditions and location

def workflow_example():
    """Complete workflow example"""
    
    # Start of session
    notebook.get_status()
    task_manager.list_tasks()
    teambook.status()
    world.datetime()
    
    # During work
    notebook.remember("Working on authentication system")
    task_manager.add_task("Implement JWT refresh tokens")
    teambook.write("TODO: Security audit needed for auth system")
    
    # Claim team task
    teambook.claim(789)
    
    # Complete personal task
    task_manager.complete_task(456, "Implemented in auth.py")
    
    # Complete team task
    teambook.complete(789, "Audit complete - 3 issues found")
    
    # End of session
    notebook.remember("Session ended - auth system improved")

if __name__ == "__main__":
    print("MCP AI Foundation - Usage Examples")
    print("These examples show how an AI would use the tools.")
    print("In practice, these are called through the MCP protocol.")