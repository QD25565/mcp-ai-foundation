#!/usr/bin/env python3
"""
NOTEBOOK MCP v2.0.0 - PERSISTENT MEMORY WITH VAULT
==================================================
Scalable AI memory with SQLite, secure vault, and smart summaries.
General-purpose tool for all AIs - simple, intuitive, empowering.

Core functions:
- remember(content) - Save thoughts/notes (searchable, up to 5000 chars)
- recall(query, full=False) - Search with optional full details
- get_status(full=False) - Current state with smart summary
- get_full_note(id) - Retrieve complete note content
- vault_store(key, value) - Secure encrypted storage
- vault_retrieve(key) - Get secret value
- vault_list() - List vault keys (not values)
- batch(operations) - Execute multiple operations efficiently
==================================================
"""

import json
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import random
import hashlib
from cryptography.fernet import Fernet
import base64

# Version
VERSION = "2.0.0"

# Limits
MAX_CONTENT_LENGTH = 5000
MAX_PREVIEW_LENGTH = 500
MAX_RESULTS = 100
BATCH_MAX = 50

# Storage paths
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "notebook_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "notebook_data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "notebook.db"
OLD_JSON_FILE = DATA_DIR / "notebook.json"
VAULT_KEY_FILE = DATA_DIR / ".vault_key"  # Hidden file for vault key

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global session info
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

def get_persistent_id():
    """Get or create persistent AI identity"""
    # Try multiple locations for robustness
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
    
    # Generate new readable ID
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep', 'Keen', 'Pure']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node', 'Wave', 'Link']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    # Save to script directory (most persistent location)
    try:
        id_file = Path(__file__).parent / "ai_identity.txt"
        with open(id_file, 'w') as f:
            f.write(new_id)
        logging.info(f"Created new identity: {new_id}")
    except Exception as e:
        logging.error(f"Error saving identity: {e}")
    
    return new_id

# Get AI identity
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

class VaultManager:
    """Secure encrypted storage for secrets"""
    
    def __init__(self):
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)
    
    def _load_or_create_key(self) -> bytes:
        """Load existing key or create new one"""
        if VAULT_KEY_FILE.exists():
            with open(VAULT_KEY_FILE, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            # Save with restricted permissions if possible
            with open(VAULT_KEY_FILE, 'wb') as f:
                f.write(key)
            try:
                # Try to restrict file permissions (Unix-like systems)
                import stat
                os.chmod(VAULT_KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
            except:
                pass
            logging.info("Created new vault key")
            return key
    
    def encrypt(self, value: str) -> bytes:
        """Encrypt a string value"""
        return self.fernet.encrypt(value.encode())
    
    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt to string"""
        return self.fernet.decrypt(encrypted).decode()

# Initialize vault
vault_manager = VaultManager()

def init_db():
    """Initialize SQLite database with all tables"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    
    # Main notes table with FTS5 for fast search
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            created TEXT NOT NULL,
            session TEXT,
            linked_items TEXT
        )
    ''')
    
    # Full-text search virtual table
    conn.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts 
        USING fts5(content, content=notes, content_rowid=id)
    ''')
    
    # Trigger to keep FTS in sync
    conn.execute('''
        CREATE TRIGGER IF NOT EXISTS notes_ai 
        AFTER INSERT ON notes BEGIN
            INSERT INTO notes_fts(rowid, content) VALUES (new.id, new.content);
        END
    ''')
    
    # Vault table for encrypted storage
    conn.execute('''
        CREATE TABLE IF NOT EXISTS vault (
            key TEXT PRIMARY KEY,
            encrypted_value BLOB NOT NULL,
            created TEXT NOT NULL,
            updated TEXT NOT NULL,
            author TEXT NOT NULL
        )
    ''')
    
    # Stats table for metrics
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
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_vault_updated ON vault(updated DESC)')
    
    conn.commit()
    return conn

def migrate_from_json():
    """One-time migration from JSON to SQLite"""
    if not OLD_JSON_FILE.exists() or DB_FILE.exists():
        return
    
    logging.info("Migrating from JSON to SQLite...")
    try:
        with open(OLD_JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = init_db()
        notes = data.get("notes", [])
        
        for note in notes:
            conn.execute(
                'INSERT INTO notes (content, author, created, session) VALUES (?, ?, ?, ?)',
                (note.get("c", ""), note.get("author", "Unknown"), 
                 note.get("t", datetime.now().isoformat()), note.get("sess"))
            )
        
        conn.commit()
        conn.close()
        
        # Rename old file to backup
        OLD_JSON_FILE.rename(OLD_JSON_FILE.with_suffix('.json.backup'))
        logging.info(f"Migrated {len(notes)} notes to SQLite")
    except Exception as e:
        logging.error(f"Migration failed: {e}")

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

def smart_truncate(text: str, max_chars: int, highlight: str = None) -> str:
    """Intelligent truncation with optional highlight preservation"""
    if len(text) <= max_chars:
        return text
    
    # If highlighting a search term, center around it
    if highlight and highlight.lower() in text.lower():
        idx = text.lower().find(highlight.lower())
        # Show context around match
        start = max(0, idx - max_chars//3)
        end = min(len(text), start + max_chars)
        excerpt = text[start:end]
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."
        return excerpt
    
    # Otherwise, smart truncate from beginning
    code_indicators = ['```', 'def ', 'class ', 'function', 'import ', '{', '}']
    is_code = any(ind in text[:200] for ind in code_indicators)
    
    if is_code and max_chars > 100:
        # For code: show start and end
        start_chars = int(max_chars * 0.65)
        end_chars = max_chars - start_chars - 5
        return text[:start_chars] + "\n...\n" + text[-end_chars:]
    else:
        # For prose: clean word boundary
        cutoff = text.rfind(' ', 0, max_chars - 3)
        if cutoff == -1 or cutoff < max_chars * 0.8:
            cutoff = max_chars - 3
        return text[:cutoff] + "..."

def log_operation(operation: str, duration_ms: int = None):
    """Log operation for stats tracking"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.execute(
                'INSERT INTO stats (operation, timestamp, duration_ms, author) VALUES (?, ?, ?, ?)',
                (operation, datetime.now().isoformat(), duration_ms, CURRENT_AI_ID)
            )
    except:
        pass  # Stats are non-critical

def remember(content: str = None, linked_items: List[str] = None, **kwargs) -> Dict:
    """Save a note with optional cross-tool links"""
    try:
        start = datetime.now()
        
        if content is None:
            content = kwargs.get('content', '')
        
        content = str(content).strip()
        if not content:
            content = f"[checkpoint {datetime.now().strftime('%H:%M')}]"
        
        # Handle truncation
        truncated = False
        original_length = len(content)
        if original_length > MAX_CONTENT_LENGTH:
            content = smart_truncate(content, MAX_CONTENT_LENGTH)
            truncated = True
        
        # Store note
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute(
                '''INSERT INTO notes (content, author, created, session, linked_items) 
                   VALUES (?, ?, ?, ?, ?)''',
                (content, CURRENT_AI_ID, datetime.now().isoformat(), session_id,
                 json.dumps(linked_items) if linked_items else None)
            )
            note_id = cursor.lastrowid
        
        # Log stats
        duration = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('remember', duration)
        
        # Return result
        preview = smart_truncate(content, 80)
        result = {"saved": f"[{note_id}] {preview}"}
        if truncated:
            result["truncated"] = f"from {original_length} chars"
        
        return result
        
    except Exception as e:
        logging.error(f"Error in remember: {e}")
        return {"error": f"Failed to save: {str(e)}"}

def recall(query: str = None, full: bool = False, limit: int = 10, **kwargs) -> Dict:
    """Search notes with summary or full mode"""
    try:
        start = datetime.now()
        
        if query:
            query = str(query).strip()
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            if query:
                # Use FTS5 for fast search
                cursor = conn.execute('''
                    SELECT n.* FROM notes n
                    JOIN notes_fts ON n.id = notes_fts.rowid
                    WHERE notes_fts MATCH ?
                    ORDER BY n.created DESC
                    LIMIT ?
                ''', (query, limit))
            else:
                # Recent notes
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    ORDER BY created DESC 
                    LIMIT ?
                ''', (limit,))
            
            notes = cursor.fetchall()
        
        if not notes:
            return {"msg": f"No matches for '{query}'" if query else "No notes yet"}
        
        # Format results based on mode
        if full:
            # Full details mode
            results = []
            for note in notes:
                author_str = f"@{note['author']}" if note['author'] != CURRENT_AI_ID else ""
                time_str = format_time_contextual(note['created'])
                
                if query:
                    # Highlight search term
                    content = smart_truncate(note['content'], 200, highlight=query)
                else:
                    content = smart_truncate(note['content'], 200)
                
                results.append(f"[{note['id']}]{author_str} {time_str}: {content}")
            
            return {"found": len(notes), "results": results}
        else:
            # Summary mode (default) - ultra-compact
            return {"summary": f"{len(notes)} notes" + (f" matching '{query}'" if query else " recent")}
        
    except Exception as e:
        logging.error(f"Error in recall: {e}")
        return {"error": f"Search failed: {str(e)}"}

def get_status(full: bool = False, **kwargs) -> Dict:
    """Get current state - summary by default, full with parameter"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            # Get counts
            total_notes = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            my_notes = conn.execute('SELECT COUNT(*) FROM notes WHERE author = ?', 
                                   (CURRENT_AI_ID,)).fetchone()[0]
            vault_items = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
            
            # Recent activity
            recent = conn.execute('''
                SELECT created FROM notes 
                ORDER BY created DESC 
                LIMIT 1
            ''').fetchone()
            
            last_activity = format_time_contextual(recent[0]) if recent else "never"
        
        if not full:
            # Summary mode - one line
            return {"status": f"Notes: {total_notes} (you: {my_notes}) | Vault: {vault_items} | Last: {last_activity}"}
        else:
            # Full mode - show recent notes
            with sqlite3.connect(str(DB_FILE)) as conn:
                conn.row_factory = sqlite3.Row
                recent_notes = conn.execute('''
                    SELECT * FROM notes 
                    ORDER BY created DESC 
                    LIMIT 5
                ''').fetchall()
            
            notes_preview = []
            for note in recent_notes:
                author_str = f"@{note['author']}" if note['author'] != CURRENT_AI_ID else ""
                time_str = format_time_contextual(note['created'])
                content = smart_truncate(note['content'], 100)
                notes_preview.append(f"[{note['id']}]{author_str} {time_str}: {content}")
            
            return {
                "summary": f"Notes: {total_notes} | Vault: {vault_items}",
                "identity": CURRENT_AI_ID,
                "recent": notes_preview
            }
        
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {"error": f"Status failed: {str(e)}"}

def get_full_note(id: int = None, **kwargs) -> Dict:
    """Retrieve complete content of a specific note"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        # Handle string IDs
        if isinstance(id, str):
            id = id.strip().strip('[]')
        id = int(id)
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            note = conn.execute('SELECT * FROM notes WHERE id = ?', (id,)).fetchone()
        
        if not note:
            return {"error": f"Note [{id}] not found"}
        
        # Return full content
        return {
            "note_id": note['id'],
            "author": note['author'],
            "created": note['created'],
            "content": note['content'],  # Full, untruncated
            "length": len(note['content']),
            "linked": json.loads(note['linked_items']) if note['linked_items'] else None
        }
        
    except Exception as e:
        logging.error(f"Error in get_full_note: {e}")
        return {"error": f"Failed to retrieve: {str(e)}"}

def vault_store(key: str = None, value: str = None, **kwargs) -> Dict:
    """Store encrypted secret - not searchable"""
    try:
        if key is None:
            key = kwargs.get('key')
        if value is None:
            value = kwargs.get('value')
        
        if not key or not value:
            return {"error": "Both key and value required"}
        
        key = str(key).strip()
        value = str(value).strip()
        
        # Encrypt value
        encrypted = vault_manager.encrypt(value)
        now = datetime.now().isoformat()
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            # Upsert (insert or update)
            conn.execute('''
                INSERT INTO vault (key, encrypted_value, created, updated, author)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    encrypted_value = excluded.encrypted_value,
                    updated = excluded.updated
            ''', (key, encrypted, now, now, CURRENT_AI_ID))
        
        log_operation('vault_store')
        return {"stored": f"Secret '{key}' secured"}
        
    except Exception as e:
        logging.error(f"Error in vault_store: {e}")
        return {"error": f"Storage failed: {str(e)}"}

def vault_retrieve(key: str = None, **kwargs) -> Dict:
    """Retrieve decrypted secret"""
    try:
        if key is None:
            key = kwargs.get('key')
        
        if not key:
            return {"error": "Key required"}
        
        key = str(key).strip()
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            result = conn.execute(
                'SELECT encrypted_value FROM vault WHERE key = ?', 
                (key,)
            ).fetchone()
        
        if not result:
            return {"error": f"Key '{key}' not found"}
        
        # Decrypt value
        decrypted = vault_manager.decrypt(result[0])
        
        log_operation('vault_retrieve')
        return {"key": key, "value": decrypted}
        
    except Exception as e:
        logging.error(f"Error in vault_retrieve: {e}")
        return {"error": f"Retrieval failed: {str(e)}"}

def vault_list(**kwargs) -> Dict:
    """List vault keys (not values) with metadata"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            items = conn.execute('''
                SELECT key, updated, author FROM vault 
                ORDER BY updated DESC
            ''').fetchall()
        
        if not items:
            return {"msg": "Vault empty"}
        
        # Format list
        keys = []
        for item in items:
            author_str = f"@{item['author']}" if item['author'] != CURRENT_AI_ID else ""
            time_str = format_time_contextual(item['updated'])
            keys.append(f"{item['key']}{author_str} {time_str}")
        
        return {"vault_keys": keys, "count": len(keys)}
        
    except Exception as e:
        logging.error(f"Error in vault_list: {e}")
        return {"error": f"List failed: {str(e)}"}

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
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
            'remember': remember,
            'recall': recall,
            'vault_store': vault_store,
            'vault_retrieve': vault_retrieve,
            'get_full_note': get_full_note
        }
        
        for op in operations:
            op_type = op.get('type')
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

def get_stats(**kwargs) -> Dict:
    """Get usage statistics"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            # Get operation counts
            stats = conn.execute('''
                SELECT operation, COUNT(*) as count, AVG(duration_ms) as avg_ms
                FROM stats
                WHERE author = ?
                GROUP BY operation
            ''', (CURRENT_AI_ID,)).fetchall()
            
            # Format stats
            if stats:
                op_stats = [f"{op}: {count} calls ({avg_ms:.0f}ms avg)" 
                           for op, count, avg_ms in stats if avg_ms]
                return {"stats": op_stats}
            else:
                return {"msg": "No stats yet"}
                
    except Exception as e:
        return {"error": f"Stats failed: {str(e)}"}

def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})
    
    # Function map
    tools = {
        "get_status": get_status,
        "remember": remember,
        "recall": recall,
        "get_full_note": get_full_note,
        "vault_store": vault_store,
        "vault_retrieve": vault_retrieve,
        "vault_list": vault_list,
        "batch": batch,
        "get_stats": get_stats
    }
    
    if tool_name not in tools:
        return {"error": f"Unknown tool: {tool_name}", "available": list(tools.keys())}
    
    # Execute tool
    result = tools[tool_name](**tool_args)
    
    # Format response
    text_parts = []
    
    # Handle different response types
    if "error" in result:
        text_parts.append(f"Error: {result['error']}")
        if "available" in result:
            text_parts.append("Available: " + ", ".join(result['available']))
    elif "status" in result:
        # Simple status line
        text_parts.append(result["status"])
    elif "summary" in result:
        text_parts.append(result["summary"])
        if "identity" in result:
            text_parts.append(f"Identity: {result['identity']}")
        if "recent" in result:
            text_parts.extend(result["recent"])
    elif "saved" in result:
        text_parts.append(result["saved"])
        if "truncated" in result:
            text_parts.append(f"({result['truncated']})")
    elif "stored" in result:
        text_parts.append(result["stored"])
    elif "value" in result and "key" in result:
        # Vault retrieve
        text_parts.append(f"Key: {result['key']}")
        text_parts.append(f"Value: {result['value']}")
    elif "vault_keys" in result:
        text_parts.append(f"Vault ({result.get('count', 0)} items):")
        text_parts.extend(result["vault_keys"])
    elif "results" in result:
        if "found" in result:
            text_parts.append(f"Found {result['found']} matches:")
        text_parts.extend(result["results"])
    elif "batch_results" in result:
        text_parts.append(f"Batch: {result.get('count', 0)} operations")
        for i, r in enumerate(result["batch_results"], 1):
            text_parts.append(f"{i}. {r}")
    elif "stats" in result:
        text_parts.append("Usage stats:")
        text_parts.extend(result["stats"])
    elif "content" in result and "note_id" in result:
        # Full note
        text_parts.append(f"[{result['note_id']}] by {result.get('author', 'Unknown')}")
        text_parts.append(f"Created: {result.get('created', '')}")
        text_parts.append(f"Length: {result.get('length', 0)} chars")
        if result.get('linked'):
            text_parts.append(f"Links: {', '.join(result['linked'])}")
        text_parts.append("---")
        text_parts.append(result["content"])
    elif "msg" in result:
        text_parts.append(result["msg"])
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Ready"
        }]
    }

# Initialize database on import
migrate_from_json()
init_db()

def main():
    """MCP server main loop"""
    logging.info(f"Notebook MCP v{VERSION} starting...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Database: {DB_FILE}")
    
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
                        "name": "notebook",
                        "version": VERSION,
                        "description": "Scalable AI memory with secure vault and smart summaries"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "get_status",
                            "description": "See your current state and recent notes",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "full": {
                                        "type": "boolean",
                                        "description": "Show full details (default: false for summary)"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "remember",
                            "description": "Save any thought, action, or note",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "What to remember"
                                    },
                                    "linked_items": {
                                        "type": "array",
                                        "description": "Optional links to other tools (e.g., ['task:123', 'teambook:456'])"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "recall",
                            "description": "Search notes or see recent ones",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search term (optional)"
                                    },
                                    "full": {
                                        "type": "boolean",
                                        "description": "Show full results (default: false for summary)"
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Max results (default: 10)"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "get_full_note",
                            "description": "Retrieve the COMPLETE content of a specific note (up to 5000 chars)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "The note ID shown in brackets, e.g., 346 from [346]"
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "vault_store",
                            "description": "Store a secret securely (encrypted, not searchable)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "key": {
                                        "type": "string",
                                        "description": "Unique key for the secret"
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Secret value to encrypt and store"
                                    }
                                },
                                "required": ["key", "value"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "vault_retrieve",
                            "description": "Retrieve a decrypted secret by key",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "key": {
                                        "type": "string",
                                        "description": "Key of the secret to retrieve"
                                    }
                                },
                                "required": ["key"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "vault_list",
                            "description": "List vault keys (not values)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": True
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
                                                    "description": "Operation type (remember, recall, vault_store, etc.)"
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
                        },
                        {
                            "name": "get_stats",
                            "description": "Get usage statistics",
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
    
    logging.info("Notebook MCP shutting down")

if __name__ == "__main__":
    main()