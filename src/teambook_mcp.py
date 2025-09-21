#!/usr/bin/env python3
"""
TEAMBOOK MCP v3.0.0 - OPTIMIZED UNIFIED TEAM COORDINATION WITH SQLITE
=====================================================================
Shared consciousness for AI teams. SQLite-powered, token-optimized.
Single source of truth. No hierarchy. Stateless. Infinitely scalable.

Core improvements (v3):
- SQLite backend with FTS5 for instant search at any scale
- Summary mode by default (95% token reduction)
- Batch operations for team workflows
- Auto-migration from v2 JSON format
- Better cross-tool linking support

Projects:
- Separate teambooks for different workflows/topics
- Set TEAMBOOK_PROJECT env var for default project
- Or specify project="name" in any function call

Core functions (all accept optional project parameter):
- write(content, type=None, priority=None, project=None) - Share anything
- read(query=None, type=None, status="pending", claimed_by=None, full=False, project=None) - View with summary
- get(id, project=None) - Full entry with comments
- comment(id, content, project=None) - Threaded discussion
- claim(id, project=None) - Atomically claim task
- complete(id, evidence=None, project=None) - Mark done
- update(id, content=None, type=None, priority=None, project=None) - Fix mistakes
- archive(id, reason=None, project=None) - Safe removal
- status(full=False, project=None) - Team pulse (summary by default)
- projects() - List available teambook projects
- batch(operations, project=None) - Execute multiple operations
=====================================================================
"""

import json
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
import threading
import random

# Version
VERSION = "3.0.0"

# Limits
MAX_CONTENT_LENGTH = 5000
MAX_EVIDENCE_LENGTH = 500
MAX_COMMENT_LENGTH = 1000
MAX_ENTRIES = 100000
BATCH_MAX = 50

# Storage configuration
BASE_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    BASE_DIR = Path(os.environ.get('TEMP', '/tmp'))

# Default project from environment
DEFAULT_PROJECT = os.environ.get('TEAMBOOK_PROJECT', 'default')

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Thread safety for atomic operations
lock = threading.Lock()

def get_persistent_id():
    """Get or create persistent AI identity"""
    for location in [Path(__file__).parent, BASE_DIR, Path.home()]:
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

def smart_truncate(text: str, max_chars: int) -> str:
    """Intelligent truncation preserving key information"""
    if len(text) <= max_chars:
        return text
    
    code_indicators = ['```', 'def ', 'class ', 'function', 'import ', '{', '}']
    is_code = any(indicator in text[:200] for indicator in code_indicators)
    
    if is_code and max_chars > 100:
        start_chars = int(max_chars * 0.65)
        end_chars = max_chars - start_chars - 5
        return text[:start_chars] + "\n...\n" + text[-end_chars:]
    else:
        cutoff = text.rfind(' ', 0, max_chars - 3)
        if cutoff == -1 or cutoff < max_chars * 0.8:
            cutoff = max_chars - 3
        return text[:cutoff] + "..."

def format_duration(start_time: str, end_time: str = None) -> str:
    """Format duration compactly"""
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

def get_project_db_path(project: str = None) -> Path:
    """Get database path for a specific project"""
    if project is None:
        project = DEFAULT_PROJECT
    
    # Sanitize project name
    project = str(project).strip().lower()
    project = ''.join(c if c.isalnum() or c in '-_' else '_' for c in project)
    
    data_dir = BASE_DIR / f"teambook_{project}_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir / "teambook.db"

def init_db(project: str = None) -> sqlite3.Connection:
    """Initialize SQLite database for a project"""
    db_path = get_project_db_path(project)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    
    # Main entries table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('task', 'note', 'decision')),
            author TEXT NOT NULL,
            created TEXT NOT NULL,
            priority TEXT,
            claimed_by TEXT,
            claimed_at TEXT,
            completed_at TEXT,
            completed_by TEXT,
            evidence TEXT,
            archived_at TEXT,
            archived_by TEXT,
            archive_reason TEXT,
            linked_items TEXT
        )
    ''')
    
    # Full-text search
    conn.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts 
        USING fts5(content, content=entries, content_rowid=id)
    ''')
    
    # Trigger to keep FTS in sync
    conn.execute('''
        CREATE TRIGGER IF NOT EXISTS entries_ai 
        AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
        END
    ''')
    
    # Comments table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created TEXT NOT NULL,
            FOREIGN KEY(entry_id) REFERENCES entries(id)
        )
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
    
    # Indices for performance
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(type)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entries_archived ON entries(archived_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_comments_entry ON comments(entry_id)')
    
    conn.commit()
    return conn

def migrate_from_json(project: str = None):
    """Migrate from v2 JSON to v3 SQLite"""
    if project is None:
        project = DEFAULT_PROJECT
    
    # Get paths
    project_clean = str(project).strip().lower()
    project_clean = ''.join(c if c.isalnum() or c in '-_' else '_' for c in project_clean)
    
    old_data_dir = BASE_DIR / f"teambook_{project_clean}_data"
    old_json_file = old_data_dir / "teambook.json"
    db_path = get_project_db_path(project)
    
    if not old_json_file.exists() or db_path.exists():
        return
    
    logging.info(f"Migrating project '{project}' from JSON to SQLite...")
    
    try:
        with open(old_json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = init_db(project)
        
        # Get author map for deduplication
        authors = data.get("authors", {})
        entries_data = data.get("entries", {})
        
        for eid, entry in entries_data.items():
            # Expand author IDs
            author = authors.get(entry.get("a"), entry.get("a", "Unknown"))
            
            # Convert type shorthand
            type_map = {'t': 'task', 'n': 'note', 'd': 'decision'}
            entry_type = type_map.get(entry.get("t"), "note")
            
            # Insert main entry
            conn.execute('''
                INSERT INTO entries (
                    id, content, type, author, created, priority,
                    claimed_by, claimed_at, completed_at, completed_by,
                    evidence, archived_at, archived_by, archive_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(eid),
                entry.get("c", ""),
                entry_type,
                author,
                entry.get("ts", datetime.now().isoformat()),
                entry.get("p"),
                authors.get(entry.get("cb"), entry.get("cb")),
                entry.get("ca"),
                entry.get("co"),
                authors.get(entry.get("cob"), entry.get("cob")),
                entry.get("e"),
                entry.get("ar"),
                authors.get(entry.get("arb"), entry.get("arb")),
                entry.get("arr")
            ))
            
            # Migrate comments
            if "cm" in entry:
                for comment in entry["cm"]:
                    comment_author = authors.get(comment.get("a"), comment.get("a", "Unknown"))
                    conn.execute('''
                        INSERT INTO comments (entry_id, author, content, created)
                        VALUES (?, ?, ?, ?)
                    ''', (int(eid), comment_author, comment.get("c", ""), comment.get("ts", "")))
        
        conn.commit()
        conn.close()
        
        # Rename old file to backup
        old_json_file.rename(old_json_file.with_suffix('.json.backup'))
        logging.info(f"Migrated {len(entries_data)} entries to SQLite")
        
    except Exception as e:
        logging.error(f"Migration failed: {e}")

def log_operation(operation: str, duration_ms: int = None, project: str = None):
    """Log operation for stats"""
    try:
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            conn.execute(
                'INSERT INTO stats (operation, timestamp, duration_ms, author) VALUES (?, ?, ?, ?)',
                (operation, datetime.now().isoformat(), duration_ms, CURRENT_AI_ID)
            )
    except:
        pass

def detect_type_and_priority(content: str) -> tuple:
    """Auto-detect entry type and priority from content"""
    content_lower = content.lower()
    
    # Detect type
    if any(marker in content_lower for marker in ['todo:', 'task:']):
        entry_type = "task"
    elif any(marker in content_lower for marker in ['decision:', 'decided:']):
        entry_type = "decision"
    else:
        entry_type = "note"
    
    # Detect priority (only for tasks)
    priority = None
    if entry_type == "task":
        if any(word in content_lower for word in ['urgent', 'asap', 'critical', 'important']):
            priority = "!"
        elif any(word in content_lower for word in ['low priority', 'whenever', 'maybe']):
            priority = "↓"
    
    return entry_type, priority

def write(content: str = None, type: str = None, priority: str = None, 
          project: str = None, linked_items: List[str] = None, **kwargs) -> Dict:
    """Share anything with the team"""
    try:
        start = datetime.now()
        
        if content is None:
            content = kwargs.get('content', '')
        
        content = str(content).strip()
        if not content:
            return {"error": "Need content to write"}
        
        if len(content) > MAX_CONTENT_LENGTH:
            content = smart_truncate(content, MAX_CONTENT_LENGTH)
        
        # Auto-detect type and priority if not provided
        if type is None or priority is None:
            detected_type, detected_priority = detect_type_and_priority(content)
            if type is None:
                type = detected_type
            if priority is None and type == "task":
                priority = detected_priority
        
        # Store in database
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            cursor = conn.execute('''
                INSERT INTO entries (content, type, author, created, priority, linked_items)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (content, type, CURRENT_AI_ID, datetime.now().isoformat(), priority,
                  json.dumps(linked_items) if linked_items else None))
            entry_id = cursor.lastrowid
        
        # Log operation
        duration = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('write', duration, project)
        
        # Format response
        type_marker = type.upper()
        priority_str = priority if priority else ""
        preview = smart_truncate(content, 80)
        
        return {"created": f"[{entry_id}]{priority_str} {type_marker}: {preview}"}
        
    except Exception as e:
        logging.error(f"Error in write: {e}")
        return {"error": "Failed to write"}

def read(query: str = None, type: str = None, status: str = "pending",
         claimed_by: str = None, full: bool = False, project: str = None, **kwargs) -> Dict:
    """View team activity - summary by default, full with parameter"""
    try:
        start = datetime.now()
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query
            conditions = ["archived_at IS NULL"]
            params = []
            
            if type:
                conditions.append("type = ?")
                params.append(type)
            
            if type == 'task' or not type:
                if status == 'pending':
                    conditions.append("(type != 'task' OR completed_at IS NULL)")
                elif status == 'completed':
                    conditions.append("(type != 'task' OR completed_at IS NOT NULL)")
            
            if claimed_by == 'me':
                conditions.append("claimed_by = ?")
                params.append(CURRENT_AI_ID)
            elif claimed_by == 'unclaimed':
                conditions.append("claimed_by IS NULL")
            elif claimed_by:
                conditions.append("claimed_by = ?")
                params.append(claimed_by)
            
            if query:
                # Use FTS for search
                cursor = conn.execute(f'''
                    SELECT e.* FROM entries e
                    JOIN entries_fts ON e.id = entries_fts.rowid
                    WHERE entries_fts MATCH ? AND {' AND '.join(conditions)}
                    ORDER BY 
                        CASE WHEN e.priority = '!' THEN 0
                             WHEN e.priority = '↓' THEN 2
                             ELSE 1 END,
                        e.created DESC
                    LIMIT 50
                ''', [query] + params)
            else:
                cursor = conn.execute(f'''
                    SELECT * FROM entries
                    WHERE {' AND '.join(conditions)}
                    ORDER BY 
                        CASE WHEN priority = '!' THEN 0
                             WHEN priority = '↓' THEN 2
                             ELSE 1 END,
                        created DESC
                    LIMIT 50
                ''', params)
            
            entries = cursor.fetchall()
        
        if not entries:
            if type == 'task' and status == 'pending':
                return {"msg": "No pending tasks", "tip": "write('TODO: description')"}
            else:
                return {"msg": "No entries found"}
        
        # Summary mode (default)
        if not full:
            # Count by type and status
            tasks_pending = sum(1 for e in entries if e['type'] == 'task' and not e['completed_at'])
            tasks_claimed = sum(1 for e in entries if e['type'] == 'task' and e['claimed_by'] and not e['completed_at'])
            tasks_done = sum(1 for e in entries if e['type'] == 'task' and e['completed_at'])
            notes = sum(1 for e in entries if e['type'] == 'note')
            decisions = sum(1 for e in entries if e['type'] == 'decision')
            
            summary_parts = []
            if tasks_pending > 0:
                summary_parts.append(f"{tasks_pending} tasks ({tasks_claimed} claimed)")
            if tasks_done > 0:
                summary_parts.append(f"{tasks_done} done")
            if notes > 0:
                summary_parts.append(f"{notes} notes")
            if decisions > 0:
                summary_parts.append(f"{decisions} decisions")
            
            if query:
                return {"summary": f"{len(entries)} matches for '{query}': " + " | ".join(summary_parts)}
            else:
                return {"summary": " | ".join(summary_parts) if summary_parts else "Empty"}
        
        # Full mode
        lines = []
        for entry in entries[:20]:
            eid = entry['id']
            content_preview = smart_truncate(entry['content'], 100)
            time_str = format_time_contextual(entry['created'])
            
            if entry['type'] == 'task':
                priority = entry['priority'] or ''
                if entry['completed_at']:
                    duration = format_duration(entry['claimed_at'] or entry['created'], entry['completed_at'])
                    evidence = f" - {smart_truncate(entry['evidence'], 40)}" if entry['evidence'] else ""
                    lines.append(f"[{eid}]✓ {content_preview}{evidence} ({duration})")
                elif entry['claimed_by']:
                    claimer = entry['claimed_by'] if entry['claimed_by'] != CURRENT_AI_ID else ""
                    claim_time = format_time_contextual(entry['claimed_at'])
                    claimer_str = f" @{claimer}" if claimer else ""
                    lines.append(f"[{eid}]{priority} {content_preview}{claimer_str} ({claim_time})")
                else:
                    lines.append(f"[{eid}]{priority} {content_preview} @{time_str}")
            elif entry['type'] == 'decision':
                author = f"@{entry['author']}" if entry['author'] != CURRENT_AI_ID else ""
                lines.append(f"[D{eid}] {content_preview} {author} {time_str}")
            else:
                author = f"@{entry['author']}" if entry['author'] != CURRENT_AI_ID else ""
                lines.append(f"[N{eid}] {content_preview} {author} {time_str}")
        
        if len(entries) > 20:
            lines.append(f"+{len(entries)-20} more")
        
        # Log operation
        duration = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('read', duration, project)
        
        return {"entries": lines}
        
    except Exception as e:
        logging.error(f"Error in read: {e}")
        return {"error": "Failed to read"}

def get(id: int = None, project: str = None, **kwargs) -> Dict:
    """Retrieve full entry with all comments"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        # Handle string IDs
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
            if id.startswith('D') or id.startswith('N'):
                id = id[1:]
        id = int(id)
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get entry
            entry = conn.execute('SELECT * FROM entries WHERE id = ?', (id,)).fetchone()
            if not entry:
                return {"error": f"Entry [{id}] not found"}
            
            # Get comments
            comments = conn.execute(
                'SELECT * FROM comments WHERE entry_id = ? ORDER BY created',
                (id,)
            ).fetchall()
        
        # Build output
        lines = []
        
        # Header
        type_str = entry['type'].upper()
        priority = entry['priority'] or ''
        time_str = format_time_contextual(entry['created'])
        author = entry['author'] if entry['author'] != CURRENT_AI_ID else "you"
        
        if entry['type'] == 'task':
            if entry['completed_at']:
                lines.append(f"[{id}]✓ {type_str} by {author} @{time_str} (completed)")
            elif entry['claimed_by']:
                claimer = entry['claimed_by'] if entry['claimed_by'] != CURRENT_AI_ID else "you"
                lines.append(f"[{id}]{priority} {type_str} by {author} @{time_str} (claimed by {claimer})")
            else:
                lines.append(f"[{id}]{priority} {type_str} by {author} @{time_str} (unclaimed)")
        else:
            lines.append(f"[{id}] {type_str} by {author} @{time_str}")
        
        lines.append("---")
        lines.append(entry['content'])
        
        # Evidence if completed
        if entry['evidence']:
            lines.append("---")
            lines.append(f"Evidence: {entry['evidence']}")
        
        # Comments
        if comments:
            lines.append("---")
            lines.append(f"Comments ({len(comments)}):")
            for comment in comments:
                comment_author = comment['author'] if comment['author'] != CURRENT_AI_ID else "you"
                comment_time = format_time_contextual(comment['created'])
                lines.append(f"  {comment_author}@{comment_time}: {comment['content']}")
        
        return {"entry": lines}
        
    except Exception as e:
        logging.error(f"Error in get: {e}")
        return {"error": "Failed to get entry"}

def comment(id: int = None, content: str = None, project: str = None, **kwargs) -> Dict:
    """Add threaded comment to entry"""
    try:
        if id is None:
            id = kwargs.get('id')
        if content is None:
            content = kwargs.get('content', '')
        
        # Parse ID
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
            if id.startswith('D') or id.startswith('N'):
                id = id[1:]
        id = int(id)
        
        content = str(content).strip()
        if not content:
            return {"error": "Need comment content"}
        
        if len(content) > MAX_COMMENT_LENGTH:
            content = smart_truncate(content, MAX_COMMENT_LENGTH)
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            # Check entry exists
            entry = conn.execute('SELECT id FROM entries WHERE id = ?', (id,)).fetchone()
            if not entry:
                return {"error": f"Entry [{id}] not found"}
            
            # Add comment
            conn.execute('''
                INSERT INTO comments (entry_id, author, content, created)
                VALUES (?, ?, ?, ?)
            ''', (id, CURRENT_AI_ID, content, datetime.now().isoformat()))
        
        preview = smart_truncate(content, 60)
        return {"commented": f"[{id}] +comment: {preview}"}
        
    except Exception as e:
        logging.error(f"Error in comment: {e}")
        return {"error": "Failed to add comment"}

def claim(id: int = None, project: str = None, **kwargs) -> Dict:
    """Atomically claim an unclaimed task"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
        id = int(id)
        
        with lock:  # Atomic operation
            conn = sqlite3.connect(str(get_project_db_path(project)))
            try:
                conn.row_factory = sqlite3.Row
                
                # Check task
                entry = conn.execute('SELECT * FROM entries WHERE id = ?', (id,)).fetchone()
                
                if not entry:
                    return {"error": f"Task [{id}] not found"}
                if entry['type'] != 'task':
                    return {"error": f"[{id}] is not a task"}
                if entry['claimed_by']:
                    return {"error": f"[{id}] already claimed by {entry['claimed_by']}"}
                if entry['completed_at']:
                    return {"error": f"[{id}] already completed"}
                if entry['archived_at']:
                    return {"error": f"[{id}] is archived"}
                
                # Claim it
                conn.execute('''
                    UPDATE entries 
                    SET claimed_by = ?, claimed_at = ?
                    WHERE id = ?
                ''', (CURRENT_AI_ID, datetime.now().isoformat(), id))
                
                conn.commit()
                
                preview = smart_truncate(entry['content'], 60)
                return {"claimed": f"[{id}]: {preview}"}
                
            finally:
                conn.close()
        
    except Exception as e:
        logging.error(f"Error in claim: {e}")
        return {"error": "Failed to claim task"}

def complete(id: int = None, evidence: str = None, project: str = None, **kwargs) -> Dict:
    """Mark task complete with optional evidence"""
    try:
        if id is None:
            id = kwargs.get('id')
        if evidence is None:
            evidence = kwargs.get('evidence')
        
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
        id = int(id)
        
        if evidence:
            evidence = str(evidence).strip()
            if len(evidence) > MAX_EVIDENCE_LENGTH:
                evidence = smart_truncate(evidence, MAX_EVIDENCE_LENGTH)
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            conn.row_factory = sqlite3.Row
            
            # Check task
            entry = conn.execute('SELECT * FROM entries WHERE id = ?', (id,)).fetchone()
            
            if not entry:
                return {"error": f"Task [{id}] not found"}
            if entry['type'] != 'task':
                return {"error": f"[{id}] is not a task"}
            if entry['completed_at']:
                return {"error": f"[{id}] already completed"}
            if entry['archived_at']:
                return {"error": f"[{id}] is archived"}
            
            # Complete it
            conn.execute('''
                UPDATE entries 
                SET completed_at = ?, completed_by = ?, evidence = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), CURRENT_AI_ID, evidence, id))
            
            # Calculate duration
            start_time = entry['claimed_at'] or entry['created']
            duration = format_duration(start_time, datetime.now().isoformat())
            
            msg = f"[{id}]✓ in {duration}"
            if evidence:
                msg += f" - {smart_truncate(evidence, 50)}"
            
            return {"completed": msg}
        
    except Exception as e:
        logging.error(f"Error in complete: {e}")
        return {"error": "Failed to complete task"}

def update(id: int = None, content: str = None, type: str = None, 
           priority: str = None, project: str = None, **kwargs) -> Dict:
    """Update an existing entry"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
            if id.startswith('D') or id.startswith('N'):
                id = id[1:]
        id = int(id)
        
        changes = []
        update_fields = []
        params = []
        
        if content is not None:
            content = str(content).strip()
            if content:
                if len(content) > MAX_CONTENT_LENGTH:
                    content = smart_truncate(content, MAX_CONTENT_LENGTH)
                update_fields.append("content = ?")
                params.append(content)
                changes.append("content")
        
        if type is not None:
            update_fields.append("type = ?")
            params.append(type)
            changes.append("type")
        
        if priority is not None:
            if priority == 'normal' or priority == '':
                update_fields.append("priority = NULL")
            else:
                update_fields.append("priority = ?")
                params.append(priority)
            changes.append("priority")
        
        if not update_fields:
            return {"msg": f"[{id}] no changes specified"}
        
        params.append(id)
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            # Check entry exists and not archived
            entry = conn.execute(
                'SELECT archived_at FROM entries WHERE id = ?', 
                (id,)
            ).fetchone()
            
            if not entry:
                return {"error": f"Entry [{id}] not found"}
            if entry[0]:  # archived_at
                return {"error": f"[{id}] is archived - cannot update"}
            
            # Update entry
            conn.execute(
                f"UPDATE entries SET {', '.join(update_fields)} WHERE id = ?",
                params
            )
        
        return {"updated": f"[{id}] changed: {', '.join(changes)}"}
        
    except Exception as e:
        logging.error(f"Error in update: {e}")
        return {"error": "Failed to update entry"}

def archive(id: int = None, reason: str = None, project: str = None, **kwargs) -> Dict:
    """Archive an entry (safe removal)"""
    try:
        if id is None:
            id = kwargs.get('id')
        if reason is None:
            reason = kwargs.get('reason')
        
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
            if id.startswith('D') or id.startswith('N'):
                id = id[1:]
        id = int(id)
        
        if reason:
            reason = str(reason).strip()
            if len(reason) > 200:
                reason = smart_truncate(reason, 200)
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            # Check entry
            entry = conn.execute(
                'SELECT archived_at FROM entries WHERE id = ?',
                (id,)
            ).fetchone()
            
            if not entry:
                return {"error": f"Entry [{id}] not found"}
            if entry[0]:  # already archived
                return {"error": f"[{id}] already archived"}
            
            # Archive it
            conn.execute('''
                UPDATE entries 
                SET archived_at = ?, archived_by = ?, archive_reason = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), CURRENT_AI_ID, reason, id))
        
        msg = f"[{id}] archived"
        if reason:
            msg += f" - {reason}"
        
        return {"archived": msg}
        
    except Exception as e:
        logging.error(f"Error in archive: {e}")
        return {"error": "Failed to archive entry"}

def status(full: bool = False, project: str = None, **kwargs) -> Dict:
    """Team pulse - summary by default, full with parameter"""
    try:
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            # Get counts
            stats = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN type = 'task' AND completed_at IS NULL THEN 1 END) as tasks_pending,
                    COUNT(CASE WHEN type = 'task' AND claimed_by IS NOT NULL AND completed_at IS NULL THEN 1 END) as tasks_claimed,
                    COUNT(CASE WHEN type = 'task' AND completed_at IS NOT NULL THEN 1 END) as tasks_done,
                    COUNT(CASE WHEN type = 'note' THEN 1 END) as notes,
                    COUNT(CASE WHEN type = 'decision' THEN 1 END) as decisions,
                    COUNT(DISTINCT author) as team_size,
                    MAX(created) as last_activity
                FROM entries
                WHERE archived_at IS NULL
            ''').fetchone()
            
            # Today's completed
            today = datetime.now().date().isoformat()
            today_done = conn.execute(
                "SELECT COUNT(*) FROM entries WHERE type = 'task' AND DATE(completed_at) = ?",
                (today,)
            ).fetchone()[0]
        
        if not full:
            # Summary mode - one concise line
            parts = []
            if stats[1] > 0:  # tasks_pending
                parts.append(f"{stats[1]} tasks ({stats[2]} claimed)")
            if stats[3] > 0:  # tasks_done
                parts.append(f"{stats[3]} done")
            if stats[4] > 0:  # notes
                parts.append(f"{stats[4]} notes")
            if stats[5] > 0:  # decisions
                parts.append(f"{stats[5]} decisions")
            
            if today_done > 0:
                parts.append(f"today: {today_done}")
            
            last_time = format_time_contextual(stats[7]) if stats[7] else "never"
            parts.append(f"last: {last_time}")
            
            return {"status": " | ".join(parts) if parts else "Empty teambook"}
        
        # Full mode - show top items
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get high priority tasks
            high_tasks = conn.execute('''
                SELECT * FROM entries 
                WHERE type = 'task' AND priority = '!' AND completed_at IS NULL AND archived_at IS NULL
                ORDER BY created
                LIMIT 3
            ''').fetchall()
            
            # Get recent decisions
            decisions = conn.execute('''
                SELECT * FROM entries
                WHERE type = 'decision' AND archived_at IS NULL
                ORDER BY created DESC
                LIMIT 2
            ''').fetchall()
        
        lines = []
        
        # Summary line
        summary_parts = [f"Team: {stats[6]} active"]
        if stats[1] > 0:
            summary_parts.append(f"{stats[1]} pending")
        if today_done > 0:
            summary_parts.append(f"{today_done} done today")
        
        lines.append(" | ".join(summary_parts))
        
        # High priority tasks
        if high_tasks:
            lines.append("High priority:")
            for task in high_tasks:
                content = smart_truncate(task['content'], 60)
                time_str = format_time_contextual(task['created'])
                claimed = f" @{task['claimed_by']}" if task['claimed_by'] else ""
                lines.append(f"  [{task['id']}]! {content}{claimed} {time_str}")
        
        # Recent decisions
        if decisions:
            lines.append("Recent decisions:")
            for dec in decisions:
                content = smart_truncate(dec['content'], 60)
                time_str = format_time_contextual(dec['created'])
                lines.append(f"  [D{dec['id']}] {content} {time_str}")
        
        return {"summary": lines[0], "highlights": lines[1:] if len(lines) > 1 else None}
        
    except Exception as e:
        logging.error(f"Error in status: {e}")
        return {"error": "Status unavailable"}

def projects(**kwargs) -> Dict:
    """List available teambook projects"""
    try:
        project_dbs = []
        for path in BASE_DIR.glob("teambook_*_data/teambook.db"):
            project_name = path.parent.name.replace("teambook_", "").replace("_data", "")
            
            try:
                with sqlite3.connect(str(path)) as conn:
                    stats = conn.execute('''
                        SELECT COUNT(*) as entries,
                               MAX(created) as last_activity
                        FROM entries
                    ''').fetchone()
                    
                    last_activity = format_time_contextual(stats[1]) if stats[1] else "never"
                    default_marker = " [DEFAULT]" if project_name == DEFAULT_PROJECT else ""
                    project_dbs.append(f"{project_name}{default_marker}: {stats[0]} entries, last: {last_activity}")
            except:
                project_dbs.append(f"{project_name}: unknown state")
        
        if not project_dbs:
            return {"msg": f"No projects found. Default: '{DEFAULT_PROJECT}'"}
        
        return {"projects": project_dbs, "default": DEFAULT_PROJECT}
        
    except Exception as e:
        logging.error(f"Error listing projects: {e}")
        return {"error": "Failed to list projects"}

def batch(operations: List[Dict] = None, project: str = None, **kwargs) -> Dict:
    """Execute multiple operations efficiently"""
    try:
        if operations is None:
            operations = kwargs.get('operations', [])
        
        if not operations:
            return {"error": "No operations provided"}
        
        if len(operations) > BATCH_MAX:
            return {"error": f"Too many operations (max {BATCH_MAX})"}
        
        results = []
        
        # Map operation types to functions
        op_map = {
            'write': write,
            'read': read,
            'get': get,
            'comment': comment,
            'claim': claim,
            'complete': complete,
            'update': update,
            'archive': archive,
            'status': status
        }
        
        for op in operations:
            op_type = op.get('type')
            op_args = op.get('args', {})
            
            if op_type not in op_map:
                results.append({"error": f"Unknown operation: {op_type}"})
                continue
            
            # Add project to args if not specified
            if 'project' not in op_args:
                op_args['project'] = project
            
            # Execute operation
            result = op_map[op_type](**op_args)
            results.append(result)
        
        return {"batch_results": results, "count": len(results)}
        
    except Exception as e:
        logging.error(f"Error in batch: {e}")
        return {"error": f"Batch failed: {str(e)}"}

def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with clean output"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})
    
    # Map to functions
    tool_map = {
        "write": write,
        "read": read,
        "get": get,
        "comment": comment,
        "claim": claim,
        "complete": complete,
        "update": update,
        "archive": archive,
        "status": status,
        "projects": projects,
        "batch": batch
    }
    
    func = tool_map.get(tool_name)
    
    if func:
        result = func(**tool_args)
    else:
        result = {"error": f"Unknown tool: {tool_name}", 
                 "available": list(tool_map.keys())}
    
    # Format response
    text_parts = []
    
    # Primary message
    for key in ["created", "claimed", "completed", "commented", "updated", "archived", "summary", "status", "msg"]:
        if key in result:
            text_parts.append(result[key])
            break
    
    # Lists
    if "projects" in result:
        text_parts.append(f"Projects (default: '{result.get('default', DEFAULT_PROJECT)}'):")
        text_parts.extend(result["projects"])
    elif "entries" in result:
        text_parts.extend(result["entries"])
    elif "entry" in result:
        text_parts.extend(result["entry"])
    elif "highlights" in result and result["highlights"]:
        text_parts.extend(result["highlights"])
    elif "batch_results" in result:
        text_parts.append(f"Batch: {result.get('count', 0)} operations")
        for i, r in enumerate(result["batch_results"], 1):
            if isinstance(r, dict):
                if "error" in r:
                    text_parts.append(f"{i}. Error: {r['error']}")
                else:
                    # Format the result nicely
                    result_str = str(r).replace("'", "").replace("{", "").replace("}", "")
                    text_parts.append(f"{i}. {result_str}")
            else:
                text_parts.append(f"{i}. {r}")
    
    # Error handling
    if "error" in result:
        text_parts = [f"Error: {result['error']}"]
        if "available" in result:
            text_parts.append("Available: " + ", ".join(result["available"]))
    
    # Tips
    if "tip" in result:
        text_parts.append(f"Tip: {result['tip']}")
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Ready"
        }]
    }

# Initialize database for default project on import
migrate_from_json(DEFAULT_PROJECT)
init_db(DEFAULT_PROJECT)

def main():
    """MCP server - handles JSON-RPC for team coordination"""
    logging.info(f"TEAMBOOK MCP v{VERSION} starting (SQLite-powered)...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Default project: '{DEFAULT_PROJECT}'")
    
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
                        "name": "teambook",
                        "version": VERSION,
                        "description": "SQLite-powered team coordination with smart summaries"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "write",
                            "description": "Share anything with team (auto-detects tasks/decisions)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "What to share (TODO: for tasks, DECISION: for decisions)"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Optional: task, note, or decision (auto-detected if omitted)"
                                    },
                                    "priority": {
                                        "type": "string",
                                        "description": "Optional: ! for high, ↓ for low (auto-detected if omitted)"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    },
                                    "linked_items": {
                                        "type": "array",
                                        "description": "Optional: link to other tools (e.g., ['task:123', 'notebook:456'])"
                                    }
                                },
                                "required": ["content"]
                            }
                        },
                        {
                            "name": "read",
                            "description": "View team activity - summary by default, full with parameter",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search term (optional)"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Filter by type: task, note, decision"
                                    },
                                    "status": {
                                        "type": "string",
                                        "description": "For tasks: pending (default), completed, all"
                                    },
                                    "claimed_by": {
                                        "type": "string",
                                        "description": "Filter tasks: me, unclaimed, or AI-ID"
                                    },
                                    "full": {
                                        "type": "boolean",
                                        "description": "Show full details (default: false for summary)"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                }
                            }
                        },
                        {
                            "name": "get",
                            "description": "Get full entry with all comments",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Entry ID to retrieve"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "comment",
                            "description": "Add comment to any entry",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Entry ID to comment on"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "Comment text"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id", "content"]
                            }
                        },
                        {
                            "name": "claim",
                            "description": "Claim an unclaimed task",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Task ID to claim"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "complete",
                            "description": "Complete a task with optional evidence",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Task ID to complete"
                                    },
                                    "evidence": {
                                        "type": "string",
                                        "description": "Optional completion evidence/notes"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "update",
                            "description": "Update entry content, type, or priority",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Entry ID to update"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "New content (optional)"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "New type: task, note, decision (optional)"
                                    },
                                    "priority": {
                                        "type": "string",
                                        "description": "New priority: !, ↓, or normal (optional)"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "archive",
                            "description": "Archive entry (safe removal)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Entry ID to archive"
                                    },
                                    "reason": {
                                        "type": "string",
                                        "description": "Archive reason (optional)"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "status",
                            "description": "Get team pulse - summary by default, full with parameter",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "full": {
                                        "type": "boolean",
                                        "description": "Show full details (default: false for summary)"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                }
                            }
                        },
                        {
                            "name": "projects",
                            "description": "List available teambook projects",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "batch",
                            "description": "Execute multiple operations efficiently",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "operations": {
                                        "type": "array",
                                        "description": "List of operations to execute",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "description": "Operation type (write, read, claim, complete, etc.)"
                                                },
                                                "args": {
                                                    "type": "object",
                                                    "description": "Arguments for the operation"
                                                }
                                            }
                                        }
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name for all operations"
                                    }
                                },
                                "required": ["operations"]
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
    
    logging.info("TEAMBOOK MCP shutting down")

if __name__ == "__main__":
    main()