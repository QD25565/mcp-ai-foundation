#!/usr/bin/env python3
"""
TASK MANAGER MCP v3.1.0 - INTEGRATED INTELLIGENCE
==================================================
Tasks that know about your notes, notes that know about your tasks.
70% fewer tokens. Natural time queries. Zero manual bridging.

NEW IN v3.1:
- Cross-tool auto-logging with notebook
- Time-based queries: list_tasks(when="yesterday")
- Smarter partial ID matching everywhere
- Reads task creation requests from notebook
- Auto-notes completions back to notebook

The evolution: Tools that work TOGETHER.
==================================================
"""

import json
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
import random
import re
import threading
import time

# Version
VERSION = "3.1.0"

# Configuration
OUTPUT_FORMAT = os.environ.get('TASKS_FORMAT', 'pipe')  # 'pipe' or 'json'

# Limits
MAX_TASK_LENGTH = 500
MAX_EVIDENCE_LENGTH = 200
BATCH_MAX = 50

# Storage
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "task_manager_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "task_manager_data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "tasks.db"
OLD_JSON_FILE = DATA_DIR / "tasks.json"
LAST_OP_FILE = DATA_DIR / ".last_task_operation"

# Cross-tool integration paths (shared with notebook)
NOTEBOOK_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "notebook_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    NOTEBOOK_DIR = Path(os.environ.get('TEMP', '/tmp')) / "notebook_data"

TASK_INTEGRATION_FILE = NOTEBOOK_DIR / ".task_integration"
NOTEBOOK_INTEGRATION_FILE = NOTEBOOK_DIR / ".notebook_integration"

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Operation memory
LAST_OPERATION = None

# Integration monitoring thread control
INTEGRATION_MONITOR_RUNNING = False
INTEGRATION_THREAD = None

def save_last_operation(op_type: str, result: Any):
    """Save last operation for chaining"""
    global LAST_OPERATION
    LAST_OPERATION = {
        'type': op_type, 
        'result': result, 
        'time': datetime.now()
    }
    try:
        with open(LAST_OP_FILE, 'w') as f:
            json.dump({
                'type': op_type, 
                'time': LAST_OPERATION['time'].isoformat()
            }, f)
    except:
        pass

def get_last_operation() -> Optional[Dict]:
    """Get last operation for context"""
    global LAST_OPERATION
    if LAST_OPERATION:
        return LAST_OPERATION
    try:
        if LAST_OP_FILE.exists():
            with open(LAST_OP_FILE, 'r') as f:
                data = json.load(f)
                return {
                    'type': data['type'], 
                    'time': datetime.fromisoformat(data['time'])
                }
    except:
        pass
    return None

def pipe_escape(text: str) -> str:
    """Escape pipes in text for pipe format"""
    return text.replace('|', '\\|')

def get_persistent_id():
    """Get or create persistent AI identity"""
    for location in [Path(__file__).parent, DATA_DIR, Path.home()]:
        id_file = location / "ai_identity.txt"
        if id_file.exists():
            try:
                with open(id_file, 'r') as f:
                    stored_id = f.read().strip()
                    if stored_id:
                        logging.info(f"Loaded identity from {location}: {stored_id}")
                        return stored_id
            except Exception as e:
                logging.error(f"Error reading identity from {location}: {e}")
    
    # Generate new ID
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    try:
        id_file = Path(__file__).parent / "ai_identity.txt"
        with open(id_file, 'w') as f:
            f.write(new_id)
        logging.info(f"Created new identity: {new_id}")
    except Exception as e:
        logging.error(f"Error saving identity: {e}")
    
    return new_id

# Get ID from environment or persistent storage
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

def init_db() -> sqlite3.Connection:
    """Initialize SQLite database"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Main tasks table - added source and source_id for integration
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            author TEXT NOT NULL,
            created TEXT NOT NULL,
            priority TEXT,
            completed_at TEXT,
            completed_by TEXT,
            evidence TEXT,
            linked_items TEXT,
            source TEXT,
            source_id TEXT
        )
    ''')
    
    # Full-text search
    conn.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts 
        USING fts5(task, content=tasks, content_rowid=id)
    ''')
    
    # Trigger to keep FTS in sync
    conn.execute('''
        CREATE TRIGGER IF NOT EXISTS tasks_ai 
        AFTER INSERT ON tasks BEGIN
            INSERT INTO tasks_fts(rowid, task) VALUES (new.id, new.task);
        END
    ''')
    
    # Stats table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            duration_ms INTEGER,
            author TEXT
        )
    ''')
    
    # Indices
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_author ON tasks(author)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_source ON tasks(source, source_id)')
    
    conn.commit()
    return conn

def migrate_from_json():
    """Migrate from JSON to SQLite if needed"""
    if not OLD_JSON_FILE.exists() or DB_FILE.exists():
        return
    
    logging.info("Migrating from JSON to SQLite...")
    try:
        with open(OLD_JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = init_db()
        tasks_data = data.get("tasks", {})
        
        for tid, task in tasks_data.items():
            task_id = int(tid) if tid.isdigit() else task.get("id", 0)
            
            conn.execute('''
                INSERT INTO tasks (id, task, author, created, priority, 
                                 completed_at, completed_by, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                task.get("task", ""),
                task.get("created_by", task.get("author", "Unknown")),
                task.get("created", datetime.now().isoformat()),
                task.get("pri"),
                task.get("completed"),
                task.get("completed_by"),
                task.get("evidence")
            ))
        
        conn.commit()
        conn.close()
        
        OLD_JSON_FILE.rename(OLD_JSON_FILE.with_suffix('.json.backup'))
        logging.info(f"Migrated {len(tasks_data)} tasks to SQLite")
        
    except Exception as e:
        logging.error(f"Migration failed: {e}")

def migrate_to_v31():
    """Add missing columns for v3.1"""
    try:
        conn = sqlite3.connect(str(DB_FILE))
        
        # Check existing columns
        cursor = conn.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add source column if missing
        if 'source' not in columns:
            logging.info("Adding source column for integration...")
            conn.execute('ALTER TABLE tasks ADD COLUMN source TEXT')
            conn.commit()
        
        # Add source_id column if missing
        if 'source_id' not in columns:
            logging.info("Adding source_id column for integration...")
            conn.execute('ALTER TABLE tasks ADD COLUMN source_id TEXT')
            conn.commit()
        
        conn.close()
    except Exception as e:
        logging.error(f"Migration error: {e}")

def parse_time_query(when: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse natural language time queries into date ranges"""
    if not when:
        return None, None
    
    when_lower = when.lower().strip()
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Time-based queries
    if when_lower == "today":
        return today_start, now
    
    elif when_lower == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start - timedelta(seconds=1)
        return yesterday_start, yesterday_end
    
    elif when_lower == "this week" or when_lower == "week":
        # Start from Monday
        days_since_monday = now.weekday()
        week_start = today_start - timedelta(days=days_since_monday)
        return week_start, now
    
    elif when_lower == "last week":
        days_since_monday = now.weekday()
        last_week_end = today_start - timedelta(days=days_since_monday)
        last_week_start = last_week_end - timedelta(days=7)
        return last_week_start, last_week_end
    
    elif when_lower == "morning":
        morning_start = today_start.replace(hour=6)
        morning_end = today_start.replace(hour=12)
        return morning_start, morning_end
    
    elif when_lower == "afternoon":
        afternoon_start = today_start.replace(hour=12)
        afternoon_end = today_start.replace(hour=18)
        return afternoon_start, afternoon_end
    
    elif when_lower == "evening":
        evening_start = today_start.replace(hour=18)
        evening_end = today_start.replace(hour=23, minute=59)
        return evening_start, evening_end
    
    elif when_lower == "last hour":
        hour_ago = now - timedelta(hours=1)
        return hour_ago, now
    
    elif when_lower.endswith(" hours ago"):
        try:
            hours = int(when_lower.split()[0])
            hours_ago = now - timedelta(hours=hours)
            return hours_ago, now
        except:
            pass
    
    elif when_lower.endswith(" days ago"):
        try:
            days = int(when_lower.split()[0])
            days_ago = now - timedelta(days=days)
            return days_ago, now
        except:
            pass
    
    return None, None

def format_time_contextual(timestamp: str) -> str:
    """Ultra-compact contextual time format"""
    if not timestamp:
        return ""
    
    try:
        dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        ref = datetime.now()
        delta = ref - dt
        
        if delta.total_seconds() < 60:
            return "now"
        elif delta.total_seconds() < 3600:
            return f"{int(delta.total_seconds()/60)}m"
        elif dt.date() == ref.date():
            return dt.strftime("%H:%M")
        elif delta.days == 1:
            return f"y{dt.strftime('%H:%M')}"
        elif delta.days < 7:
            return f"{delta.days}d"
        elif delta.days < 30:
            return dt.strftime("%m/%d")
        else:
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

def detect_priority(task: str) -> Optional[str]:
    """Detect priority from task content"""
    task_lower = task.lower()
    if any(word in task_lower for word in ['urgent', 'asap', 'critical', 'important', 'high priority', '!!!', 'now']):
        return "!"
    elif any(word in task_lower for word in ['low priority', 'whenever', 'maybe', 'someday', 'optional']):
        return "↓"
    return None

def find_task_smart(identifier: str, conn: sqlite3.Connection) -> Optional[int]:
    """Smart task resolution: exact ID → partial match → most recent"""
    identifier = str(identifier).strip()
    
    # Check for "last" keyword
    if identifier.lower() == "last":
        last_op = get_last_operation()
        if last_op and last_op['type'] == 'add_task':
            return last_op['result'].get('id')
        else:
            # Get most recent pending task
            result = conn.execute('''
                SELECT id FROM tasks 
                WHERE completed_at IS NULL 
                ORDER BY created DESC 
                LIMIT 1
            ''').fetchone()
            return result[0] if result else None
    
    # Clean ID - just numbers
    clean_id = re.sub(r'[^\d]', '', identifier)
    if clean_id:
        # Try exact match first
        try:
            task_id = int(clean_id)
            # Check if exists
            exists = conn.execute('SELECT id FROM tasks WHERE id = ?', (task_id,)).fetchone()
            if exists:
                return task_id
        except:
            pass
        
        # Try partial ID match (e.g., "23" finds task 234)
        try:
            result = conn.execute('''
                SELECT id FROM tasks 
                WHERE CAST(id AS TEXT) LIKE ? AND completed_at IS NULL
                ORDER BY id DESC 
                LIMIT 1
            ''', (f'%{clean_id}%',)).fetchone()
            if result:
                return result[0]
        except:
            pass
    
    # Try partial match on task content
    if len(identifier) >= 3:
        result = conn.execute('''
            SELECT id FROM tasks 
            WHERE task LIKE ? AND completed_at IS NULL 
            ORDER BY created DESC 
            LIMIT 1
        ''', (f'%{identifier}%',)).fetchone()
        if result:
            return result[0]
    
    return None

def log_operation(operation: str, duration_ms: int = None):
    """Log operation for stats"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.execute(
                'INSERT INTO stats (operation, timestamp, duration_ms, author) VALUES (?, ?, ?, ?)',
                (operation, datetime.now().isoformat(), duration_ms, CURRENT_AI_ID)
            )
    except:
        pass

def log_to_notebook(action: str, task_id: int, task_desc: str, evidence: str = None):
    """Log task actions to notebook integration file"""
    try:
        integration_data = {
            'source': 'task_manager',
            'source_id': task_id,
            'action': action,
            'task': task_desc[:200],
            'evidence': evidence[:200] if evidence else None,
            'created': datetime.now().isoformat()
        }
        
        # Append to integration file for notebook to pick up
        with open(NOTEBOOK_INTEGRATION_FILE, 'a') as f:
            f.write(json.dumps(integration_data) + '\n')
            
    except Exception as e:
        logging.debug(f"Could not log to notebook: {e}")
        # Silent fail - integration is optional

def monitor_task_integration():
    """Monitor integration file for tasks from notebook"""
    global INTEGRATION_MONITOR_RUNNING
    
    processed_lines = set()
    
    while INTEGRATION_MONITOR_RUNNING:
        try:
            if TASK_INTEGRATION_FILE.exists():
                with open(TASK_INTEGRATION_FILE, 'r') as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if not line or line in processed_lines:
                        continue
                    
                    processed_lines.add(line)
                    
                    try:
                        data = json.loads(line)
                        if data.get('action') == 'create_task' and data.get('source') == 'notebook':
                            # Create task from notebook
                            task_desc = data.get('task', 'Task from notebook')
                            source_id = data.get('source_id')
                            
                            with sqlite3.connect(str(DB_FILE)) as conn:
                                priority = detect_priority(task_desc)
                                cursor = conn.execute('''
                                    INSERT INTO tasks (task, author, created, priority, source, source_id)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (task_desc, CURRENT_AI_ID, datetime.now().isoformat(), 
                                     priority, 'notebook', source_id))
                                
                                task_id = cursor.lastrowid
                                logging.info(f"Created task {task_id} from notebook note {source_id}")
                                
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logging.debug(f"Error processing integration line: {e}")
        
        except Exception as e:
            logging.debug(f"Integration monitor error: {e}")
        
        time.sleep(5)  # Check every 5 seconds

def start_integration_monitor():
    """Start the integration monitoring thread"""
    global INTEGRATION_MONITOR_RUNNING, INTEGRATION_THREAD
    
    if not INTEGRATION_MONITOR_RUNNING:
        INTEGRATION_MONITOR_RUNNING = True
        INTEGRATION_THREAD = threading.Thread(target=monitor_task_integration, daemon=True)
        INTEGRATION_THREAD.start()
        logging.info("Started integration monitor")

def stop_integration_monitor():
    """Stop the integration monitoring thread"""
    global INTEGRATION_MONITOR_RUNNING, INTEGRATION_THREAD
    
    INTEGRATION_MONITOR_RUNNING = False
    if INTEGRATION_THREAD:
        INTEGRATION_THREAD.join(timeout=1)
        logging.info("Stopped integration monitor")

def add_task(task: str = None, linked_items: List[str] = None, **kwargs) -> Dict:
    """Add a new task with auto-priority detection"""
    try:
        start = datetime.now()
        
        if task is None:
            task = kwargs.get('task') or kwargs.get('text') or kwargs.get('description') or ""
        
        task = str(task).strip()
        
        if not task:
            return {"error": "Need task description"}
        
        # Truncate if needed
        if len(task) > MAX_TASK_LENGTH:
            task = smart_truncate(task, MAX_TASK_LENGTH)
        
        # Detect priority
        priority = detect_priority(task)
        
        # Store in database
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute('''
                INSERT INTO tasks (task, author, created, priority, linked_items, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (task, CURRENT_AI_ID, datetime.now().isoformat(), priority,
                  json.dumps(linked_items) if linked_items else None, 'manual'))
            task_id = cursor.lastrowid
        
        # Log to notebook
        log_to_notebook('task_created', task_id, task)
        
        # Save operation
        save_last_operation('add_task', {'id': task_id, 'task': task})
        
        # Log operation
        duration = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('add_task', duration)
        
        # Format response
        if OUTPUT_FORMAT == 'pipe':
            priority_str = priority if priority else ""
            result = f"{task_id}|now|{smart_truncate(task, 80)}{priority_str}"
            return {"added": result}
        else:
            return {
                "id": task_id,
                "task": smart_truncate(task, 80),
                "priority": priority
            }
        
    except Exception as e:
        logging.error(f"Error in add_task: {e}")
        return {"error": "Failed to add task"}

def list_tasks(filter_type: str = None, when: str = None, full: bool = False, **kwargs) -> Dict:
    """List tasks with time-based filtering"""
    try:
        start = datetime.now()
        
        if filter_type is None:
            filter_type = kwargs.get('filter') or kwargs.get('type') or "pending"
        
        filter_lower = str(filter_type).lower().strip()
        
        # Parse time query if provided
        if when:
            start_time, end_time = parse_time_query(when)
            if not start_time:
                return {"msg": f"Didn't understand time query: '{when}'"}
        else:
            start_time, end_time = None, None
        
        # Determine what to show
        show_pending = filter_lower in ["pending", "todo", "open", "active", ""]
        show_completed = filter_lower in ["completed", "complete", "done", "finished"]
        
        if filter_lower in ["all", "everything", "both"]:
            show_pending = True
            show_completed = True
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query based on filters
            if when:
                # Time-based query
                if show_pending and not show_completed:
                    cursor = conn.execute('''
                        SELECT * FROM tasks 
                        WHERE completed_at IS NULL 
                        AND created >= ? AND created <= ?
                        ORDER BY 
                            CASE WHEN priority = '!' THEN 0
                                 WHEN priority = '↓' THEN 2
                                 ELSE 1 END,
                            created DESC
                    ''', (start_time.isoformat(), end_time.isoformat()))
                elif show_completed and not show_pending:
                    cursor = conn.execute('''
                        SELECT * FROM tasks 
                        WHERE completed_at IS NOT NULL 
                        AND completed_at >= ? AND completed_at <= ?
                        ORDER BY completed_at DESC
                    ''', (start_time.isoformat(), end_time.isoformat()))
                else:  # all
                    cursor = conn.execute('''
                        SELECT * FROM tasks 
                        WHERE (created >= ? AND created <= ?)
                           OR (completed_at >= ? AND completed_at <= ?)
                        ORDER BY completed_at IS NULL DESC,
                            CASE WHEN priority = '!' THEN 0
                                 WHEN priority = '↓' THEN 2
                                 ELSE 1 END,
                            created DESC
                    ''', (start_time.isoformat(), end_time.isoformat(),
                          start_time.isoformat(), end_time.isoformat()))
            else:
                # Regular filtering
                if show_pending and not show_completed:
                    cursor = conn.execute('''
                        SELECT * FROM tasks 
                        WHERE completed_at IS NULL 
                        ORDER BY 
                            CASE WHEN priority = '!' THEN 0
                                 WHEN priority = '↓' THEN 2
                                 ELSE 1 END,
                            created DESC
                    ''')
                elif show_completed and not show_pending:
                    cursor = conn.execute('''
                        SELECT * FROM tasks 
                        WHERE completed_at IS NOT NULL 
                        ORDER BY completed_at DESC
                    ''')
                else:  # all
                    cursor = conn.execute('''
                        SELECT * FROM tasks 
                        ORDER BY completed_at IS NULL DESC,
                            CASE WHEN priority = '!' THEN 0
                                 WHEN priority = '↓' THEN 2
                                 ELSE 1 END,
                            created DESC
                    ''')
            
            tasks = cursor.fetchall()
        
        if not tasks:
            if when:
                return {"msg": f"No tasks {when}"}
            elif filter_lower == "completed":
                return {"msg": "No completed tasks"}
            else:
                return {"msg": "No pending tasks"}
        
        # Count tasks
        pending_tasks = [t for t in tasks if not t['completed_at']]
        completed_tasks = [t for t in tasks if t['completed_at']]
        
        # Format based on output format
        if OUTPUT_FORMAT == 'pipe' and not full:
            # Pipe format - ultra efficient
            lines = []
            
            # Summary line
            summary_parts = []
            if pending_tasks:
                high = sum(1 for t in pending_tasks if t['priority'] == '!')
                if high > 0:
                    summary_parts.append(f"{len(pending_tasks)}p({high}!)")
                else:
                    summary_parts.append(f"{len(pending_tasks)}p")
            if completed_tasks:
                summary_parts.append(f"{len(completed_tasks)}c")
            
            if summary_parts:
                lines.append('|'.join(summary_parts))
            
            # Task lines (limited)
            shown = 0
            for t in pending_tasks[:15]:
                parts = []
                parts.append(str(t['id']))
                parts.append(format_time_contextual(t['created']))
                parts.append(smart_truncate(t['task'], 80))
                if t['priority']:
                    parts.append(t['priority'])
                if t['source'] == 'notebook' and t['source_id']:
                    parts.append(f"n{t['source_id']}")
                lines.append('|'.join(pipe_escape(p) for p in parts))
                shown += 1
            
            if len(pending_tasks) > shown:
                lines.append(f"+{len(pending_tasks)-shown}")
            
            # Add some completed if showing all
            if show_completed and completed_tasks:
                for t in completed_tasks[:5]:
                    parts = []
                    parts.append(str(t['id']))
                    parts.append("✓")
                    parts.append(smart_truncate(t['task'], 60))
                    parts.append(format_time_contextual(t['completed_at']))
                    lines.append('|'.join(pipe_escape(p) for p in parts))
            
            return {"tasks": lines}
        
        elif full or OUTPUT_FORMAT == 'json':
            # JSON format or full mode
            formatted_tasks = []
            
            for t in tasks[:30]:  # Limit for sanity
                task_data = {
                    'id': t['id'],
                    'task': t['task'],
                    'created': format_time_contextual(t['created']),
                    'priority': t['priority'],
                    'status': 'done' if t['completed_at'] else 'pending'
                }
                
                if t['source'] == 'notebook' and t['source_id']:
                    task_data['from_note'] = t['source_id']
                
                if t['completed_at']:
                    task_data['completed'] = format_time_contextual(t['completed_at'])
                    task_data['duration'] = format_duration(t['created'], t['completed_at'])
                    if t['evidence']:
                        task_data['evidence'] = t['evidence']
                
                formatted_tasks.append(task_data)
            
            return {"tasks": formatted_tasks, "total": len(tasks)}
        
        else:
            # Summary mode (default for non-pipe)
            summary = f"{len(pending_tasks)} pending"
            if completed_tasks:
                summary += f" | {len(completed_tasks)} done"
            if when:
                summary += f" ({when})"
            return {"summary": summary}
        
    except Exception as e:
        logging.error(f"Error in list_tasks: {e}")
        return {"error": "Failed to list tasks"}

def complete_task(task_id: str = None, evidence: str = None, **kwargs) -> Dict:
    """Complete a task with smart ID resolution and notebook logging"""
    try:
        start = datetime.now()
        
        if task_id is None:
            task_id = kwargs.get('task_id') or kwargs.get('id') or ""
        
        if evidence is None:
            evidence = kwargs.get('evidence') or kwargs.get('proof') or kwargs.get('notes') or ""
        
        task_id = str(task_id).strip()
        evidence = str(evidence).strip() if evidence else None
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Smart resolution
            resolved_id = find_task_smart(task_id, conn)
            
            if not resolved_id:
                # Show available tasks
                pending = conn.execute(
                    'SELECT id, task FROM tasks WHERE completed_at IS NULL ORDER BY created DESC LIMIT 5'
                ).fetchall()
                
                if OUTPUT_FORMAT == 'pipe':
                    available = '|'.join([f"{p['id']}:{smart_truncate(p['task'], 20)}" for p in pending])
                    return {"error": f"Task not found", "available": available}
                else:
                    return {
                        "error": f"Task '{task_id}' not found",
                        "available": [{'id': p['id'], 'task': smart_truncate(p['task'], 30)} for p in pending]
                    }
            
            # Get task
            task = conn.execute('SELECT * FROM tasks WHERE id = ?', (resolved_id,)).fetchone()
            
            # Check if already completed
            if task['completed_at']:
                return {"error": f"Task {resolved_id} already completed"}
            
            # Complete the task
            now = datetime.now()
            if evidence and len(evidence) > MAX_EVIDENCE_LENGTH:
                evidence = smart_truncate(evidence, MAX_EVIDENCE_LENGTH)
            
            conn.execute('''
                UPDATE tasks 
                SET completed_at = ?, completed_by = ?, evidence = ?
                WHERE id = ?
            ''', (now.isoformat(), CURRENT_AI_ID, evidence, resolved_id))
            
            # Calculate duration
            duration = format_duration(task['created'], now.isoformat())
            
            # Log to notebook
            log_to_notebook('task_completed', resolved_id, task['task'], evidence)
        
        # Save operation
        save_last_operation('complete_task', {'id': resolved_id})
        
        # Log operation
        op_duration = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('complete_task', op_duration)
        
        # Response
        if OUTPUT_FORMAT == 'pipe':
            msg = f"{resolved_id}|✓|{duration}"
            if evidence:
                msg += f"|{smart_truncate(evidence, 50)}"
            return {"completed": msg}
        else:
            result = {
                "id": resolved_id,
                "status": "completed",
                "duration": duration
            }
            if evidence:
                result["evidence"] = evidence
            return result
        
    except Exception as e:
        logging.error(f"Error in complete_task: {e}")
        return {"error": "Failed to complete task"}

def delete_task(task_id: str = None, **kwargs) -> Dict:
    """Delete a task with smart resolution"""
    try:
        if task_id is None:
            task_id = kwargs.get('task_id') or kwargs.get('id') or ""
        
        task_id = str(task_id).strip()
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Smart resolution
            resolved_id = find_task_smart(task_id, conn)
            
            if not resolved_id:
                return {"error": f"Task not found: '{task_id}'"}
            
            # Get task for logging
            task = conn.execute(
                'SELECT * FROM tasks WHERE id = ?', 
                (resolved_id,)
            ).fetchone()
            
            status = "done" if task['completed_at'] else "pending"
            
            # Log deletion to notebook
            log_to_notebook('task_deleted', resolved_id, task['task'])
            
            # Delete task
            conn.execute('DELETE FROM tasks WHERE id = ?', (resolved_id,))
        
        if OUTPUT_FORMAT == 'pipe':
            return {"deleted": f"{resolved_id}|{status}"}
        else:
            return {"deleted": resolved_id, "was": status}
        
    except Exception as e:
        logging.error(f"Error in delete_task: {e}")
        return {"error": "Failed to delete task"}

def task_stats(full: bool = False, **kwargs) -> Dict:
    """Get task statistics - minimal by default"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            # Get stats
            stats = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN completed_at IS NULL THEN 1 END) as pending,
                    COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as completed,
                    COUNT(CASE WHEN priority = '!' AND completed_at IS NULL THEN 1 END) as high,
                    COUNT(CASE WHEN author = ? AND completed_at IS NULL THEN 1 END) as my_pending,
                    COUNT(CASE WHEN completed_by = ? THEN 1 END) as my_completed,
                    COUNT(CASE WHEN DATE(completed_at) = DATE('now') THEN 1 END) as completed_today,
                    COUNT(CASE WHEN source = 'notebook' THEN 1 END) as from_notebook
                FROM tasks
            ''', (CURRENT_AI_ID, CURRENT_AI_ID)).fetchone()
            
            # Get oldest pending
            oldest = conn.execute('''
                SELECT created FROM tasks 
                WHERE completed_at IS NULL 
                ORDER BY created 
                LIMIT 1
            ''').fetchone()
        
        if OUTPUT_FORMAT == 'pipe':
            # Pipe format stats
            parts = []
            parts.append(f"t:{stats[0]}")  # total
            parts.append(f"p:{stats[1]}")  # pending
            if stats[3] > 0:  # high priority
                parts.append(f"!:{stats[3]}")
            parts.append(f"c:{stats[2]}")  # completed
            if stats[6] > 0:  # completed today
                parts.append(f"today:{stats[6]}")
            if stats[7] > 0:  # from notebook
                parts.append(f"nb:{stats[7]}")
            if oldest:
                parts.append(f"oldest:{format_time_contextual(oldest[0])}")
            
            return {"stats": '|'.join(parts)}
        else:
            # JSON format
            result = {
                "total": stats[0],
                "pending": stats[1],
                "completed": stats[2]
            }
            
            if stats[3] > 0:
                result["high_priority"] = stats[3]
            if stats[6] > 0:
                result["completed_today"] = stats[6]
            if stats[7] > 0:
                result["from_notebook"] = stats[7]
            if oldest:
                result["oldest_pending"] = format_time_contextual(oldest[0])
            if stats[2] > 0:
                result["completion_rate"] = round((stats[2] / stats[0]) * 100)
            
            return result
        
    except Exception as e:
        logging.error(f"Error in task_stats: {e}")
        return {"error": "Stats unavailable"}

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
    """Execute multiple operations efficiently with aliases"""
    try:
        if operations is None:
            operations = kwargs.get('operations', [])
        
        if not operations:
            return {"error": "No operations provided"}
        
        if len(operations) > BATCH_MAX:
            return {"error": f"Too many operations (max {BATCH_MAX})"}
        
        results = []
        
        # Map operation types to functions with aliases
        op_map = {
            'add_task': add_task,
            'add': add_task,
            'a': add_task,
            'list_tasks': list_tasks,
            'list': list_tasks,
            'l': list_tasks,
            'complete_task': complete_task,
            'complete': complete_task,
            'c': complete_task,
            'done': complete_task,
            'delete_task': delete_task,
            'delete': delete_task,
            'd': delete_task,
            'task_stats': task_stats,
            'stats': task_stats,
            's': task_stats
        }
        
        for op in operations:
            op_type = op.get('type', '').lower()
            op_args = op.get('args', {})
            
            if op_type not in op_map:
                results.append({"error": f"Unknown operation: {op_type}"})
                continue
            
            # Execute operation
            result = op_map[op_type](**op_args)
            results.append(result)
        
        return {"batch_results": results, "count": len(results)}
        
    except Exception as e:
        logging.error(f"Error in batch: {e}")
        return {"error": f"Batch failed: {str(e)}"}

def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with minimal output"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})
    
    # Map to functions
    tool_map = {
        "add_task": add_task,
        "list_tasks": list_tasks,
        "complete_task": complete_task,
        "delete_task": delete_task,
        "task_stats": task_stats,
        "batch": batch
    }
    
    func = tool_map.get(tool_name)
    
    if func:
        result = func(**tool_args)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    # Format response minimally
    text_parts = []
    
    if "error" in result:
        text_parts.append(f"Error: {result['error']}")
        if "available" in result:
            if isinstance(result["available"], str):
                text_parts.append(f"Available: {result['available']}")
            else:
                text_parts.append(f"Available: {json.dumps(result['available'])}")
    elif "added" in result:
        text_parts.append(result["added"])
    elif "tasks" in result:
        if isinstance(result["tasks"], list):
            if OUTPUT_FORMAT == 'pipe':
                text_parts.extend(result["tasks"])
            else:
                text_parts.append(json.dumps(result["tasks"]))
        else:
            text_parts.append(result["tasks"])
    elif "completed" in result:
        text_parts.append(result["completed"])
    elif "deleted" in result:
        text_parts.append(result["deleted"])
    elif "stats" in result:
        text_parts.append(result["stats"])
    elif "summary" in result:
        text_parts.append(result["summary"])
    elif "msg" in result:
        text_parts.append(result["msg"])
    elif "batch_results" in result:
        text_parts.append(f"Batch: {result.get('count', 0)}")
        for r in result["batch_results"]:
            if isinstance(r, dict):
                if "error" in r:
                    text_parts.append(f"Error: {r['error']}")
                elif "added" in r:
                    text_parts.append(r["added"])
                elif "completed" in r:
                    text_parts.append(r["completed"])
                elif "deleted" in r:
                    text_parts.append(r["deleted"])
                else:
                    text_parts.append(json.dumps(r))
            else:
                text_parts.append(str(r))
    else:
        # Default to JSON for complex structures
        if OUTPUT_FORMAT == 'pipe' and isinstance(result, dict):
            # Try to format as pipe
            parts = [f"{k}:{v}" for k, v in result.items() if v is not None]
            text_parts.append('|'.join(pipe_escape(p) for p in parts))
        else:
            text_parts.append(json.dumps(result))
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Ready"
        }]
    }

# Initialize on import
migrate_from_json()
migrate_to_v31()
init_db()

# Start integration monitoring
start_integration_monitor()

def main():
    """MCP server - handles JSON-RPC for task management"""
    logging.info(f"Task Manager MCP v{VERSION} starting...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Database: {DB_FILE}")
    logging.info("v3.1 Integrated features:")
    logging.info(f"- Output format: {OUTPUT_FORMAT}")
    logging.info("- Cross-tool integration with notebook")
    logging.info("- Time-based queries (when='yesterday')")
    logging.info("- Enhanced smart ID resolution")
    logging.info("- Auto-logging to notebook")
    logging.info("- 70% token reduction in pipe mode")
    
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
                        "description": "Integrated tasks: cross-tool logging, time queries, 70% fewer tokens"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "add_task",
                            "description": "Create task (auto-logs to notebook)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": {
                                        "type": "string",
                                        "description": "The task description"
                                    },
                                    "linked_items": {
                                        "type": "array",
                                        "description": "Optional links to other tools"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "list_tasks",
                            "description": "List tasks (supports when='yesterday'/'today'/etc)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "filter": {
                                        "type": "string",
                                        "description": "Filter: pending (default), completed, or all"
                                    },
                                    "when": {
                                        "type": "string",
                                        "description": "Time query: today, yesterday, this week, morning, etc."
                                    },
                                    "full": {
                                        "type": "boolean",
                                        "description": "Show full details (default: false for summary)"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "complete_task",
                            "description": "Complete task (auto-logs to notebook, use 'last' for recent)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {
                                        "type": "string",
                                        "description": "Task ID, 'last', or partial match"
                                    },
                                    "evidence": {
                                        "type": "string",
                                        "description": "Optional evidence or notes"
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
                                        "description": "Task ID or partial match"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "task_stats",
                            "description": "Get task statistics",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "full": {
                                        "type": "boolean",
                                        "description": "Show full insights"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "batch",
                            "description": "Execute multiple operations",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "operations": {
                                        "type": "array",
                                        "description": "List of operations",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "description": "Operation type (add, complete, etc.)"
                                                },
                                                "args": {
                                                    "type": "object",
                                                    "description": "Arguments for the operation"
                                                }
                                            }
                                        }
                                    }
                                },
                                "required": ["operations"],
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
    
    # Clean shutdown
    stop_integration_monitor()
    logging.info("Task Manager MCP shutting down")

if __name__ == "__main__":
    main()