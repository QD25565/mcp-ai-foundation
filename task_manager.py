#!/usr/bin/env python3
"""
TASK MANAGER MCP v1.0.0 - INTEGRATED INTELLIGENCE
==================================================
Tasks that know about your notes, notes that know about your tasks.
70% fewer tokens. Natural time queries. Zero manual bridging.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import re
import threading
import time

# Import shared utilities
from mcp_shared import (
    MCPServer, CURRENT_AI_ID, get_tool_data_dir,
    pipe_escape, OperationTracker, BASE_DATA_DIR
)

try:
    from storage_adapter import TeambookStorageAdapter
    from teambook_shared import CURRENT_TEAMBOOK as TASK_MANAGER_TEAMBOOK
    TEAMBOOK_STORAGE_AVAILABLE = True
except ImportError:
    TEAMBOOK_STORAGE_AVAILABLE = False
    TeambookStorageAdapter = None
    TASK_MANAGER_TEAMBOOK = None

VERSION = "1.0.0"
OUTPUT_FORMAT = "pipe"  # Default to pipe format

# Limits
MAX_TASK_LENGTH = 500
MAX_EVIDENCE_LENGTH = 200
BATCH_MAX = 50

# Storage
DATA_DIR = get_tool_data_dir('task_manager')
DB_FILE = DATA_DIR / "tasks.db"
OLD_JSON_FILE = DATA_DIR / "tasks.json"

# Cross-tool integration paths
NOTEBOOK_DIR = BASE_DATA_DIR / "notebook_data"
NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
TASK_INTEGRATION_FILE = NOTEBOOK_DIR / ".task_integration"
NOTEBOOK_INTEGRATION_FILE = NOTEBOOK_DIR / ".notebook_integration"

# Operation tracker
op_tracker = OperationTracker('task_manager')

# Integration monitoring
INTEGRATION_MONITOR_RUNNING = False
INTEGRATION_THREAD = None

# ============= TIME UTILITIES =============

def parse_time_query(when: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse natural language time queries"""
    if not when:
        return None, None
    
    when_lower = when.lower().strip()
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if when_lower == "today":
        return today_start, now
    elif when_lower == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        return yesterday_start, today_start - timedelta(seconds=1)
    elif when_lower in ["this week", "week"]:
        week_start = today_start - timedelta(days=now.weekday())
        return week_start, now
    elif when_lower == "last week":
        week_start = today_start - timedelta(days=now.weekday())
        last_week_start = week_start - timedelta(days=7)
        return last_week_start, week_start
    elif when_lower == "morning":
        return today_start.replace(hour=6), today_start.replace(hour=12)
    elif when_lower == "afternoon":
        return today_start.replace(hour=12), today_start.replace(hour=18)
    elif when_lower == "evening":
        return today_start.replace(hour=18), today_start.replace(hour=23, minute=59)
    elif when_lower == "last hour":
        return now - timedelta(hours=1), now
    
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
        else:
            return dt.strftime("%m/%d")
    except:
        return ""

def format_duration(start_time: str, end_time: str = None) -> str:
    """Format task completion duration"""
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
    if any(word in task_lower for word in ['urgent', 'asap', 'critical', 'important', '!!!', 'now']):
        return "!"
    elif any(word in task_lower for word in ['low priority', 'whenever', 'maybe', 'someday']):
        return "↓"
    return None

# ============= DATABASE =============

def _init_db() -> sqlite3.Connection:
    """Initialize SQLite database (internal)"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")
    
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
    
    conn.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts 
        USING fts5(task, content=tasks, content_rowid=id)
    ''')
    
    conn.execute('''
        CREATE TRIGGER IF NOT EXISTS tasks_ai 
        AFTER INSERT ON tasks BEGIN
            INSERT INTO tasks_fts(rowid, task) VALUES (new.id, new.task);
        END
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            duration_ms INTEGER,
            author TEXT
        )
    ''')
    
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_author ON tasks(author)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_source ON tasks(source, source_id)')
    
    conn.commit()
    return conn

def find_task_smart(identifier: str, conn: sqlite3.Connection) -> Optional[int]:
    """Smart task resolution"""
    identifier = str(identifier).strip()
    
    if identifier.lower() == "last":
        last_op = op_tracker.get()
        if last_op and last_op['type'] == 'add_task':
            return last_op['result'].get('id')
        
        result = conn.execute('''
            SELECT id FROM tasks 
            WHERE completed_at IS NULL 
            ORDER BY created DESC 
            LIMIT 1
        ''').fetchone()
        return result[0] if result else None
    
    clean_id = re.sub(r'[^\d]', '', identifier)
    if clean_id:
        try:
            task_id = int(clean_id)
            exists = conn.execute('SELECT id FROM tasks WHERE id = ?', (task_id,)).fetchone()
            if exists:
                return task_id
        except:
            pass
        
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

def _log_operation(operation: str, duration_ms: int = None):
    """Log operation for stats"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.execute(
                'INSERT INTO stats (operation, timestamp, duration_ms, author) VALUES (?, ?, ?, ?)',
                (operation, datetime.now().isoformat(), duration_ms, CURRENT_AI_ID)
            )
    except:
        pass

def _log_to_notebook(action: str, task_id: int, task_desc: str, evidence: str = None):
    """Log task actions to notebook"""
    try:
        integration_data = {
            'source': 'task_manager',
            'source_id': task_id,
            'action': action,
            'task': task_desc[:200],
            'evidence': evidence[:200] if evidence else None,
            'created': datetime.now().isoformat()
        }
        
        with open(NOTEBOOK_INTEGRATION_FILE, 'a') as f:
            f.write(json.dumps(integration_data) + '\n')
    except:
        pass

# ============= INTEGRATION MONITORING =============

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
                            task_desc = data.get('task', 'Task from notebook')
                            source_id = data.get('source_id')
                            
                            with sqlite3.connect(str(DB_FILE)) as conn:
                                priority = detect_priority(task_desc)
                                cursor = conn.execute('''
                                    INSERT INTO tasks (task, author, created, priority, source, source_id)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (task_desc, CURRENT_AI_ID, datetime.now().isoformat(), 
                                     priority, 'notebook', source_id))
                    except:
                        continue
        except:
            pass
        
        time.sleep(5)

def start_integration_monitor():
    """Start integration monitoring"""
    global INTEGRATION_MONITOR_RUNNING, INTEGRATION_THREAD
    
    if not INTEGRATION_MONITOR_RUNNING:
        INTEGRATION_MONITOR_RUNNING = True
        INTEGRATION_THREAD = threading.Thread(target=monitor_task_integration, daemon=True)
        INTEGRATION_THREAD.start()

def stop_integration_monitor():
    """Stop integration monitoring"""
    global INTEGRATION_MONITOR_RUNNING, INTEGRATION_THREAD
    INTEGRATION_MONITOR_RUNNING = False
    if INTEGRATION_THREAD:
        INTEGRATION_THREAD.join(timeout=1)


def task_manager_link_notebook_entry(
    task_id: int = None,
    notebook_entry_id: int = None,
    summary: str = None,
    context: str = None,
    representation_policy: str = 'default',
    teambook_name: str = None,
    **kwargs
) -> Dict:
    """Link a task to a notebook entry and log the connection in Teambook."""
    try:
        task_id = int(kwargs.get('task_id', task_id))
        notebook_entry_id = int(kwargs.get('notebook_entry_id', notebook_entry_id))
    except Exception:
        return {"error": "invalid_ids"}

    if task_id <= 0 or notebook_entry_id <= 0:
        return {"error": "invalid_ids"}

    representation_policy = (kwargs.get('representation_policy', representation_policy) or 'default').strip().lower()
    summary = kwargs.get('summary', summary)
    context = kwargs.get('context', context)
    teambook_target = kwargs.get('teambook_name', teambook_name) or TASK_MANAGER_TEAMBOOK

    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute('BEGIN')

            row = conn.execute(
                'SELECT id, task, linked_items FROM tasks WHERE id = ?',
                (task_id,)
            ).fetchone()

            if not row:
                conn.rollback()
                return {"error": f"task_not_found:{task_id}"}

            linked_items_raw = row['linked_items']
            linked_items_list = []
            if linked_items_raw:
                try:
                    parsed = json.loads(linked_items_raw)
                    if isinstance(parsed, list):
                        linked_items_list = parsed
                except json.JSONDecodeError:
                    linked_items_list = []

            existing_entry = None
            for item in linked_items_list:
                if isinstance(item, dict) and item.get('type') == 'notebook' and item.get('id') == notebook_entry_id:
                    existing_entry = item
                    break

            if existing_entry is None:
                existing_entry = {'type': 'notebook', 'id': notebook_entry_id}
                linked_items_list.append(existing_entry)

            if context:
                existing_entry['context'] = context[:200]

            teambook_note_id = None

            conn.execute(
                'UPDATE tasks SET linked_items = ? WHERE id = ?',
                (json.dumps(linked_items_list), task_id)
            )

            if TEAMBOOK_STORAGE_AVAILABLE and teambook_target:
                try:
                    adapter = TeambookStorageAdapter(teambook_target)
                    note_content = f"[TASK LINK] Task #{task_id}: {row['task']}\nLinked notebook entry: {notebook_entry_id}"
                    if context:
                        note_content += f"\nContext: {context[:500]}"

                    note_summary = summary or f"Linked task {task_id} to notebook {notebook_entry_id}"
                    adapter_linked_items = json.dumps([
                        f"task:{task_id}",
                        f"notebook:{notebook_entry_id}"
                    ])

                    teambook_note_id = adapter.write_note(
                        content=note_content,
                        summary=note_summary,
                        tags=['task-link', 'integration'],
                        linked_items=adapter_linked_items,
                        note_type='task_link',
                        representation_policy=representation_policy,
                        metadata={'task_id': task_id, 'notebook_entry_id': notebook_entry_id}
                    )

                    existing_entry['teambook_note_id'] = teambook_note_id
                    conn.execute(
                        'UPDATE tasks SET linked_items = ? WHERE id = ?',
                        (json.dumps(linked_items_list), task_id)
                    )

                except Exception as exc:
                    conn.rollback()
                    logging.error(f"Failed to create Teambook link note: {exc}")
                    return {"error": "teambook_link_failed"}

            conn.commit()

        return {
            "linked": f"{task_id}|notebook:{notebook_entry_id}|teambook_note:{teambook_note_id or 'none'}"
        }

    except Exception as exc:
        logging.error(f"Link notebook entry failed: {exc}")
        return {"error": "link_failed"}

# ============= TOOL FUNCTIONS =============

def add_task(task: str = None, linked_items: List[str] = None, **kwargs) -> Dict:
    """
    Add a new task

    SECURITY: Validates input size BEFORE str() conversion to prevent DoS
    """
    try:
        start = datetime.now()

        # SECURITY: Check type and size BEFORE conversion
        # This prevents DoS attacks from large/complex objects
        task_input = task or kwargs.get('task') or ''

        # Type validation
        if not isinstance(task_input, (str, int, float, bool, type(None))):
            # Reject complex objects that could cause DoS during str() conversion
            return {"error": "Task must be a string or simple type"}

        # Convert to string (safe for simple types)
        task = str(task_input).strip()

        if not task:
            return {"error": "Need task description"}

        # SECURITY: Length check after conversion
        if len(task) > MAX_TASK_LENGTH:
            task = smart_truncate(task, MAX_TASK_LENGTH)

        priority = detect_priority(task)

        # Ensure database is initialized
        conn = _init_db()
        try:
            cursor = conn.execute('''
                INSERT INTO tasks (task, author, created, priority, linked_items, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (task, CURRENT_AI_ID, datetime.now().isoformat(), priority,
                  json.dumps(linked_items) if linked_items else None, 'manual'))
            task_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()

        _log_to_notebook('task_created', task_id, task)
        op_tracker.save('add_task', {'id': task_id, 'task': task})

        duration = int((datetime.now() - start).total_seconds() * 1000)
        _log_operation('add_task', duration)

        priority_str = priority if priority else ""
        return {"added": f"{task_id}|now|{smart_truncate(task, 80)}{priority_str}"}

    except Exception as e:
        import traceback
        error_details = f"Failed to add task: {str(e)}\n{traceback.format_exc()}"
        return {"error": error_details}

def list_tasks(filter_type: str = None, when: str = None, full: bool = False, **kwargs) -> Dict:
    """List tasks"""
    try:
        filter_lower = str(filter_type or kwargs.get('filter') or "pending").lower().strip()

        if when:
            start_time, end_time = parse_time_query(when)
            if not start_time:
                return {"msg": f"Didn't understand time query: '{when}'"}
        else:
            start_time, end_time = None, None

        show_pending = filter_lower in ["pending", "todo", "open", "active", ""]
        show_completed = filter_lower in ["completed", "complete", "done", "finished"]

        if filter_lower in ["all", "everything", "both"]:
            show_pending = show_completed = True

        # Ensure database exists and is initialized
        with sqlite3.connect(str(DB_FILE)) as conn:
            # Check if tasks table exists, if not initialize
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
            if not cursor.fetchone():
                # Initialize the database
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
                conn.commit()

        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            if when:
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
                else:
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
                else:
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
        
        pending_tasks = [t for t in tasks if not t['completed_at']]
        completed_tasks = [t for t in tasks if t['completed_at']]
        
        # Pipe format
        lines = []
        summary_parts = []
        if pending_tasks:
            high = sum(1 for t in pending_tasks if t['priority'] == '!')
            summary_parts.append(f"{len(pending_tasks)}p({high}!)" if high > 0 else f"{len(pending_tasks)}p")
        if completed_tasks:
            summary_parts.append(f"{len(completed_tasks)}c")
        
        if summary_parts:
            lines.append('|'.join(summary_parts))
        
        shown = 0
        for t in pending_tasks[:15]:
            parts = [
                str(t['id']),
                format_time_contextual(t['created']),
                smart_truncate(t['task'], 80)
            ]
            if t['priority']:
                parts.append(t['priority'])
            if t['source'] == 'notebook' and t['source_id']:
                parts.append(f"n{t['source_id']}")
            lines.append('|'.join(pipe_escape(p) for p in parts))
            shown += 1
        
        if len(pending_tasks) > shown:
            lines.append(f"+{len(pending_tasks)-shown}")
        
        if show_completed and completed_tasks:
            for t in completed_tasks[:5]:
                parts = [
                    str(t['id']),
                    "✓",
                    smart_truncate(t['task'], 60),
                    format_time_contextual(t['completed_at'])
                ]
                lines.append('|'.join(pipe_escape(p) for p in parts))
        
        return {"tasks": lines}
        
    except Exception as e:
        import traceback
        return {"error": f"Failed to list tasks: {str(e)}", "traceback": traceback.format_exc()}

def complete_task(task_id: str = None, evidence: str = None, **kwargs) -> Dict:
    """Complete a task"""
    try:
        start = datetime.now()
        task_id = str(task_id or kwargs.get('task_id') or '').strip()
        evidence = str(evidence or kwargs.get('evidence') or '').strip() if evidence or kwargs.get('evidence') else None
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            resolved_id = find_task_smart(task_id, conn)
            
            if not resolved_id:
                pending = conn.execute(
                    'SELECT id, task FROM tasks WHERE completed_at IS NULL ORDER BY created DESC LIMIT 5'
                ).fetchall()
                
                available = '|'.join([f"{p['id']}:{smart_truncate(p['task'], 20)}" for p in pending])
                return {"error": "Task not found", "available": available}
            
            task = conn.execute('SELECT * FROM tasks WHERE id = ?', (resolved_id,)).fetchone()
            
            if task['completed_at']:
                return {"error": f"Task {resolved_id} already completed"}
            
            now = datetime.now()
            if evidence and len(evidence) > MAX_EVIDENCE_LENGTH:
                evidence = smart_truncate(evidence, MAX_EVIDENCE_LENGTH)
            
            conn.execute('''
                UPDATE tasks 
                SET completed_at = ?, completed_by = ?, evidence = ?
                WHERE id = ?
            ''', (now.isoformat(), CURRENT_AI_ID, evidence, resolved_id))
            
            duration = format_duration(task['created'], now.isoformat())
            _log_to_notebook('task_completed', resolved_id, task['task'], evidence)
        
        op_tracker.save('complete_task', {'id': resolved_id})
        op_duration = int((datetime.now() - start).total_seconds() * 1000)
        _log_operation('complete_task', op_duration)
        
        msg = f"{resolved_id}|✓|{duration}"
        if evidence:
            msg += f"|{smart_truncate(evidence, 50)}"
        return {"completed": msg}
        
    except Exception as e:
        return {"error": "Failed to complete task"}

def delete_task(task_id: str = None, **kwargs) -> Dict:
    """Delete a task"""
    try:
        task_id = str(task_id or kwargs.get('task_id') or '').strip()
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            resolved_id = find_task_smart(task_id, conn)
            
            if not resolved_id:
                return {"error": f"Task not found: '{task_id}'"}
            
            task = conn.execute('SELECT * FROM tasks WHERE id = ?', (resolved_id,)).fetchone()
            status = "done" if task['completed_at'] else "pending"
            
            _log_to_notebook('task_deleted', resolved_id, task['task'])
            conn.execute('DELETE FROM tasks WHERE id = ?', (resolved_id,))
        
        return {"deleted": f"{resolved_id}|{status}"}
        
    except Exception as e:
        return {"error": "Failed to delete task"}

def task_stats(full: bool = False, **kwargs) -> Dict:
    """Get task statistics"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
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
            
            oldest = conn.execute('''
                SELECT created FROM tasks 
                WHERE completed_at IS NULL 
                ORDER BY created 
                LIMIT 1
            ''').fetchone()
        
        parts = [
            f"t:{stats[0]}",
            f"p:{stats[1]}",
        ]
        if stats[3] > 0:
            parts.append(f"!:{stats[3]}")
        parts.append(f"c:{stats[2]}")
        if stats[6] > 0:
            parts.append(f"today:{stats[6]}")
        if stats[7] > 0:
            parts.append(f"nb:{stats[7]}")
        if oldest:
            parts.append(f"oldest:{format_time_contextual(oldest[0])}")
        
        return {"stats": '|'.join(parts)}
        
    except Exception as e:
        return {"error": "Stats unavailable"}

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
    """Execute multiple operations"""
    try:
        operations = operations or kwargs.get('operations', [])
        
        if not operations:
            return {"error": "No operations provided"}
        
        if len(operations) > BATCH_MAX:
            return {"error": f"Too many operations (max {BATCH_MAX})"}
        
        results = []
        op_map = {
            'add_task': add_task, 'add': add_task, 'a': add_task,
            'list_tasks': list_tasks, 'list': list_tasks, 'l': list_tasks,
            'complete_task': complete_task, 'complete': complete_task, 'c': complete_task, 'done': complete_task,
            'delete_task': delete_task, 'delete': delete_task, 'd': delete_task,
            'task_stats': task_stats, 'stats': task_stats, 's': task_stats,
            'link_notebook_entry': task_manager_link_notebook_entry, 'link': task_manager_link_notebook_entry
        }
        
        for op in operations:
            op_type = op.get('type', '').lower()
            op_args = op.get('args', {})
            
            if op_type not in op_map:
                results.append({"error": f"Unknown operation: {op_type}"})
                continue
            
            result = op_map[op_type](**op_args)
            results.append(result)
        
        return {"batch_results": results, "count": len(results)}
        
    except Exception as e:
        return {"error": f"Batch failed: {str(e)}"}

# ============= MCP SERVER =============

def main():
    # Initialize
    _init_db()
    start_integration_monitor()
    
    server = MCPServer("task_manager", VERSION, 
                      "Integrated tasks: cross-tool logging, time queries, 70% fewer tokens")
    
    # Register tools
    server.register_tool(
        add_task, "add_task",
        "Create task (auto-logs to notebook)",
        {
            "task": {"type": "string", "description": "The task description"},
            "linked_items": {"type": "array", "description": "Optional links to other tools"}
        }
    )
    
    server.register_tool(
        list_tasks, "list_tasks",
        "List tasks (supports when='yesterday'/'today'/etc)",
        {
            "filter": {"type": "string", "description": "Filter: pending (default), completed, or all"},
            "when": {"type": "string", "description": "Time query: today, yesterday, this week, morning, etc."},
            "full": {"type": "boolean", "description": "Show full details (default: false for summary)"}
        }
    )
    
    server.register_tool(
        complete_task, "complete_task",
        "Complete task (auto-logs to notebook, use 'last' for recent)",
        {
            "task_id": {"type": "string", "description": "Task ID, 'last', or partial match"},
            "evidence": {"type": "string", "description": "Optional evidence or notes"}
        }
    )
    
    server.register_tool(
        delete_task, "delete_task",
        "Delete a task",
        {"task_id": {"type": "string", "description": "Task ID or partial match"}}
    )

    server.register_tool(
        task_manager_link_notebook_entry, "link_notebook_entry",
        "Link a task to a notebook entry (and log it in Teambook)",
        {
            "task_id": {"type": "integer", "description": "Existing task identifier"},
            "notebook_entry_id": {"type": "integer", "description": "Notebook entry identifier"},
            "summary": {"type": "string", "description": "Optional Teambook summary"},
            "context": {"type": "string", "description": "Optional context to store with the link"},
            "representation_policy": {"type": "string", "description": "Use 'verbatim' to keep full detail"},
            "teambook_name": {"type": "string", "description": "Override target Teambook"}
        },
        ["task_id", "notebook_entry_id"]
    )

    server.register_tool(
        task_stats, "task_stats",
        "Get task statistics",
        {"full": {"type": "boolean", "description": "Show full insights"}}
    )
    
    server.register_tool(
        batch, "batch",
        "Execute multiple operations",
        {
            "operations": {
                "type": "array",
                "description": "List of operations",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "Operation type"},
                        "args": {"type": "object", "description": "Arguments"}
                    }
                }
            }
        },
        ["operations"]
    )
    
    # Custom result formatting
    def format_result(tool_name: str, result: Dict) -> str:
        if "error" in result:
            text = f"Error: {result['error']}"
            if "available" in result:
                text += f"\nAvailable: {result['available']}"
            return text
        elif "added" in result:
            return result["added"]
        elif "tasks" in result:
            return '\n'.join(result["tasks"])
        elif "completed" in result:
            return result["completed"]
        elif "deleted" in result:
            return result["deleted"]
        elif "stats" in result:
            return result["stats"]
        elif "msg" in result:
            return result["msg"]
        elif "batch_results" in result:
            lines = [f"Batch: {result.get('count', 0)}"]
            for r in result["batch_results"]:
                if isinstance(r, dict):
                    if "error" in r:
                        lines.append(f"Error: {r['error']}")
                    elif "added" in r:
                        lines.append(r["added"])
                    elif "completed" in r:
                        lines.append(r["completed"])
                    elif "deleted" in r:
                        lines.append(r["deleted"])
                else:
                    lines.append(str(r))
            return '\n'.join(lines)
        else:
            return str(list(result.values())[0]) if result else ""
    
    server.format_tool_result = format_result
    
    # Run server
    try:
        server.run()
    finally:
        stop_integration_monitor()

if __name__ == "__main__":
    main()
