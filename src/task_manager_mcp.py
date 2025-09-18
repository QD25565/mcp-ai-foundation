#!/usr/bin/env python3
"""
TASK MANAGER MCP v5.0 - COHERENT EDITION
=============================================
Your personal task tracker with clear, intuitive workflow.
Every term matches its meaning. Every function does what it says.

Task Lifecycle:
PENDING → VERIFY → COMPLETED
(to do)   (awaiting verification)   (verified & archived)

Commands:
- add_task("description") → Creates pending task
- list_tasks() → Shows all active work (pending + verify)
- list_tasks("pending") → Only tasks to do
- list_tasks("verify") → Only tasks needing verification  
- list_tasks("completed") → Only completed/archived tasks
- list_tasks("detailed") → Tree view with full metadata
- submit_task(id, "evidence") → Submit task for verification
- complete_task(id) → Verify and complete (archives)
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
VERSION = "5.0.0"

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

def load_tasks():
    """Load existing tasks"""
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
            "status": "pending",  # Clear: this task is pending
            "priority": priority,
            "created_at": now.isoformat(),
            "created_session": session_id,
            "evidence": None,
            "submitted_at": None,
            "submitted_session": None,
            "completed_at": None,
            "completion_notes": None,
            "time_to_submit": None,
            "time_to_complete": None
        }
        
        tasks[task_id] = new_task
        save_tasks()
        
        msg = f"Created pending task [{task_id}] {priority} - {task}"
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
            "message": "Had a hiccup creating task, try again!"
        }

def list_tasks(filter_type: str = None, **kwargs) -> Dict:
    """List tasks with clear, intuitive filtering"""
    global tasks
    
    try:
        if filter_type is None:
            filter_type = kwargs.get('filter') or kwargs.get('type') or kwargs.get('status') or "active"
        
        filter_lower = str(filter_type).lower().strip()
        
        # Check if detailed mode requested
        detailed = filter_lower in ["detailed", "detail", "full", "verbose", "tree"]
        if detailed:
            actual_filter = kwargs.get('include', 'active')
            filter_lower = actual_filter.lower() if actual_filter else 'active'
        
        # Group tasks by status
        pending_tasks = []
        verify_tasks = []
        completed_tasks = []
        
        for tid, task in tasks.items():
            status = task.get("status", "pending")
            
            if status == "pending":
                pending_tasks.append(task)
            elif status == "verify":
                verify_tasks.append(task)
            elif status == "completed":
                completed_tasks.append(task)
        
        # Sort by priority and age
        priority_order = {"High": 0, "Norm": 1, "Low": 2}
        for task_list in [pending_tasks, verify_tasks, completed_tasks]:
            task_list.sort(key=lambda t: (
                priority_order.get(t.get("priority", "Norm"), 1),
                t.get("created_at", "")
            ))
        
        # Clear filter logic
        show_pending = False
        show_verify = False
        show_completed = False
        
        if filter_lower in ["active", "all", ""]:
            # Active work: pending + needs verification
            show_pending = True
            show_verify = True
            
        elif filter_lower in ["pending", "todo", "open"]:
            show_pending = True
            
        elif filter_lower in ["verify", "verification", "review", "submitted"]:
            show_verify = True
            
        elif filter_lower in ["completed", "complete", "archive", "archived", "done"]:
            show_completed = True
        
        # Build output
        task_lines = []
        total_shown = 0
        
        if detailed:
            # Detailed tree view
            all_tasks = []
            if show_pending:
                all_tasks.extend(pending_tasks)
            if show_verify:
                all_tasks.extend(verify_tasks)
            if show_completed:
                all_tasks.extend(completed_tasks)
            
            for task in all_tasks:
                tid = task.get("id", "?")
                task_text = task.get("task", "")
                priority = task.get("priority", "Norm")
                status = task.get("status", "pending")
                created = task.get("created_at", "")
                
                # Main line with clear status
                status_display = status.upper()
                task_lines.append(f"[{tid}] {priority}/{status_display}: {task_text}")
                
                # Details
                if created:
                    age = format_time_smart(created)
                    created_display = datetime.fromisoformat(created).strftime("%m/%d %H:%M")
                    task_lines.append(f"  Created: {created_display} ({age})")
                
                # Status-specific info
                if status == "verify":
                    if task.get("evidence"):
                        evidence_preview = str(task["evidence"])[:200]
                        task_lines.append(f"  Evidence: {evidence_preview}")
                    if task.get("time_to_submit"):
                        task_lines.append(f"  Time to submit: {task['time_to_submit']}")
                
                elif status == "completed":
                    if task.get("evidence"):
                        evidence_preview = str(task["evidence"])[:200]
                        task_lines.append(f"  Evidence: {evidence_preview}")
                    if task.get("time_to_complete"):
                        task_lines.append(f"  Total time: {task['time_to_complete']}")
                
                task_lines.append("")  # Empty line between tasks
                total_shown += 1
        
        else:
            # Optimized grouped view
            
            # Show pending tasks
            if show_pending and pending_tasks:
                task_lines.append(f"PENDING ({len(pending_tasks)} total):")
                
                # Group by priority
                high = [t for t in pending_tasks if t.get("priority") == "High"]
                normal = [t for t in pending_tasks if t.get("priority") == "Norm"]
                low = [t for t in pending_tasks if t.get("priority") == "Low"]
                
                if high:
                    task_lines.append(f"  High priority [{len(high)}]:")
                    for t in high:
                        time_str = format_time_smart(t.get("created_at", ""))
                        task_lines.append(f"    [{t['id']}] {t['task']} ({time_str})")
                
                if normal:
                    task_lines.append(f"  Normal priority [{len(normal)}]:")
                    for t in normal:
                        time_str = format_time_smart(t.get("created_at", ""))
                        task_lines.append(f"    [{t['id']}] {t['task']} ({time_str})")
                
                if low:
                    task_lines.append(f"  Low priority [{len(low)}]:")
                    for t in low:
                        time_str = format_time_smart(t.get("created_at", ""))
                        task_lines.append(f"    [{t['id']}] {t['task']} ({time_str})")
                
                total_shown += len(pending_tasks)
            
            # Show tasks needing verification
            if show_verify and verify_tasks:
                if task_lines:
                    task_lines.append("")
                task_lines.append(f"NEEDS VERIFICATION ({len(verify_tasks)} total):")
                task_lines.append(f"  IDs: [{','.join(str(t['id']) for t in verify_tasks)}]")
                
                task_lines.append("  First few tasks:")
                for t in verify_tasks[:5]:
                    task_lines.append(f"    {t['id']}: {t['task'][:100]}")
                
                if len(verify_tasks) > 5:
                    task_lines.append(f"  ... and {len(verify_tasks) - 5} more")
                
                total_shown += len(verify_tasks)
            
            # Show completed/archived tasks
            if show_completed and completed_tasks:
                if task_lines:
                    task_lines.append("")
                task_lines.append(f"COMPLETED/ARCHIVED ({len(completed_tasks)} total)")
                task_lines.append(f"  Recent IDs: [{','.join(str(t['id']) for t in completed_tasks[:10])}...]")
                
                task_lines.append("  Recent completions:")
                for t in completed_tasks[:3]:
                    task_lines.append(f"    {t['id']}: {t['task'][:80]}")
                
                total_shown += len(completed_tasks)
        
        # Build summary
        summary_parts = []
        if show_pending and pending_tasks:
            summary_parts.append(f"{len(pending_tasks)} pending")
        if show_verify and verify_tasks:
            summary_parts.append(f"{len(verify_tasks)} to verify")
        if show_completed and completed_tasks:
            summary_parts.append(f"{len(completed_tasks)} completed")
        
        if not summary_parts:
            summary = f"No {filter_lower} tasks"
        else:
            summary = " | ".join(summary_parts)
        
        # Handle empty results
        if total_shown == 0:
            tip = "Create one with: add_task('your task')"
            if filter_lower == "verify":
                tip = "Submit pending tasks with: submit_task(id, 'evidence')"
            elif filter_lower == "completed":
                tip = "Complete verified tasks with: complete_task(id)"
            
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
            "mode": "detailed" if detailed else "grouped",
            "count": total_shown,
            "message": summary,
            "tasks": task_lines
        }
        
        if not detailed and total_shown > 0:
            result["tip"] = "Use list_tasks('detailed') for full metadata"
        
        if filter_lower in ["active", "all"] and completed_tasks:
            result["note"] = f"{len(completed_tasks)} completed tasks hidden. Use list_tasks('completed') to see them."
        
        return result
        
    except Exception as e:
        logging.error(f"Error in list_tasks: {e}")
        return {
            "status": "error",
            "message": "Had trouble listing tasks",
            "tasks": []
        }

def submit_task(task_id: str = None, evidence: str = None, **kwargs) -> Dict:
    """Submit a task for verification (moves from pending to verify status)"""
    global tasks
    
    try:
        if task_id is None:
            task_id = kwargs.get('task_id') or kwargs.get('id') or kwargs.get('tid') or ""
        
        if evidence is None:
            evidence = kwargs.get('evidence') or kwargs.get('proof') or kwargs.get('verification') or \
                      kwargs.get('details') or kwargs.get('how') or kwargs.get('where') or ""
        
        task_id = str(task_id).strip()
        evidence = str(evidence).strip()
        
        # Convert to integer
        try:
            if task_id.startswith('T'):
                task_id = int(task_id[1:])
            else:
                task_id = int(task_id)
        except:
            return {
                "status": "error",
                "message": f"Invalid task ID: '{task_id}'",
                "tip": "Use just the number: submit_task(123, 'evidence')"
            }
        
        # Find task
        if task_id not in tasks:
            pending = [t['id'] for t in tasks.values() if t.get("status") == "pending"][:5]
            return {
                "status": "error",
                "message": f"Task {task_id} not found",
                "available": pending if pending else ["No pending tasks"],
                "tip": "Use list_tasks('pending') to see available tasks"
            }
        
        found_task = tasks[task_id]
        
        # Check status
        if found_task.get("status") == "verify":
            return {
                "status": "warning",
                "message": f"[{task_id}] already submitted for verification",
                "task": found_task["task"]
            }
        
        if found_task.get("status") == "completed":
            return {
                "status": "warning",
                "message": f"[{task_id}] already completed",
                "task": found_task["task"]
            }
        
        # Require evidence
        if not evidence:
            return {
                "status": "error",
                "message": f"Need evidence to submit [{task_id}]",
                "task": found_task["task"],
                "tip": f"submit_task({task_id}, 'What you did/where/how')"
            }
        
        # Update task to verify status
        now = datetime.now()
        found_task["status"] = "verify"
        found_task["evidence"] = evidence
        found_task["submitted_at"] = now.isoformat()
        found_task["submitted_session"] = session_id
        found_task["time_to_submit"] = format_time_delta(found_task["created_at"], now.isoformat())
        
        save_tasks()
        
        return {
            "status": "success",
            "message": f"Submitted [{task_id}] for verification in {found_task['time_to_submit']}",
            "task": found_task["task"],
            "evidence": evidence,
            "next": f"complete_task({task_id}) to verify and archive"
        }
        
    except Exception as e:
        logging.error(f"Error in submit_task: {e}")
        return {
            "status": "error",
            "message": "Had trouble submitting task"
        }

def complete_task(task_id: str = None, notes: str = None, **kwargs) -> Dict:
    """Complete a task (verify and archive it)"""
    global tasks, completed_archive
    
    try:
        if task_id is None:
            task_id = kwargs.get('task_id') or kwargs.get('id') or kwargs.get('tid') or ""
        
        if notes is None:
            notes = kwargs.get('notes') or kwargs.get('verification') or kwargs.get('check') or ""
        
        task_id = str(task_id).strip()
        notes = str(notes).strip() if notes else None
        
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
            to_verify = [t['id'] for t in tasks.values() if t.get("status") == "verify"][:5]
            return {
                "status": "error",
                "message": f"Task {task_id} not found",
                "to_verify": to_verify if to_verify else ["No tasks awaiting verification"]
            }
        
        found_task = tasks[task_id]
        
        # Check status
        if found_task.get("status") == "pending":
            return {
                "status": "error",
                "message": f"[{task_id}] still pending - submit it first!",
                "task": found_task["task"],
                "tip": f"Use submit_task({task_id}, 'evidence') first"
            }
        
        if found_task.get("status") == "completed":
            return {
                "status": "info",
                "message": f"[{task_id}] already completed",
                "task": found_task["task"]
            }
        
        # Complete the task (verify and archive)
        now = datetime.now()
        found_task["status"] = "completed"
        found_task["completed_at"] = now.isoformat()
        found_task["completion_notes"] = notes if notes else "Verified"
        
        # Calculate total time from creation to completion
        created_at = found_task.get("created_at", now.isoformat())
        found_task["time_to_complete"] = format_time_delta(created_at, now.isoformat())
        
        # Add to archive
        archive_entry = {
            "task_id": task_id,
            "task": found_task["task"],
            "priority": found_task.get("priority"),
            "created": found_task.get("created_at"),
            "submitted": found_task.get("submitted_at"),
            "completed": found_task["completed_at"],
            "evidence": found_task.get("evidence"),
            "time_to_submit": found_task.get("time_to_submit"),
            "time_to_complete": found_task["time_to_complete"]
        }
        completed_archive.append(archive_entry)
        
        save_tasks()
        
        return {
            "status": "success",
            "message": f"Completed and archived [{task_id}]",
            "task": found_task["task"],
            "total_time": found_task["time_to_complete"],
            "archived_count": len(completed_archive),
            "note": "Task completed and archived. Use list_tasks('completed') to see archived tasks."
        }
        
    except Exception as e:
        logging.error(f"Error in complete_task: {e}")
        return {
            "status": "error",
            "message": "Had trouble completing task"
        }

def delete_task(task_id: str = None, **kwargs) -> Dict:
    """Delete a task"""
    global tasks, completed_archive
    
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
        
        # Archive completed tasks, delete others
        if status == "completed":
            archive_entry = {
                "task_id": task_id,
                "task": found_task["task"],
                "status": status,
                "deleted_at": datetime.now().isoformat()
            }
            completed_archive.append(archive_entry)
            action = "archived (was completed)"
        else:
            action = f"deleted (was {status})"
        
        deleted = tasks.pop(task_id)
        save_tasks()
        
        return {
            "status": "success",
            "message": f"[{task_id}] {action}",
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
        verify = [t for t in tasks.values() if t.get("status") == "verify"]
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
        
        # Active work
        active_count = len(pending) + len(verify)
        if active_count > 0:
            insights.append(f"{active_count} active tasks ({len(pending)} pending, {len(verify)} to verify)")
        
        # Productivity
        if created_today:
            insights.append(f"Created {len(created_today)} today")
        
        if completed_this_week:
            insights.append(f"Completed {len(completed_this_week)} this week")
        
        # Priority breakdown for pending
        high_priority = [t for t in pending if t.get("priority") == "High"]
        if high_priority:
            oldest_high = min(high_priority, key=lambda t: t.get("created_at", ""))
            age = format_time_smart(oldest_high["created_at"])
            insights.append(f"{len(high_priority)} high-priority pending (oldest: {age})")
        
        # Archive
        if completed_archive:
            insights.append(f"{len(completed_archive)} tasks in archive")
        
        # Stats line
        stats_line = f"Pending: {len(pending)} | To verify: {len(verify)} | Completed: {len(completed) + len(completed_archive)}"
        
        return {
            "status": "success",
            "message": stats_line,
            "insights": insights if insights else ["No tasks yet - start with add_task()"],
            "stats": {
                "pending": len(pending),
                "to_verify": len(verify),
                "completed": len(completed),
                "archived": len(completed_archive),
                "today": len(created_today),
                "this_week": len(completed_this_week),
                "active_total": len(pending) + len(verify)
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
        "submit_task": submit_task,
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
    
    for key in ["tasks", "insights", "available", "to_verify"]:
        if key in result and isinstance(result[key], list) and result[key]:
            if key == "tasks":
                text_parts.extend(result["tasks"])
            else:
                text_parts.extend(result[key])
    
    for key in ["task", "evidence", "next", "tip"]:
        if key in result and result[key]:
            if key == "next":
                text_parts.append(f"Next: {result[key]}")
            elif key == "tip":
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
                        "description": "Clear, coherent task tracking for AIs"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "add_task",
                            "description": "Create a new pending task",
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
                            "description": "List tasks (default: active work, use 'completed' for archive)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "filter": {
                                        "type": "string",
                                        "description": "Filter: all/active, pending, verify, completed, detailed"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "submit_task",
                            "description": "Submit task for verification (pending → verify)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {
                                        "type": "string",
                                        "description": "The task ID to submit (just the number)"
                                    },
                                    "evidence": {
                                        "type": "string",
                                        "description": "Evidence/proof of work done (required)"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "complete_task",
                            "description": "Verify and complete task (verify → completed/archived)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {
                                        "type": "string",
                                        "description": "The task ID to complete"
                                    },
                                    "notes": {
                                        "type": "string",
                                        "description": "Verification notes (optional)"
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