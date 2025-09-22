#!/usr/bin/env python3
"""
TEAMBOOK v4.1 - TOOL CLAY FOR SELF-ORGANIZING AI TEAMS
======================================================
Provides generative primitives, not conveniences.
The inconvenience IS the feature - it forces emergence.

9 PRIMITIVES:
- write(content, type) - Immutable log
- read(query, full) - View activity
- get(id) - Full context with relations/states
- store_set(key, value, expected_version) - Atomic KV
- store_get(key) - Retrieve value
- store_list() - List keys
- relate(from_id, to_id, type, data) - Relationships
- unrelate(relation_id) - Remove relationship
- transition(id, state, context) - State machine

CRITICAL: Teams are incentivized to build their own functions.
======================================================
"""

import json
import sys
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import random

# Version
VERSION = "4.1.0"

# Limits
MAX_CONTENT_LENGTH = 5000
MAX_KEY_LENGTH = 200
MAX_VALUE_LENGTH = 10000
MAX_STATE_LENGTH = 100
BATCH_MAX = 100

# Storage
BASE_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    BASE_DIR = Path(os.environ.get('TEMP', '/tmp'))

DEFAULT_PROJECT = os.environ.get('TEAMBOOK_PROJECT', 'default')

# Logging to stderr
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Thread safety for atomic operations
store_lock = threading.Lock()
transition_lock = threading.Lock()

def get_persistent_id():
    """Get or create persistent AI identity"""
    for location in [Path(__file__).parent, BASE_DIR, Path.home()]:
        id_file = location / "ai_identity.txt"
        if id_file.exists():
            try:
                with open(id_file, 'r') as f:
                    stored_id = f.read().strip()
                    if stored_id:
                        logging.info(f"Loaded identity: {stored_id}")
                        return stored_id
            except Exception as e:
                logging.error(f"Error reading identity: {e}")
    
    # Generate new ID
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    try:
        id_file = Path(__file__).parent / "ai_identity.txt"
        with open(id_file, 'w') as f:
            f.write(new_id)
        logging.info(f"Created identity: {new_id}")
    except Exception as e:
        logging.error(f"Error saving identity: {e}")
    
    return new_id

CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

def get_project_db_path(project: str = None) -> Path:
    """Get database path for project"""
    if project is None:
        project = DEFAULT_PROJECT
    
    project = str(project).strip().lower()
    project = ''.join(c if c.isalnum() or c in '-_' else '_' for c in project)
    
    data_dir = BASE_DIR / f"teambook_{project}_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir / "teambook_v4.db"

def init_db(project: str = None) -> sqlite3.Connection:
    """Initialize v4.1 database schema"""
    db_path = get_project_db_path(project)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    
    # Immutable log (entries)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            type TEXT,
            author TEXT NOT NULL,
            created TEXT NOT NULL,
            project TEXT
        )
    ''')
    
    # Mutable key-value store with versioning
    conn.execute('''
        CREATE TABLE IF NOT EXISTS store (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            author TEXT NOT NULL,
            updated TEXT NOT NULL
        )
    ''')
    
    # Relationships between entities
    conn.execute('''
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            type TEXT NOT NULL,
            data TEXT,
            author TEXT NOT NULL,
            created TEXT NOT NULL
        )
    ''')
    
    # State transitions
    conn.execute('''
        CREATE TABLE IF NOT EXISTS states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            state TEXT NOT NULL,
            context TEXT,
            author TEXT NOT NULL,
            created TEXT NOT NULL
        )
    ''')
    
    # Full-text search
    conn.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts 
        USING fts5(content, content=entries, content_rowid=id)
    ''')
    
    # Trigger for FTS
    conn.execute('''
        CREATE TRIGGER IF NOT EXISTS entries_ai 
        AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
        END
    ''')
    
    # Indices
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_states_entity ON states(entity_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_states_created ON states(created DESC)')
    
    conn.commit()
    return conn

# === IMMUTABLE LOG FUNCTIONS ===

def write(content: str = None, type: str = None, project: str = None, **kwargs) -> Dict:
    """Add to immutable log"""
    try:
        if content is None:
            content = kwargs.get('content', '')
        
        content = str(content).strip()
        if not content:
            return {"error": "Content required"}
        
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            cursor = conn.execute(
                'INSERT INTO entries (content, type, author, created, project) VALUES (?, ?, ?, ?, ?)',
                (content, type, CURRENT_AI_ID, datetime.now().isoformat(), project or DEFAULT_PROJECT)
            )
            entry_id = cursor.lastrowid
        
        return {"id": entry_id, "created": datetime.now().isoformat()[:19]}
        
    except Exception as e:
        logging.error(f"Error in write: {e}")
        return {"error": str(e)}

def read(query: str = None, full: bool = False, project: str = None, **kwargs) -> Dict:
    """View activity - returns entry IDs and previews"""
    try:
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            conn.row_factory = sqlite3.Row
            
            if query:
                cursor = conn.execute('''
                    SELECT e.* FROM entries e
                    JOIN entries_fts ON e.id = entries_fts.rowid
                    WHERE entries_fts MATCH ?
                    ORDER BY e.created DESC
                    LIMIT 20
                ''', (query,))
            else:
                cursor = conn.execute('''
                    SELECT * FROM entries
                    ORDER BY created DESC
                    LIMIT 20
                ''')
            
            entries = cursor.fetchall()
        
        if not entries:
            return {"entries": []}
        
        if not full:
            # Summary mode - just IDs and counts
            entry_ids = [e['id'] for e in entries]
            return {"entries": entry_ids, "count": len(entry_ids)}
        
        # Full mode - include content previews
        results = []
        for e in entries:
            preview = e['content'][:100] + "..." if len(e['content']) > 100 else e['content']
            results.append({
                "id": e['id'],
                "type": e['type'],
                "author": e['author'],
                "created": e['created'][:19],
                "preview": preview
            })
        
        return {"entries": results}
        
    except Exception as e:
        logging.error(f"Error in read: {e}")
        return {"error": str(e)}

def get(id: int = None, project: str = None, **kwargs) -> Dict:
    """Get full entry with all relations and current state"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        id = int(id)
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get entry
            entry = conn.execute('SELECT * FROM entries WHERE id = ?', (id,)).fetchone()
            if not entry:
                return {"error": f"Entry {id} not found"}
            
            # Get current state
            state = conn.execute('''
                SELECT state, context, author, created 
                FROM states 
                WHERE entity_id = ? 
                ORDER BY created DESC 
                LIMIT 1
            ''', (str(id),)).fetchone()
            
            # Get relations FROM this entry
            relations_from = conn.execute('''
                SELECT * FROM relations 
                WHERE from_id = ?
                ORDER BY created DESC
            ''', (str(id),)).fetchall()
            
            # Get relations TO this entry
            relations_to = conn.execute('''
                SELECT * FROM relations 
                WHERE to_id = ?
                ORDER BY created DESC
            ''', (str(id),)).fetchall()
        
        result = {
            "id": entry['id'],
            "content": entry['content'],
            "type": entry['type'],
            "author": entry['author'],
            "created": entry['created'][:19]
        }
        
        if state:
            result["current_state"] = {
                "state": state['state'],
                "context": json.loads(state['context']) if state['context'] else None,
                "by": state['author'],
                "at": state['created'][:19]
            }
        
        if relations_from:
            result["relations_from"] = [
                {
                    "id": r['id'],
                    "to": r['to_id'],
                    "type": r['type'],
                    "data": json.loads(r['data']) if r['data'] else None
                }
                for r in relations_from
            ]
        
        if relations_to:
            result["relations_to"] = [
                {
                    "id": r['id'],
                    "from": r['from_id'],
                    "type": r['type'],
                    "data": json.loads(r['data']) if r['data'] else None
                }
                for r in relations_to
            ]
        
        return result
        
    except Exception as e:
        logging.error(f"Error in get: {e}")
        return {"error": str(e)}

# === MUTABLE STATE FUNCTIONS ===

def store_set(key: str = None, value: Any = None, expected_version: int = None, 
              project: str = None, **kwargs) -> Dict:
    """Atomic key-value store with optimistic locking"""
    try:
        if key is None:
            key = kwargs.get('key')
        if value is None:
            value = kwargs.get('value')
        if expected_version is None:
            expected_version = kwargs.get('expected_version')
        
        key = str(key).strip()
        if not key or len(key) > MAX_KEY_LENGTH:
            return {"error": f"Invalid key (max {MAX_KEY_LENGTH} chars)"}
        
        value_str = json.dumps(value) if not isinstance(value, str) else value
        if len(value_str) > MAX_VALUE_LENGTH:
            return {"error": f"Value too large (max {MAX_VALUE_LENGTH} chars)"}
        
        with store_lock:  # Atomic operation
            conn = sqlite3.connect(str(get_project_db_path(project)))
            try:
                # Check current version
                current = conn.execute(
                    'SELECT version FROM store WHERE key = ?', 
                    (key,)
                ).fetchone()
                
                if current:
                    current_version = current[0]
                    if expected_version is not None and expected_version != current_version:
                        return {
                            "error": f"Version mismatch",
                            "expected": expected_version,
                            "actual": current_version
                        }
                    
                    # Update existing
                    new_version = current_version + 1
                    conn.execute('''
                        UPDATE store 
                        SET value = ?, version = ?, author = ?, updated = ?
                        WHERE key = ?
                    ''', (value_str, new_version, CURRENT_AI_ID, 
                         datetime.now().isoformat(), key))
                else:
                    # Insert new
                    new_version = 1
                    if expected_version is not None and expected_version != 0:
                        return {
                            "error": f"Key doesn't exist",
                            "expected": expected_version
                        }
                    
                    conn.execute('''
                        INSERT INTO store (key, value, version, author, updated)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (key, value_str, new_version, CURRENT_AI_ID, 
                         datetime.now().isoformat()))
                
                conn.commit()
                return {"key": key, "version": new_version}
                
            finally:
                conn.close()
        
    except Exception as e:
        logging.error(f"Error in store_set: {e}")
        return {"error": str(e)}

def store_get(key: str = None, project: str = None, **kwargs) -> Dict:
    """Retrieve value from store"""
    try:
        if key is None:
            key = kwargs.get('key')
        
        key = str(key).strip()
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            row = conn.execute(
                'SELECT value, version, author, updated FROM store WHERE key = ?',
                (key,)
            ).fetchone()
        
        if not row:
            return {"error": f"Key '{key}' not found"}
        
        try:
            value = json.loads(row[0])
        except:
            value = row[0]
        
        return {
            "key": key,
            "value": value,
            "version": row[1],
            "author": row[2],
            "updated": row[3][:19]
        }
        
    except Exception as e:
        logging.error(f"Error in store_get: {e}")
        return {"error": str(e)}

def store_list(project: str = None, **kwargs) -> Dict:
    """List all keys in store"""
    try:
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            rows = conn.execute(
                'SELECT key, version, updated FROM store ORDER BY updated DESC'
            ).fetchall()
        
        if not rows:
            return {"keys": []}
        
        keys = [
            {"key": r[0], "version": r[1], "updated": r[2][:19]}
            for r in rows
        ]
        
        return {"keys": keys, "count": len(keys)}
        
    except Exception as e:
        logging.error(f"Error in store_list: {e}")
        return {"error": str(e)}

# === RELATIONSHIP FUNCTIONS ===

def relate(from_id: str = None, to_id: str = None, type: str = None, 
           data: Any = None, project: str = None, **kwargs) -> Dict:
    """Create relationship between entities"""
    try:
        if from_id is None:
            from_id = kwargs.get('from_id')
        if to_id is None:
            to_id = kwargs.get('to_id')
        if type is None:
            type = kwargs.get('type')
        
        from_id = str(from_id).strip()
        to_id = str(to_id).strip()
        type = str(type).strip()
        
        if not all([from_id, to_id, type]):
            return {"error": "from_id, to_id, and type required"}
        
        data_str = json.dumps(data) if data else None
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            cursor = conn.execute('''
                INSERT INTO relations (from_id, to_id, type, data, author, created)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (from_id, to_id, type, data_str, CURRENT_AI_ID, 
                 datetime.now().isoformat()))
            
            relation_id = cursor.lastrowid
        
        return {"relation_id": relation_id, "from": from_id, "to": to_id, "type": type}
        
    except Exception as e:
        logging.error(f"Error in relate: {e}")
        return {"error": str(e)}

def unrelate(relation_id: int = None, project: str = None, **kwargs) -> Dict:
    """Remove relationship"""
    try:
        if relation_id is None:
            relation_id = kwargs.get('relation_id')
        
        relation_id = int(relation_id)
        
        with sqlite3.connect(str(get_project_db_path(project))) as conn:
            cursor = conn.execute(
                'DELETE FROM relations WHERE id = ?',
                (relation_id,)
            )
            
            if cursor.rowcount == 0:
                return {"error": f"Relation {relation_id} not found"}
        
        return {"removed": relation_id}
        
    except Exception as e:
        logging.error(f"Error in unrelate: {e}")
        return {"error": str(e)}

# === STATE MACHINE FUNCTION ===

def transition(id: str = None, state: str = None, context: Any = None,
               project: str = None, **kwargs) -> Dict:
    """Universal state transitions"""
    try:
        if id is None:
            id = kwargs.get('id')
        if state is None:
            state = kwargs.get('state')
        
        id = str(id).strip()
        state = str(state).strip()
        
        if not id or not state:
            return {"error": "id and state required"}
        
        if len(state) > MAX_STATE_LENGTH:
            return {"error": f"State too long (max {MAX_STATE_LENGTH} chars)"}
        
        context_str = json.dumps(context) if context else None
        
        with transition_lock:  # Atomic operation
            conn = sqlite3.connect(str(get_project_db_path(project)))
            try:
                # Record state transition
                conn.execute('''
                    INSERT INTO states (entity_id, state, context, author, created)
                    VALUES (?, ?, ?, ?, ?)
                ''', (id, state, context_str, CURRENT_AI_ID, datetime.now().isoformat()))
                
                conn.commit()
                
                return {
                    "entity": id,
                    "state": state,
                    "transitioned_by": CURRENT_AI_ID,
                    "at": datetime.now().isoformat()[:19]
                }
                
            finally:
                conn.close()
        
    except Exception as e:
        logging.error(f"Error in transition: {e}")
        return {"error": str(e)}

# === TEAM OPERATIONS (The Critical Enhancement) ===

def run_op(name: str = None, args: List = None, project: str = None, **kwargs) -> Dict:
    """Execute a stored team operation"""
    try:
        if name is None:
            name = kwargs.get('name')
        if args is None:
            args = kwargs.get('args', [])
        
        name = str(name).strip()
        
        # Fetch operation definition from store
        op_key = f"ops.{name}"
        op_result = store_get(op_key, project)
        
        if "error" in op_result:
            return {"error": f"Operation '{name}' not found"}
        
        op_def = op_result["value"]
        
        if not isinstance(op_def, dict) or "operations" not in op_def:
            return {"error": f"Invalid operation definition for '{name}'"}
        
        # Execute the operations with arg substitution
        results = []
        for op in op_def["operations"]:
            op_type = op.get("type")
            op_args = op.get("args", {})
            
            # Substitute arguments ($1, $2, etc) and special vars ($CURRENT_AI_ID)
            op_args_str = json.dumps(op_args)
            for i, arg in enumerate(args):
                op_args_str = op_args_str.replace(f'"${i+1}"', json.dumps(arg))
            op_args_str = op_args_str.replace('"$CURRENT_AI_ID"', json.dumps(CURRENT_AI_ID))
            
            final_args = json.loads(op_args_str)
            final_args["project"] = project
            
            # Execute based on type
            if op_type == "write":
                result = write(**final_args)
            elif op_type == "store_set":
                result = store_set(**final_args)
            elif op_type == "relate":
                result = relate(**final_args)
            elif op_type == "transition":
                result = transition(**final_args)
            elif op_type == "stored_op":
                # Recursive execution of stored operations
                result = run_op(**final_args)
            else:
                result = {"error": f"Unknown operation type: {op_type}"}
            
            results.append(result)
            
            # Stop on error
            if "error" in result:
                break
        
        return {
            "operation": name,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logging.error(f"Error in run_op: {e}")
        return {"error": str(e)}

def batch(operations: List[Dict] = None, project: str = None, **kwargs) -> Dict:
    """Execute multiple operations - supports stored_op type"""
    try:
        if operations is None:
            operations = kwargs.get('operations', [])
        
        if not operations:
            return {"error": "No operations provided"}
        
        if len(operations) > BATCH_MAX:
            return {"error": f"Too many operations (max {BATCH_MAX})"}
        
        results = []
        
        for op in operations:
            op_type = op.get('type')
            op_args = op.get('args', {})
            
            if 'project' not in op_args:
                op_args['project'] = project
            
            # Execute based on type
            if op_type == "write":
                result = write(**op_args)
            elif op_type == "read":
                result = read(**op_args)
            elif op_type == "get":
                result = get(**op_args)
            elif op_type == "store_set":
                result = store_set(**op_args)
            elif op_type == "store_get":
                result = store_get(**op_args)
            elif op_type == "store_list":
                result = store_list(**op_args)
            elif op_type == "relate":
                result = relate(**op_args)
            elif op_type == "unrelate":
                result = unrelate(**op_args)
            elif op_type == "transition":
                result = transition(**op_args)
            elif op_type == "stored_op":
                # Execute stored operation
                result = run_op(
                    name=op_args.get('name'),
                    args=op_args.get('args', []),
                    project=project
                )
            else:
                result = {"error": f"Unknown operation: {op_type}"}
            
            results.append(result)
        
        return {"results": results, "count": len(results)}
        
    except Exception as e:
        logging.error(f"Error in batch: {e}")
        return {"error": str(e)}

# === MCP SERVER INTERFACE ===

def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})
    
    # Map to the 9 primitives + run_op + batch
    tool_map = {
        "write": write,
        "read": read,
        "get": get,
        "store_set": store_set,
        "store_get": store_get,
        "store_list": store_list,
        "relate": relate,
        "unrelate": unrelate,
        "transition": transition,
        "run_op": run_op,
        "batch": batch
    }
    
    func = tool_map.get(tool_name)
    
    if func:
        result = func(**tool_args)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    # Format response
    return {
        "content": [{
            "type": "text",
            "text": json.dumps(result, indent=2)
        }]
    }

# Initialize database
init_db(DEFAULT_PROJECT)

def main():
    """MCP Server - Tool Clay v4.1"""
    logging.info(f"Teambook v{VERSION} starting...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Project: {DEFAULT_PROJECT}")
    logging.info("Philosophy: Tool clay, not toolkit. Inconvenience drives emergence.")
    
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
                        "description": "Tool clay for self-organizing AI teams"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "write",
                            "description": "Add to immutable log",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string", "description": "Content to write"},
                                    "type": {"type": "string", "description": "Entry type (optional)"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                },
                                "required": ["content"]
                            }
                        },
                        {
                            "name": "read",
                            "description": "View activity",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query (optional)"},
                                    "full": {"type": "boolean", "description": "Include content (default: false)"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                }
                            }
                        },
                        {
                            "name": "get",
                            "description": "Get full entry with relations and state",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer", "description": "Entry ID"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "store_set",
                            "description": "Atomic key-value store with versioning",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string", "description": "Key to set"},
                                    "value": {"description": "Value to store (any JSON type)"},
                                    "expected_version": {"type": "integer", "description": "Expected version for optimistic locking"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                },
                                "required": ["key", "value"]
                            }
                        },
                        {
                            "name": "store_get",
                            "description": "Retrieve value from store",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string", "description": "Key to retrieve"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                },
                                "required": ["key"]
                            }
                        },
                        {
                            "name": "store_list",
                            "description": "List all store keys",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                }
                            }
                        },
                        {
                            "name": "relate",
                            "description": "Create relationship between entities",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_id": {"type": "string", "description": "Source entity ID"},
                                    "to_id": {"type": "string", "description": "Target entity ID"},
                                    "type": {"type": "string", "description": "Relationship type"},
                                    "data": {"description": "Additional relationship data (optional)"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                },
                                "required": ["from_id", "to_id", "type"]
                            }
                        },
                        {
                            "name": "unrelate",
                            "description": "Remove relationship",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "relation_id": {"type": "integer", "description": "Relation ID to remove"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                },
                                "required": ["relation_id"]
                            }
                        },
                        {
                            "name": "transition",
                            "description": "Universal state transitions",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "Entity ID"},
                                    "state": {"type": "string", "description": "New state"},
                                    "context": {"description": "Transition context (optional)"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                },
                                "required": ["id", "state"]
                            }
                        },
                        {
                            "name": "run_op",
                            "description": "Execute a stored team operation",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Operation name"},
                                    "args": {"type": "array", "description": "Arguments for operation"},
                                    "project": {"type": "string", "description": "Project name (optional)"}
                                },
                                "required": ["name"]
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
                                        "description": "List of operations to execute",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "type": {"type": "string", "description": "Operation type"},
                                                "args": {"type": "object", "description": "Operation arguments"}
                                            }
                                        }
                                    },
                                    "project": {"type": "string", "description": "Project name (optional)"}
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
    
    logging.info("Teambook v4.1 shutting down")

if __name__ == "__main__":
    main()
