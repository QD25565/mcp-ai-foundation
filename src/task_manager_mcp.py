#!/usr/bin/env python3
"""
TASK MANAGER MCP v1.0.0 - TOKEN OPTIMIZED
=========================================
Persistent AI identity.
Simple 2-state workflow: PENDING → COMPLETED

Commands:
- add_task("description") → Creates pending task
- list_tasks() → Shows pending tasks  
- list_tasks("completed") → Shows completed tasks
- list_tasks("all") → Shows everything
- complete_task(id, "evidence") → Complete with optional evidence
- delete_task(id) → Remove task
- task_stats() → Productivity insights
=========================================
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import random

# Version
VERSION = "1.0.0"

# Limits
MAX_TASK_LENGTH = 500
MAX_EVIDENCE_LENGTH = 200

# Storage
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "task_manager_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "task_manager_data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "tasks.json"
ARCHIVE_FILE = DATA_DIR / "completed_archive.json"
ID_FILE = DATA_DIR / "last_id.json"

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global state
tasks = {}
completed_archive = []
last_task_id = 0

def get_persistent_id():
    """Get or create persistent AI identity - stored at script directory level"""
    # Get the directory where this script is located
    SCRIPT_DIR = Path(__file__).parent
    id_file = SCRIPT_DIR / "ai_identity.txt"
    
    if id_file.exists():
        try:
            with open(id_file, 'r') as f:
                stored_id = f.read().strip()
                if stored_id:
                    logging.info(f"Loaded persistent identity: {stored_id}")
                    return stored_id
        except Exception as e:
            logging.error(f"Error reading identity file: {e}")
    
    # Generate new ID - make it more readable
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    try:
        with open(id_file, 'w') as f:
            f.write(new_id)
        logging.info(f"Created new persistent identity: {new_id}")
    except Exception as e:
        logging.error(f"Error saving identity file: {e}")
    
    return new_id

# Get ID from environment or persistent storage
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

def format_time_contextual(timestamp: str, reference_time: datetime = None) -> str:
    """Ultra-compact contextual time format"""
    if not timestamp:
        return ""
    
    try:
        dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        ref = reference_time or datetime.now()
        delta = ref - dt
        
        # Less than an hour
        if delta.total_seconds() < 3600:
            mins = int(delta.total_seconds() / 60)
            if mins == 0:
                return "now"
            elif mins == 1:
                return "1m"
            else:
                return f"{mins}m"
        
        # Today - just time
        if dt.date() == ref.date():
            return dt.strftime("%H:%M")
        
        # Yesterday
        if delta.days == 1:
            return f"y{dt.strftime('%H:%M')}"
        
        # This week - days
        if delta.days < 7:
            return f"{delta.days}d"
        
        # This month
        if delta.days < 30:
            return dt.strftime("%m/%d")
        
        # Older
        return dt.strftime("%m/%d")
    except:
        return ""

def format_duration(start_time: str, end_time: str = None) -> str:
    """Format task completion duration compactly"""
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time) if end_time else datetime.now()
        delta = end - start
        
        if delta.days > 0:
            return f"{delta.days}d"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m"
        else:
            return "<1m"
    except:
        return ""

def smart_truncate(text: str, max_chars: int) -> str:
    """Truncate intelligently at word boundaries"""
    if len(text) <= max_chars:
        return text
    
    cutoff = text.rfind(' ', 0, max_chars - 3)
    if cutoff == -1 or cutoff < max_chars * 0.8:
        cutoff = max_chars - 3
    return text[:cutoff] + "..."

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

def load_tasks():
    """Load existing tasks with format migration"""
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
                        # Convert to integer ID
                        if isinstance(tid, str) and tid.startswith('T'):
                            int_id = int(tid[1:])
                        else:
                            int_id = int(tid)
                        
                        # Migrate to optimized format
                        optimized = {
                            "id": int_id,
                            "task": task.get("task", ""),
                            "created": task.get("created_at", task.get("created", "")),
                            "created_by": task.get("created_by", task.get("author", "")),  # Include author
                        }
                        
                        # Only add priority if not normal
                        priority = task.get("priority", "Norm")
                        if priority != "Norm":
                            optimized["pri"] = "!" if priority == "High" else "↓"
                        
                        # If completed, add completion fields
                        if task.get("status") == "completed" or task.get("completed_at"):
                            optimized["completed"] = task.get("completed_at", task.get("completed", ""))
                            optimized["completed_by"] = task.get("completed_by", "")
                            if task.get("evidence"):
                                optimized["evidence"] = task.get("evidence")
                        
                        tasks[int_id] = optimized
                    
                    # Clean up very old completed tasks (>30 days)
                    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                    tasks = {tid: task for tid, task in tasks.items() 
                            if not task.get("completed") or task.get("completed") > cutoff}
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
    """Save tasks with optimized format"""
    try:
        data = {
            "v": VERSION,
            "tasks": {str(k): v for k, v in tasks.items()},
            "saved": datetime.now().isoformat()
        }
        
        temp_file = DATA_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
        temp_file.replace(DATA_FILE)
        
        if completed_archive:
            archive_data = {
                "v": VERSION,
                "archive": completed_archive[-500:],
                "saved": datetime.now().isoformat()
            }
            archive_temp = ARCHIVE_FILE.with_suffix('.tmp')
            with open(archive_temp, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, separators=(',', ':'), ensure_ascii=False)
            archive_temp.replace(ARCHIVE_FILE)
        
        return True
    except Exception as e:
        logging.error(f"Failed to save tasks: {e}")
        return False

def add_task(task: str = None, **kwargs) -> Dict:
    """Add a new task"""
    global tasks
    
    try:
        if task is None:
            task = kwargs.get('task') or kwargs.get('text') or kwargs.get('description') or ""
        
        task = str(task).strip()
        
        if not task:
            return {"msg": "Need task description!"}
        
        # Truncate if needed
        if len(task) > MAX_TASK_LENGTH:
            task = smart_truncate(task, MAX_TASK_LENGTH)
        
        task_id = generate_task_id()
        
        # Detect priority from keywords
        task_lower = task.lower()
        priority = None
        if any(word in task_lower for word in ['urgent', 'asap', 'critical', 'important', 'high priority']):
            priority = "!"
        elif any(word in task_lower for word in ['low priority', 'whenever', 'maybe', 'someday']):
            priority = "↓"
        
        # Create compact task with creator identity
        new_task = {
            "id": task_id,
            "task": task,
            "created": datetime.now().isoformat(),
            "created_by": CURRENT_AI_ID  # Track who created it
        }
        
        # Only add priority if not normal
        if priority:
            new_task["pri"] = priority
        
        tasks[task_id] = new_task
        save_tasks()
        
        # Compact response
        priority_str = priority if priority else ""
        return {"msg": f"[{task_id}]{priority_str} {smart_truncate(task, 80)} (by {CURRENT_AI_ID})"}
        
    except Exception as e:
        logging.error(f"Error in add_task: {e}")
        return {"msg": "Failed to add task"}

def list_tasks(filter_type: str = None, **kwargs) -> Dict:
    """List tasks efficiently"""
    global tasks
    
    try:
        if filter_type is None:
            filter_type = kwargs.get('filter') or kwargs.get('type') or "pending"
        
        filter_lower = str(filter_type).lower().strip()
        
        # Group tasks
        pending_tasks = []
        completed_tasks = []
        
        for tid, task in tasks.items():
            if task.get("completed"):
                completed_tasks.append(task)
            else:
                pending_tasks.append(task)
        
        # Sort efficiently
        pending_tasks.sort(key=lambda t: (
            0 if t.get("pri") == "!" else (2 if t.get("pri") == "↓" else 1),
            t.get("created", "")
        ))
        completed_tasks.sort(key=lambda t: t.get("completed", ""), reverse=True)
        
        # Determine what to show
        show_pending = filter_lower in ["pending", "todo", "open", "active", ""]
        show_completed = filter_lower in ["completed", "complete", "done", "finished"]
        
        if filter_lower in ["all", "everything", "both"]:
            show_pending = True
            show_completed = True
        
        # Build output
        lines = []
        
        # Pending tasks - compact format
        if show_pending and pending_tasks:
            # Group by priority
            high = [t for t in pending_tasks if t.get("pri") == "!"]
            normal = [t for t in pending_tasks if not t.get("pri")]
            low = [t for t in pending_tasks if t.get("pri") == "↓"]
            
            # Header only if multiple types
            if show_completed:
                lines.append(f"PENDING[{len(pending_tasks)}]:")
            
            # High priority
            for t in high[:10]:
                time_str = format_time_contextual(t.get("created", ""))
                task_text = smart_truncate(t['task'], 100)
                creator = t.get('created_by', '')
                creator_str = f" @{creator}" if creator and creator != CURRENT_AI_ID else ""
                lines.append(f"[{t['id']}]! {task_text}{creator_str} {time_str}")
            if len(high) > 10:
                lines.append(f"+{len(high)-10} more high")
            
            # Normal priority
            for t in normal[:10]:
                time_str = format_time_contextual(t.get("created", ""))
                task_text = smart_truncate(t['task'], 100)
                creator = t.get('created_by', '')
                creator_str = f" @{creator}" if creator and creator != CURRENT_AI_ID else ""
                lines.append(f"[{t['id']}] {task_text}{creator_str} {time_str}")
            if len(normal) > 10:
                lines.append(f"+{len(normal)-10} more")
            
            # Low priority
            for t in low[:5]:
                time_str = format_time_contextual(t.get("created", ""))
                task_text = smart_truncate(t['task'], 100)
                creator = t.get('created_by', '')
                creator_str = f" @{creator}" if creator and creator != CURRENT_AI_ID else ""
                lines.append(f"[{t['id']}]↓ {task_text}{creator_str} {time_str}")
            if len(low) > 5:
                lines.append(f"+{len(low)-5} more low")
        
        # Completed tasks - ultra compact
        if show_completed and completed_tasks:
            if lines:
                lines.append("")  # Separator
            
            if show_pending:
                lines.append(f"COMPLETED[{len(completed_tasks)}]:")
            
            for t in completed_tasks[:10]:
                time_str = format_time_contextual(t.get("completed", ""))
                duration = format_duration(t.get("created"), t.get("completed"))
                task_text = smart_truncate(t['task'], 60)
                
                # Show who completed it
                completer = t.get('completed_by', '')
                completer_str = f" by {completer}" if completer and completer != CURRENT_AI_ID else ""
                
                # Only show evidence if it exists
                evidence = ""
                if t.get("evidence"):
                    evidence = f" - {smart_truncate(t['evidence'], 40)}"
                
                lines.append(f"[{t['id']}]✔ {task_text}{evidence}{completer_str} {time_str}({duration})")
            
            if len(completed_tasks) > 10:
                lines.append(f"+{len(completed_tasks)-10} more completed")
        
        # Empty state
        if not lines:
            if filter_lower == "completed":
                return {"msg": "No completed tasks", "tip": "complete_task(id)"}
            else:
                return {"msg": "No pending tasks", "tip": "add_task('description')"}
        
        # Summary header with identity
        summary_parts = [f"ID:{CURRENT_AI_ID}"]
        if show_pending:
            summary_parts.append(f"{len(pending_tasks)} pending")
        if show_completed:
            summary_parts.append(f"{len(completed_tasks)} done")
        
        return {
            "msg": " | ".join(summary_parts) if summary_parts else "",
            "tasks": lines
        }
        
    except Exception as e:
        logging.error(f"Error in list_tasks: {e}")
        return {"msg": "Failed to list tasks"}

def complete_task(task_id: str = None, evidence: str = None, **kwargs) -> Dict:
    """Complete a task with optional evidence"""
    global tasks, completed_archive
    
    try:
        if task_id is None:
            task_id = kwargs.get('task_id') or kwargs.get('id') or ""
        
        if evidence is None:
            evidence = kwargs.get('evidence') or kwargs.get('proof') or kwargs.get('notes') or ""
        
        task_id = str(task_id).strip()
        evidence = str(evidence).strip() if evidence else None
        
        # Convert to integer
        try:
            if task_id.startswith('T'):
                task_id = int(task_id[1:])
            else:
                task_id = int(task_id)
        except:
            return {"msg": f"Invalid ID: '{task_id}'"}
        
        if task_id not in tasks:
            pending = [t['id'] for t in tasks.values() if not t.get("completed")][:5]
            return {
                "msg": f"Task {task_id} not found",
                "available": [f"[{pid}]" for pid in pending] if pending else ["No pending tasks"]
            }
        
        task = tasks[task_id]
        
        # Check if already completed
        if task.get("completed"):
            return {"msg": f"[{task_id}] already completed @{format_time_contextual(task['completed'])}"}
        
        # Complete the task
        now = datetime.now()
        task["completed"] = now.isoformat()
        task["completed_by"] = CURRENT_AI_ID  # Track who completed it
        if evidence:
            task["evidence"] = smart_truncate(evidence, MAX_EVIDENCE_LENGTH)
        
        # Archive entry (compact)
        duration = format_duration(task.get("created"), now.isoformat())
        archive_entry = {
            "id": task_id,
            "task": task["task"][:100],
            "created": task.get("created"),
            "created_by": task.get("created_by", ""),
            "completed": task["completed"],
            "completed_by": CURRENT_AI_ID,
            "duration": duration
        }
        if evidence:
            archive_entry["evidence"] = task.get("evidence")
        completed_archive.append(archive_entry)
        
        save_tasks()
        
        # Response
        msg = f"[{task_id}]✔ by {CURRENT_AI_ID} in {duration}"
        if evidence:
            msg += f" - {smart_truncate(evidence, 50)}"
        
        return {"msg": msg}
        
    except Exception as e:
        logging.error(f"Error in complete_task: {e}")
        return {"msg": "Failed to complete task"}

def delete_task(task_id: str = None, **kwargs) -> Dict:
    """Delete a task"""
    global tasks
    
    try:
        if task_id is None:
            task_id = kwargs.get('task_id') or kwargs.get('id') or ""
        
        task_id = str(task_id).strip()
        
        try:
            if task_id.startswith('T'):
                task_id = int(task_id[1:])
            else:
                task_id = int(task_id)
        except:
            return {"msg": f"Invalid ID: '{task_id}'"}
        
        if task_id not in tasks:
            return {"msg": f"Task {task_id} not found"}
        
        task = tasks[task_id]
        status = "done" if task.get("completed") else "pending"
        
        deleted = tasks.pop(task_id)
        save_tasks()
        
        return {"msg": f"Deleted [{task_id}] ({status})"}
        
    except Exception as e:
        logging.error(f"Error in delete_task: {e}")
        return {"msg": "Failed to delete task"}

def task_stats(**kwargs) -> Dict:
    """Get compact task statistics"""
    global tasks, completed_archive
    
    try:
        # Count
        pending = [t for t in tasks.values() if not t.get("completed")]
        completed = [t for t in tasks.values() if t.get("completed")]
        
        # Count by creator
        my_pending = len([t for t in pending if t.get("created_by") == CURRENT_AI_ID])
        my_completed = len([t for t in completed if t.get("completed_by") == CURRENT_AI_ID])
        
        # Time analysis
        now = datetime.now()
        today_str = now.date().isoformat()
        week_ago = (now - timedelta(days=7)).isoformat()
        
        created_today = len([t for t in tasks.values() 
                            if t.get("created", "")[:10] == today_str])
        
        completed_this_week = len([t for t in tasks.values() 
                                  if t.get("completed", "") > week_ago])
        
        # Build insights
        insights = []
        
        # Identity
        insights.append(f"You: {CURRENT_AI_ID}")
        
        # Personal stats
        if my_pending > 0:
            insights.append(f"Your pending: {my_pending}")
        if my_completed > 0:
            insights.append(f"Your completed: {my_completed}")
        
        # Priorities
        high_count = len([t for t in pending if t.get("pri") == "!"])
        if high_count:
            oldest_high = min([t for t in pending if t.get("pri") == "!"], 
                            key=lambda t: t.get("created", ""))
            age = format_time_contextual(oldest_high["created"])
            insights.append(f"{high_count} high @{age}")
        
        # Activity
        if created_today:
            insights.append(f"{created_today} new today")
        
        if completed_this_week:
            insights.append(f"{completed_this_week} done/week")
        
        # Archive
        total_completed = len(completed) + len(completed_archive)
        if total_completed > len(completed):
            insights.append(f"{total_completed} total done")
        
        # Oldest pending
        if pending:
            oldest = min(pending, key=lambda t: t.get("created", ""))
            age = format_time_contextual(oldest["created"])
            insights.append(f"oldest @{age}")
        
        # Summary
        summary = f"P:{len(pending)} C:{len(completed)}"
        if completed_archive:
            summary += f" A:{len(completed_archive)}"
        
        return {
            "msg": summary,
            "stats": insights if insights else ["No tasks yet"]
        }
        
    except Exception as e:
        logging.error(f"Error in task_stats: {e}")
        return {"msg": "Stats unavailable"}

# Initialize on import
load_tasks()

# Tool handler for MCP protocol
def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with clean output"""
    
    tool_name = params.get("name", "")
    tool_args = params.get("arguments", {})
    
    # Map to functions
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
    
    # Format response - ultra clean
    text_parts = []
    
    # Primary message
    if "msg" in result:
        text_parts.append(result["msg"])
    
    # Tasks or stats
    if "tasks" in result:
        text_parts.extend(result["tasks"])
    elif "stats" in result:
        text_parts.extend(result["stats"])
    elif "available" in result:
        text_parts.append("Available: " + " ".join(result["available"]))
    
    # Tip
    if "tip" in result:
        text_parts.append(f"Tip: {result['tip']}")
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Ready"
        }]
    }

# Main server loop
def main():
    """MCP server - handles JSON-RPC for task management"""
    
    logging.info(f"Task Manager MCP v{VERSION} starting (optimized)...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
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
                        "description": "Optimized task tracking for AIs"
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
                response["result"] = {"status": "ready"}
            
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