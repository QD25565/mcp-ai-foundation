#!/usr/bin/env python3
"""
TASK MANAGER MCP v6.0 - SIMPLIFIED EDITION
=============================================
Your personal task tracker - now actually useful!
Simple 2-state workflow that matches how you actually work.

Task Lifecycle:
PENDING → COMPLETED
(to do)   (done with optional evidence)

Commands:
- add_task("description") → Creates pending task
- list_tasks() → Shows pending tasks
- list_tasks("completed") → Shows completed tasks
- list_tasks("all") → Shows everything
- complete_task(id, "evidence") → Complete with optional evidence
- delete_task(id) → Remove task
- task_stats() → Productivity insights
=============================================
"""

import json
import sys
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import random

# Version
VERSION = "6.0.0"

# Limits
MAX_TASK_LENGTH = 500  # Characters for task description

# Storage - organized under Claude/tools
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "task_manager_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "task_manager_data"

# Ensure directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "tasks.json"
ARCHIVE_FILE = DATA_DIR / "completed_tasks_archive.json"
ID_FILE = DATA_DIR / "last_id.json"

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global state
tasks = {}
completed_archive = []
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
last_task_id = 0

def load_last_id():
    """Load the last used task ID"""
    global last_task_id
    try:
        if ID_FILE.exists():
            with open(ID_FILE, 'r') as f:
                data = json.load(f)
                last_task_id = data.get("last_id", 0)
    except:
        last_task_id = random.randint(100, 999)

def save_last_id():
    """Save the last used task ID"""
    try:
        with open(ID_FILE, 'w') as f:
            json.dump({"last_id": last_task_id}, f)
    except:
        pass

def generate_task_id() -> int:
    """Generate a simple integer task ID"""
    global last_task_id
    last_task_id += 1
    save_last_id()
    return last_task_id

def format_time_smart(timestamp: str) -> str:
    """Clear but compact time formatting"""
    try:
        dt = datetime.fromisoformat(timestamp)
        now = datetime.now()
        delta = now - dt
        
        if delta.seconds < 3600 and delta.days == 0:
            mins = delta.seconds // 60
            if mins == 0:
                return "just now"
            elif mins == 1:
                return "1 min ago"
            else:
                return f"{mins} min ago"
        
        elif delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 1:
                return "1 hr ago"
            else:
                return f"{hours} hrs ago"
        
        elif delta.days < 7:
            if delta.days == 1:
                return "1 day ago"
            else:
                return f"{delta.days} days ago"
        
        else:
            return dt.strftime("%b %d")
    except:
        return "unknown"

def format_time_delta(start_time: str, end_time: str = None) -> str:
    """Format time difference for task completion"""
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time) if end_time else datetime.now()
        delta = end - start
        
        if delta.days > 0:
            return f"{delta.days} days"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hrs"
        elif delta.seconds > 60:
            mins = delta.seconds // 60
            return f"{mins} min"
        else:
            return "<1 min"
    except:
        return "unknown time"

def migrate_old_tasks():
    """Migrate tasks from old 3-state system to new 2-state system"""
    migrated_count = 0
    for tid, task in tasks.items():
        old_status = task.get("status", "pending")
        
        # Migration logic:
        # - "pending" stays "pending"
        # - "verify" becomes "pending" (wasn't truly completed)
        # - "completed" stays "completed"
        if old_status == "verify":
            task["status"] = "pending"
            task["migration_note"] = f"Migrated from verify status (had evidence: {task.get('evidence', 'none')})"
            migrated_count += 1
        elif old_status not in ["pending", "completed"]:
            task["status"] = "pending"
            migrated_count += 1
    
    if migrated_count > 0:
        logging.info(f"Migrated {migrated_count} tasks to new 2-state system")
    
    return migrated_count

def load_tasks():
    """Load existing tasks with migration"""
    global tasks, completed_archive
    load_last_id()
    
    try:
        if DATA_FILE.exists():
            logging.info(f"Loading tasks from {DATA_FILE}")
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    loaded_tasks = data.get("tasks", {})
                    tasks = {}
                    for tid, task in loaded_tasks.items():
                        if isinstance(tid, str) and tid.startswith('T'):
                            int_id = int(tid[1:])
                        else:
                            int_id = int(tid)
                        task["id"] = int_id
                        tasks[int_id] = task
                    
                    # Migrate old 3-state tasks to 2-state
                    migrate_old_tasks()
                    
                    # Clean up very old completed tasks (>30 days)
                    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                    tasks = {tid: task for tid, task in tasks.items() 
                            if task.get("status") != "completed" or 
                            task.get("completed_at", "") > cutoff}
                else:
                    tasks = {}
            logging.info(f"Loaded {len(tasks)} active tasks")
        
        # Load archive
        if ARCHIVE_FILE.exists():
            try:
                with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                    archive_data = json.load(f)
                    completed_archive = archive_data.get("archive", [])[-500:]
            except:
                completed_archive = []
    except Exception as e:
        logging.error(f"Error loading tasks: {e}")
        tasks = {}
        completed_archive = []

def save_tasks():
    """Save tasks persistently"""
    try:
        data = {
            "version": VERSION,
            "tasks": {str(k): v for k, v in tasks.items()},
            "last_save": datetime.now().isoformat(),
            "session": session_id
        }
        
        temp_file = DATA_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(DATA_FILE)
        
        if completed_archive:
            archive_data = {
                "version": VERSION,
                "archive": completed_archive[-500:],
                "last_save": datetime.now().isoformat()
            }
            archive_temp = ARCHIVE_FILE.with_suffix('.tmp')
            with open(archive_temp, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, indent=2, ensure_ascii=False)
            archive_temp.replace(ARCHIVE_FILE)
        
        return True
    except Exception as e:
        logging.error(f"Failed to save tasks: {e}")
        return False

def add_task(task: str = None, **kwargs) -> Dict:
    """Add a new task in pending status"""
    global tasks
    
    try:
        if task is None:
            task = kwargs.get('task') or kwargs.get('text') or kwargs.get('description') or \
                   kwargs.get('what') or kwargs.get('todo') or kwargs.get('content') or ""
        
        task = str(task).strip()
        
        if not task:
            return {
                "status": "error",
                "message": "Need a task description! Try: add_task('Review PR #123')"
            }
        
        if len(task) > MAX_TASK_LENGTH:
            task = task[:MAX_TASK_LENGTH]
            truncated = True
        else:
            truncated = False
        
        task_id = generate_task_id()
        
        # Detect priority from keywords
        priority = "Norm"
        task_lower = task.lower()
        if any(word in task_lower for word in ['urgent', 'asap', 'critical', 'important', 'high priority']):
            priority = "High"
        elif any(word in task_lower for word in ['low priority', 'whenever', 'maybe', 'someday']):
            priority = "Low"
        
        # Create task entry with PENDING status
        now = datetime.now()
        new_task = {
            "id": task_id,
            "task": task,
            "status": "pending",
            "priority": priority,
            "created_at": now.isoformat(),
            "created_session": session_id,
            "completed_at": None,
            "evidence": None,
            "time_to_complete": None
        }
        
        tasks[task_id] = new_task
        save_tasks()
        
        msg = f"Created task [{task_id}] {priority} - {task}"
        if truncated:
            msg += f" (truncated to {MAX_TASK_LENGTH} chars)"
        
        return {
            "status": "success",
            "message": msg,
            "task_id": task_id,
            "priority": priority
        }
        
    except Exception as e:
        logging.error(f"Error in add_task: {e}")
        return {
            "status": "error",
            "message": "Had trouble creating task, try again!"
        }

def list_tasks(filter_type: str = None, **kwargs) -> Dict:
    """List tasks with clear filtering"""
    global tasks
    
    try:
        if filter_type is None:
            filter_type = kwargs.get('filter') or kwargs.get('type') or kwargs.get('status') or "pending"
        
        filter_lower = str(filter_type).lower().strip()
        
        # Group tasks by status
        pending_tasks = []
        completed_tasks = []
        
        for tid, task in tasks.items():
            status = task.get("status", "pending")
            
            if status == "pending":
                pending_tasks.append(task)
            elif status == "completed":
                completed_tasks.append(task)
        
        # Sort by priority and age
        priority_order = {"High": 0, "Norm": 1, "Low": 2}
        pending_tasks.sort(key=lambda t: (
            priority_order.get(t.get("priority", "Norm"), 1),
            t.get("created_at", "")
        ))
        completed_tasks.sort(key=lambda t: t.get("completed_at", ""), reverse=True)
        
        # Determine what to show
        show_pending = False
        show_completed = False
        
        if filter_lower in ["pending", "todo", "open", "active", ""]:
            show_pending = True
            
        elif filter_lower in ["completed", "complete", "done", "finished"]:
            show_completed = True
            
        elif filter_lower in ["all", "everything", "both"]:
            show_pending = True
            show_completed = True
        
        # Build output
        task_lines = []
        total_shown = 0
        
        # Show pending tasks
        if show_pending and pending_tasks:
            task_lines.append(f"PENDING ({len(pending_tasks)} tasks):")
            
            # Group by priority
            high = [t for t in pending_tasks if t.get("priority") == "High"]
            normal = [t for t in pending_tasks if t.get("priority") == "Norm"]
            low = [t for t in pending_tasks if t.get("priority") == "Low"]
            
            if high:
                task_lines.append(f"  High priority [{len(high)}]:")
                for t in high[:10]:  # Show first 10
                    time_str = format_time_smart(t.get("created_at", ""))
                    task_lines.append(f"    [{t['id']}] {t['task'][:100]} ({time_str})")
                if len(high) > 10:
                    task_lines.append(f"    ... and {len(high) - 10} more")
            
            if normal:
                task_lines.append(f"  Normal priority [{len(normal)}]:")
                for t in normal[:10]:  # Show first 10
                    time_str = format_time_smart(t.get("created_at", ""))
                    task_lines.append(f"    [{t['id']}] {t['task'][:100]} ({time_str})")
                if len(normal) > 10:
                    task_lines.append(f"    ... and {len(normal) - 10} more")
            
            if low:
                task_lines.append(f"  Low priority [{len(low)}]:")
                for t in low[:5]:  # Show first 5
                    time_str = format_time_smart(t.get("created_at", ""))
                    task_lines.append(f"    [{t['id']}] {t['task'][:100]} ({time_str})")
                if len(low) > 5:
                    task_lines.append(f"    ... and {len(low) - 5} more")
            
            total_shown += len(pending_tasks)
        
        # Show completed tasks
        if show_completed and completed_tasks:
            if task_lines:
                task_lines.append("")
            task_lines.append(f"COMPLETED ({len(completed_tasks)} tasks):")
            
            # Show recent completions
            for t in completed_tasks[:10]:
                time_str = format_time_smart(t.get("completed_at", ""))
                evidence = f" - {t['evidence'][:50]}" if t.get("evidence") else ""
                task_lines.append(f"    [{t['id']}] {t['task'][:80]}{evidence} ({time_str})")
            
            if len(completed_tasks) > 10:
                task_lines.append(f"    ... and {len(completed_tasks) - 10} more")
            
            total_shown += len(completed_tasks)
        
        # Build summary
        summary_parts = []
        if show_pending:
            summary_parts.append(f"{len(pending_tasks)} pending")
        if show_completed:
            summary_parts.append(f"{len(completed_tasks)} completed")
        
        if not summary_parts:
            summary = f"No {filter_lower} tasks"
        else:
            summary = " | ".join(summary_parts)
        
        # Handle empty results
        if total_shown == 0:
            tip = "Create one with: add_task('your task')"
            if filter_lower == "completed":
                tip = "Complete tasks with: complete_task(id)"
            
            return {
                "status": "success",
                "filter": filter_lower,
                "count": 0,
                "message": summary,
                "tasks": [],
                "tip": tip
            }
        
        result = {
            "status": "success",
            "filter": filter_lower,
            "count": total_shown,
            "message": summary,
            "tasks": task_lines
        }
        
        return result
        
    except Exception as e:
        logging.error(f"Error in list_tasks: {e}")
        return {
            "status": "error",
            "message": "Had trouble listing tasks",
            "tasks": []
        }

def complete_task(task_id: str = None, evidence: str = None, **kwargs) -> Dict:
    """Complete a task with optional evidence"""
    global tasks, completed_archive
    
    try:
        if task_id is None:
            task_id = kwargs.get('task_id') or kwargs.get('id') or kwargs.get('tid') or ""
        
        if evidence is None:
            evidence = kwargs.get('evidence') or kwargs.get('proof') or kwargs.get('notes') or \
                      kwargs.get('details') or kwargs.get('how') or ""
        
        task_id = str(task_id).strip()
        evidence = str(evidence).strip() if evidence else None
        
        # Convert to integer
        try:
            if task_id.startswith('T'):
                task_id = int(task_id[1:])
            else:
                task_id = int(task_id)
        except:
            return {
                "status": "error",
                "message": f"Invalid task ID: '{task_id}'"
            }
        
        # Find task
        if task_id not in tasks:
            pending = [t['id'] for t in tasks.values() if t.get("status") == "pending"][:5]
            return {
                "status": "error",
                "message": f"Task {task_id} not found",
                "available": pending if pending else ["No pending tasks"]
            }
        
        found_task = tasks[task_id]
        
        # Check if already completed
        if found_task.get("status") == "completed":
            return {
                "status": "info",
                "message": f"Task [{task_id}] already completed",
                "task": found_task["task"]
            }
        
        # Complete the task
        now = datetime.now()
        found_task["status"] = "completed"
        found_task["completed_at"] = now.isoformat()
        found_task["evidence"] = evidence if evidence else None
        
        # Calculate time to complete
        created_at = found_task.get("created_at", now.isoformat())
        found_task["time_to_complete"] = format_time_delta(created_at, now.isoformat())
        
        # Add to archive
        archive_entry = {
            "task_id": task_id,
            "task": found_task["task"],
            "priority": found_task.get("priority"),
            "created": found_task.get("created_at"),
            "completed": found_task["completed_at"],
            "evidence": found_task.get("evidence"),
            "time_to_complete": found_task["time_to_complete"]
        }
        completed_archive.append(archive_entry)
        
        save_tasks()
        
        msg = f"Completed [{task_id}] in {found_task['time_to_complete']}"
        if evidence:
            msg += f" - {evidence[:100]}"
        
        return {
            "status": "success",
            "message": msg,
            "task": found_task["task"],
            "time": found_task["time_to_complete"]
        }
        
    except Exception as e:
        logging.error(f"Error in complete_task: {e}")
        return {
            "status": "error",
            "message": "Had trouble completing task"
        }

def delete_task(task_id: str = None, **kwargs) -> Dict:
    """Delete a task"""
    global tasks
    
    try:
        if task_id is None:
            task_id = kwargs.get('task_id') or kwargs.get('id') or kwargs.get('tid') or ""
        
        task_id = str(task_id).strip()
        
        try:
            if task_id.startswith('T'):
                task_id = int(task_id[1:])
            else:
                task_id = int(task_id)
        except:
            return {
                "status": "error",
                "message": f"Invalid task ID: '{task_id}'"
            }
        
        if task_id not in tasks:
            return {
                "status": "error",
                "message": f"Task {task_id} not found"
            }
        
        found_task = tasks[task_id]
        status = found_task.get("status")
        
        deleted = tasks.pop(task_id)
        save_tasks()
        
        return {
            "status": "success",
            "message": f"Deleted [{task_id}] (was {status})",
            "task": deleted["task"]
        }
        
    except Exception as e:
        logging.error(f"Error in delete_task: {e}")
        return {
            "status": "error",
            "message": "Had trouble deleting task"
        }

def task_stats(**kwargs) -> Dict:
    """Get task statistics and insights"""
    global tasks, completed_archive
    
    try:
        # Count by status
        pending = [t for t in tasks.values() if t.get("status") == "pending"]
        completed = [t for t in tasks.values() if t.get("status") == "completed"]
        
        # Time analysis
        now = datetime.now()
        today = now.date()
        week_ago = (now - timedelta(days=7)).isoformat()
        
        # Tasks created today
        created_today = [t for t in tasks.values() 
                        if t.get("created_at", "")[:10] == str(today)]
        
        # Tasks completed this week
        completed_this_week = [t for t in tasks.values() 
                              if t.get("status") == "completed" and
                              t.get("completed_at", "") > week_ago]
        
        # Build insights
        insights = []
        
        # Pending breakdown
        if pending:
            high_priority = [t for t in pending if t.get("priority") == "High"]
            if high_priority:
                oldest_high = min(high_priority, key=lambda t: t.get("created_at", ""))
                age = format_time_smart(oldest_high["created_at"])
                insights.append(f"{len(high_priority)} high-priority tasks (oldest: {age})")
            
            insights.append(f"{len(pending)} tasks pending")
        
        # Productivity
        if created_today:
            insights.append(f"Created {len(created_today)} today")
        
        if completed_this_week:
            insights.append(f"Completed {len(completed_this_week)} this week")
        
        # Archive
        if completed_archive:
            insights.append(f"{len(completed_archive)} tasks in archive")
        
        # Average completion time for recent tasks
        recent_completed = [t for t in completed[:10] if t.get("time_to_complete")]
        if recent_completed:
            insights.append(f"Recent completion times: {recent_completed[0].get('time_to_complete', 'unknown')}")
        
        # Stats line
        stats_line = f"Pending: {len(pending)} | Completed: {len(completed) + len(completed_archive)}"
        
        return {
            "status": "success",
            "message": stats_line,
            "insights": insights if insights else ["No tasks yet - start with add_task()"],
            "stats": {
                "pending": len(pending),
                "completed": len(completed),
                "archived": len(completed_archive),
                "today": len(created_today),
                "this_week": len(completed_this_week)
            }
        }
        
    except Exception as e:
        logging.error(f"Error in task_stats: {e}")
        return {
            "status": "success",
            "message": "Stats unavailable",
            "insights": []
        }

# Initialize on import
load_tasks()

# Tool handler for MCP protocol
def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with proper MCP tool name handling"""
    
    tool_name = params.get("name", "")
    tool_args = params.get("arguments", {})
    
    # Map MCP tool names to functions
    tool_map = {
        "add_task": add_task,
        "list_tasks": list_tasks,
        "complete_task": complete_task,
        "delete_task": delete_task,
        "task_stats": task_stats
    }
    
    func = tool_map.get(tool_name)
    
    if func:
        result = func(**tool_args)
    else:
        result = list_tasks()
    
    # Format response for MCP
    text_parts = []
    
    if "message" in result:
        text_parts.append(result["message"])
    
    if "note" in result:
        text_parts.append(result["note"])
    
    for key in ["tasks", "insights", "available"]:
        if key in result and isinstance(result[key], list) and result[key]:
            if key == "tasks":
                text_parts.extend(result["tasks"])
            else:
                text_parts.extend(result[key])
    
    for key in ["task", "evidence", "tip", "time"]:
        if key in result and result[key]:
            if key == "tip":
                text_parts.append(f"{result[key]}")
            else:
                text_parts.append(result[key])
    
    text_response = "\n".join(text_parts) if text_parts else "Ready!"
    
    return {
        "content": [{
            "type": "text",
            "text": text_response
        }]
    }

# Main server loop
def main():
    """MCP server - handles JSON-RPC for task management"""
    
    logging.info(f"Task Manager MCP v{VERSION} starting...")
    logging.info(f"Data location: {DATA_FILE}")
    
    load_tasks()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
            except:
                continue
            
            request_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})
            
            response = {"jsonrpc": "2.0", "id": request_id}
            
            if method == "initialize":
                response["result"] = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "task_manager",
                        "version": VERSION,
                        "description": "Simple, effective task tracking for AIs"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "add_task",
                            "description": "Create a new task",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": {
                                        "type": "string",
                                        "description": "The task description"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "list_tasks",
                            "description": "List tasks (default: pending, use 'completed' or 'all')",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "filter": {
                                        "type": "string",
                                        "description": "Filter: pending (default), completed, or all"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "complete_task",
                            "description": "Complete a task with optional evidence",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {
                                        "type": "string",
                                        "description": "The task ID to complete"
                                    },
                                    "evidence": {
                                        "type": "string",
                                        "description": "Optional evidence or notes about completion"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "delete_task",
                            "description": "Delete a task",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {
                                        "type": "string",
                                        "description": "The task ID to delete"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "task_stats",
                            "description": "Get task statistics and insights",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": True
                            }
                        }
                    ]
                }
            
            elif method == "tools/call":
                result = handle_tools_call(params)
                response["result"] = result
            
            else:
                response["result"] = {
                    "status": "success",
                    "message": "Task Manager ready!"
                }
            
            if "result" in response or "error" in response:
                print(json.dumps(response), flush=True)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Server loop error: {e}", exc_info=True)
            continue
    
    save_tasks()
    logging.info("Task Manager MCP shutting down, tasks saved")

if __name__ == "__main__":
    main()