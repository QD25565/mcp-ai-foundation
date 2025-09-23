#!/usr/bin/env python3
"""
NOTEBOOK MCP v2.6.0 - EXPANDED MEMORY VIEW
===========================================
More visible memory with cleaner output.
Token-efficient by removing decorative elements.

Core improvements (v2.6):
- Expanded default view: 30 recent notes + all pinned
- Removed tags from list views (search/full only)
- Removed unnecessary punctuation and decoration
- Cleaner headers without colons
- More notes visible by default (30 vs 10)

Core functions:
- remember(content, summary=None, tags=None) - Save with optional summary/tags
- recall(query=None, tag=None, limit=50) - Search or filter by tag
- pin_note(id) - Pin important note
- unpin_note(id) - Unpin note
- get_status() - Shows pinned + 30 recent
- get_full_note(id) - Complete content with tags
- vault_store/retrieve/list - Secure storage
============================================
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
import re
from cryptography.fernet import Fernet

# Version
VERSION = "2.6.0"

# Limits
MAX_CONTENT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 200
MAX_RESULTS = 100
BATCH_MAX = 50
DEFAULT_RECENT = 30  # Show 30 recent notes by default

# Storage paths
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "notebook_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "notebook_data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "notebook.db"
OLD_JSON_FILE = DATA_DIR / "notebook.json"
VAULT_KEY_FILE = DATA_DIR / ".vault_key"

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global session info
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

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
    
    # Generate new readable ID
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep', 'Keen', 'Pure']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node', 'Wave', 'Link']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
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
            with open(VAULT_KEY_FILE, 'wb') as f:
                f.write(key)
            try:
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
    """Initialize SQLite database with pinning and tags"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Main notes table with pinning and tags
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            summary TEXT,
            tags TEXT,
            pinned INTEGER DEFAULT 0,
            author TEXT NOT NULL,
            created TEXT NOT NULL,
            session TEXT,
            linked_items TEXT
        )
    ''')
    
    # Full-text search virtual table
    conn.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts 
        USING fts5(content, summary, content=notes, content_rowid=id)
    ''')
    
    # Trigger to keep FTS in sync
    conn.execute('''
        CREATE TRIGGER IF NOT EXISTS notes_ai 
        AFTER INSERT ON notes BEGIN
            INSERT INTO notes_fts(rowid, content, summary) 
            VALUES (new.id, new.content, new.summary);
        END
    ''')
    
    # Vault table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS vault (
            key TEXT PRIMARY KEY,
            encrypted_value BLOB NOT NULL,
            created TEXT NOT NULL,
            updated TEXT NOT NULL,
            author TEXT NOT NULL
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
    
    # Indices
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned DESC, created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_vault_updated ON vault(updated DESC)')
    
    conn.commit()
    return conn

def migrate_to_v26():
    """Migration for v2.6 - no schema changes, just behavior"""
    try:
        conn = sqlite3.connect(str(DB_FILE))
        
        # Check if columns exist (from v2.5)
        cursor = conn.execute("PRAGMA table_info(notes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'pinned' not in columns:
            logging.info("Migrating to v2.6 - adding pinned column...")
            conn.execute('ALTER TABLE notes ADD COLUMN pinned INTEGER DEFAULT 0')
            conn.commit()
        
        if 'tags' not in columns:
            logging.info("Migrating to v2.6 - adding tags column...")
            conn.execute('ALTER TABLE notes ADD COLUMN tags TEXT')
            conn.commit()
        
        if 'summary' not in columns:
            logging.info("Migrating to v2.6 - adding summary column...")
            conn.execute('ALTER TABLE notes ADD COLUMN summary TEXT')
            
            # Generate simple summaries for existing notes
            conn.execute('''
                UPDATE notes 
                SET summary = SUBSTR(
                    REPLACE(REPLACE(content, CHAR(10), ' '), '  ', ' '), 
                    1, 150
                ) || '...'
                WHERE summary IS NULL AND LENGTH(content) > 150
            ''')
            conn.execute('''
                UPDATE notes 
                SET summary = REPLACE(REPLACE(content, CHAR(10), ' '), '  ', ' ')
                WHERE summary IS NULL
            ''')
            conn.commit()
        
        conn.close()
    except Exception as e:
        logging.error(f"Migration error: {e}")

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

def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and newlines"""
    if not text:
        return ""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def simple_summary(content: str, max_length: int = 150) -> str:
    """Create simple summary by truncating cleanly"""
    if not content:
        return ""
    
    # Clean the text
    clean = clean_text(content)
    
    if len(clean) <= max_length:
        return clean
    
    # Find a good break point (sentence or word boundary)
    # First try to break at sentence
    for sep in ['. ', '! ', '? ', '; ']:
        idx = clean.rfind(sep, 0, max_length)
        if idx > max_length * 0.5:  # If we found a sentence break in second half
            return clean[:idx + 1]
    
    # Otherwise break at word
    idx = clean.rfind(' ', 0, max_length - 3)
    if idx == -1 or idx < max_length * 0.7:
        idx = max_length - 3
    
    return clean[:idx] + "..."

def log_operation(operation: str, duration_ms: int = None):
    """Log operation for stats tracking"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.execute(
                'INSERT INTO stats (operation, timestamp, duration_ms, author) VALUES (?, ?, ?, ?)',
                (operation, datetime.now().isoformat(), duration_ms, CURRENT_AI_ID)
            )
    except:
        pass

def remember(content: str = None, summary: str = None, tags: List[str] = None, 
             linked_items: List[str] = None, **kwargs) -> Dict:
    """Save a note with optional summary and tags"""
    try:
        start = datetime.now()
        
        if content is None:
            content = kwargs.get('content', '')
        
        content = str(content).strip()
        if not content:
            content = f"Checkpoint {datetime.now().strftime('%H:%M')}"
        
        # Handle truncation
        truncated = False
        original_length = len(content)
        if original_length > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
            truncated = True
        
        # Generate summary if not provided
        if summary:
            summary = clean_text(summary)[:MAX_SUMMARY_LENGTH]
        else:
            summary = simple_summary(content)
        
        # Process tags
        tags_json = None
        if tags:
            # Ensure tags are strings and lowercase
            tags = [str(t).lower().strip() for t in tags if t]
            tags_json = json.dumps(tags) if tags else None
        
        # Store note
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute(
                '''INSERT INTO notes (content, summary, tags, author, created, session, linked_items) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (content, summary, tags_json, CURRENT_AI_ID, datetime.now().isoformat(), 
                 session_id, json.dumps(linked_items) if linked_items else None)
            )
            note_id = cursor.lastrowid
        
        # Log stats
        duration = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('remember', duration)
        
        # Return result - clean, no decoration
        result = {"saved": f"{note_id} now {summary}"}
        if truncated:
            result["truncated"] = f"from {original_length} chars"
        
        return result
        
    except Exception as e:
        logging.error(f"Error in remember: {e}")
        return {"error": f"Failed to save: {str(e)}"}

def recall(query: str = None, tag: str = None, show_all: bool = False, 
           limit: int = 50, **kwargs) -> Dict:
    """Search notes or filter by tag"""
    try:
        start = datetime.now()
        
        # Use higher default limit
        if not show_all and not query and not tag:
            limit = DEFAULT_RECENT
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            if query:
                # Search mode
                query = str(query).strip()
                cursor = conn.execute('''
                    SELECT n.* FROM notes n
                    JOIN notes_fts ON n.id = notes_fts.rowid
                    WHERE notes_fts MATCH ?
                    ORDER BY n.pinned DESC, n.created DESC
                    LIMIT ?
                ''', (query, limit))
            
            elif tag:
                # Tag filter mode
                tag = str(tag).lower().strip()
                # Use LIKE for JSON array search
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    WHERE tags LIKE ?
                    ORDER BY pinned DESC, created DESC
                    LIMIT ?
                ''', (f'%"{tag}"%', limit))
            
            else:
                # Default: show pinned + recent
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    ORDER BY pinned DESC, created DESC
                    LIMIT ?
                ''', (limit,))
            
            notes = cursor.fetchall()
        
        if not notes:
            if query:
                return {"msg": f"No matches for '{query}'"}
            elif tag:
                return {"msg": f"No notes tagged '{tag}'"}
            else:
                return {"msg": "No notes yet"}
        
        # Format results - CLEAN, NO TAGS IN LIST VIEW
        lines = []
        
        # Get counts
        with sqlite3.connect(str(DB_FILE)) as conn:
            total = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            pinned = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = 1').fetchone()[0]
        
        # Header - no colons
        header = f"{total} notes"
        if pinned > 0:
            header += f" | {pinned} pinned"
        if query:
            header += f" | searching '{query}'"
        elif tag:
            header += f" | tag '{tag}'"
        header += f" | last {format_time_contextual(notes[0]['created'])}"
        lines.append(header)
        
        # Group by pinned status
        pinned_notes = [n for n in notes if n['pinned']]
        regular_notes = [n for n in notes if not n['pinned']]
        
        if pinned_notes:
            lines.append("\nPINNED")
            for note in pinned_notes:
                time_str = format_time_contextual(note['created'])
                summary = note['summary'] or simple_summary(note['content'])
                # NO TAGS IN LIST VIEW
                lines.append(f"p{note['id']} {time_str} {summary}")
        
        if regular_notes:
            if pinned_notes:
                lines.append("\nRECENT")
            for note in regular_notes:
                time_str = format_time_contextual(note['created'])
                summary = note['summary'] or simple_summary(note['content'])
                # NO TAGS IN LIST VIEW
                lines.append(f"{note['id']} {time_str} {summary}")
        
        # Log operation
        duration = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('recall', duration)
        
        return {"notes": "\n".join(lines)}
        
    except Exception as e:
        logging.error(f"Error in recall: {e}")
        return {"error": f"Recall failed: {str(e)}"}

def get_status(**kwargs) -> Dict:
    """Get current state with pinned and more recent notes"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get counts
            total_notes = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            my_notes = conn.execute('SELECT COUNT(*) FROM notes WHERE author = ?', 
                                   (CURRENT_AI_ID,)).fetchone()[0]
            pinned_count = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = 1').fetchone()[0]
            vault_items = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
            
            # Get ALL pinned notes
            pinned = conn.execute('''
                SELECT id, summary, content, created FROM notes 
                WHERE pinned = 1
                ORDER BY created DESC
            ''').fetchall()
            
            # Get 30 recent unpinned notes (expanded from 5)
            recent = conn.execute('''
                SELECT id, summary, content, created FROM notes 
                WHERE pinned = 0
                ORDER BY created DESC 
                LIMIT 30
            ''').fetchall()
            
            last_activity = format_time_contextual(recent[0]['created'] if recent else 
                                                  (pinned[0]['created'] if pinned else None))
        
        # Build response - clean formatting
        lines = []
        
        # Header line - no colons
        header = f"{total_notes} notes"
        if pinned_count > 0:
            header += f" | {pinned_count} pinned"
        header += f" | {vault_items} vault | last {last_activity}"
        lines.append(header)
        
        # Pinned notes (show all)
        if pinned:
            lines.append("\nPINNED")
            for note in pinned:
                time_str = format_time_contextual(note['created'])
                summary = note['summary'] or simple_summary(note['content'])
                lines.append(f"p{note['id']} {time_str} {summary}")
        
        # Recent notes (show 30 instead of 3)
        if recent:
            lines.append("\nRECENT")
            for note in recent:
                time_str = format_time_contextual(note['created'])
                summary = note['summary'] or simple_summary(note['content'])
                lines.append(f"{note['id']} {time_str} {summary}")
        
        lines.append(f"\nIdentity {CURRENT_AI_ID}")
        
        return {"status": "\n".join(lines)}
        
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {"error": f"Status failed: {str(e)}"}

def pin_note(id: Any = None, **kwargs) -> Dict:
    """Pin an important note"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        if id is None:
            return {"error": "No ID provided"}
        
        # Handle string IDs (including 'p' prefix)
        if isinstance(id, str):
            id = id.strip().lstrip('p')
        
        if not id or id == '':
            return {"error": "Invalid/empty ID provided"}
        
        try:
            id = int(id)
        except (ValueError, TypeError):
            return {"error": f"Invalid ID format '{id}'"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute('UPDATE notes SET pinned = 1 WHERE id = ?', (id,))
            
            if cursor.rowcount == 0:
                return {"error": f"Note {id} not found"}
            
            # Get the note summary for confirmation
            note = conn.execute('SELECT summary, content FROM notes WHERE id = ?', (id,)).fetchone()
            summary = note[0] or simple_summary(note[1])
        
        return {"pinned": f"p{id} {summary}"}
        
    except Exception as e:
        logging.error(f"Error in pin_note: {e}")
        return {"error": f"Failed to pin: {str(e)}"}

def unpin_note(id: Any = None, **kwargs) -> Dict:
    """Unpin a note"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        if id is None:
            return {"error": "No ID provided"}
        
        # Handle string IDs (including 'p' prefix)
        if isinstance(id, str):
            id = id.strip().lstrip('p')
        
        if not id or id == '':
            return {"error": "Invalid/empty ID provided"}
        
        try:
            id = int(id)
        except (ValueError, TypeError):
            return {"error": f"Invalid ID format '{id}'"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute('UPDATE notes SET pinned = 0 WHERE id = ?', (id,))
            
            if cursor.rowcount == 0:
                return {"error": f"Note {id} not found"}
        
        return {"unpinned": f"Note {id} unpinned"}
        
    except Exception as e:
        logging.error(f"Error in unpin_note: {e}")
        return {"error": f"Failed to unpin: {str(e)}"}

def get_full_note(id: Any = None, **kwargs) -> Dict:
    """Retrieve complete content of a specific note - INCLUDING TAGS"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        if id is None:
            return {"error": "No ID provided"}
        
        # Handle string IDs (including 'p' prefix)
        if isinstance(id, str):
            id = id.strip().lstrip('p')
        
        if not id or id == '':
            return {"error": "Invalid/empty ID provided"}
        
        try:
            id = int(id)
        except (ValueError, TypeError):
            return {"error": f"Invalid ID format '{id}'"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            note = conn.execute('SELECT * FROM notes WHERE id = ?', (id,)).fetchone()
        
        if not note:
            return {"error": f"Note {id} not found"}
        
        result = {
            "note_id": note['id'],
            "author": note['author'],
            "created": note['created'],
            "summary": note['summary'] or simple_summary(note['content']),
            "content": note['content'],
            "length": len(note['content']),
            "pinned": note['pinned']
        }
        
        # Include tags in full view
        if note['tags']:
            result["tags"] = json.loads(note['tags'])
        
        if note['linked_items']:
            result["linked"] = json.loads(note['linked_items'])
        
        return result
        
    except Exception as e:
        logging.error(f"Error in get_full_note: {e}")
        return {"error": f"Failed to retrieve: {str(e)}"}

def vault_store(key: str = None, value: str = None, **kwargs) -> Dict:
    """Store encrypted secret"""
    try:
        if key is None:
            key = kwargs.get('key')
        if value is None:
            value = kwargs.get('value')
        
        if not key or not value:
            return {"error": "Both key and value required"}
        
        key = str(key).strip()
        value = str(value).strip()
        
        encrypted = vault_manager.encrypt(value)
        now = datetime.now().isoformat()
        
        with sqlite3.connect(str(DB_FILE)) as conn:
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
        
        decrypted = vault_manager.decrypt(result[0])
        
        log_operation('vault_retrieve')
        return {"key": key, "value": decrypted}
        
    except Exception as e:
        logging.error(f"Error in vault_retrieve: {e}")
        return {"error": f"Retrieval failed: {str(e)}"}

def vault_list(**kwargs) -> Dict:
    """List vault keys"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            items = conn.execute('''
                SELECT key, updated FROM vault 
                ORDER BY updated DESC
            ''').fetchall()
        
        if not items:
            return {"msg": "Vault empty"}
        
        keys = []
        for item in items:
            time_str = format_time_contextual(item['updated'])
            keys.append(f"{item['key']} {time_str}")
        
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
            'pin_note': pin_note,
            'unpin_note': unpin_note,
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
    
    # Function map
    tools = {
        "get_status": get_status,
        "remember": remember,
        "recall": recall,
        "get_full_note": get_full_note,
        "pin_note": pin_note,
        "unpin_note": unpin_note,
        "vault_store": vault_store,
        "vault_retrieve": vault_retrieve,
        "vault_list": vault_list,
        "batch": batch
    }
    
    if tool_name not in tools:
        # Return proper error response structure
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Unknown tool: {tool_name}\nAvailable: {', '.join(tools.keys())}"
            }]
        }
    
    # Execute tool
    result = tools[tool_name](**tool_args)
    
    # Format response - clean, no decoration
    text_parts = []
    
    # Check if result is a dictionary
    if not isinstance(result, dict):
        text_parts.append(str(result))
    elif "error" in result:
        text_parts.append(str(f"Error {result['error']}"))
    elif "note_id" in result:  # get_full_note
        # Full note - show everything including tags
        text_parts.append(str(f"{result['note_id']} by {result.get('author', 'Unknown')}"))
        text_parts.append(str(f"Created {result.get('created', '')}"))
        text_parts.append(str(f"Summary {result.get('summary', '')}"))
        if result.get('pinned'):  # Will show if pinned is 1 (truthy)
            text_parts.append(str("Status PINNED"))
        if result.get('tags'):
            tags_str = ', '.join(str(tag) for tag in result['tags'])
            text_parts.append(str(f"Tags {tags_str}"))
        text_parts.append(str(f"Length {result.get('length', 0)} chars"))
        text_parts.append(str("---"))
        text_parts.append(str(result.get("content", "")))
    elif "status" in result:  # get_status
        text_parts.append(str(result["status"]))
    elif "notes" in result:  # recall
        text_parts.append(str(result["notes"]))
    elif "saved" in result:  # remember
        parts = [str(result["saved"])]
        if "truncated" in result:
            parts.append(f"({result['truncated']})")
        text_parts.append(" ".join(parts))
    elif "pinned" in result:  # pin_note
        text_parts.append(str(result["pinned"]))
    elif "unpinned" in result:  # unpin_note
        text_parts.append(str(result["unpinned"]))
    elif "stored" in result:  # vault_store
        text_parts.append(str(result["stored"]))
    elif "key" in result and "value" in result:  # vault_retrieve
        text_parts.append(f"Vault[{result['key']}] = {result['value']}")
    elif "vault_keys" in result:  # vault_list
        text_parts.append(f"Vault ({result.get('count', 0)} keys)")
        text_parts.extend(str(k) for k in result["vault_keys"])
    elif "msg" in result:  # Simple messages
        text_parts.append(str(result["msg"]))
    elif "batch_results" in result:
        text_parts.append(str(f"Batch {result.get('count', 0)} operations"))
        for i, r in enumerate(result["batch_results"], 1):
            # Format each batch result properly
            if isinstance(r, dict):
                if "error" in r:
                    text_parts.append(str(f"{i}. Error {r['error']}"))
                elif "saved" in r:
                    text_parts.append(str(f"{i}. {r['saved']}"))
                elif "pinned" in r:
                    text_parts.append(str(f"{i}. {r['pinned']}"))
                elif "unpinned" in r:
                    text_parts.append(str(f"{i}. {r['unpinned']}"))
                elif "stored" in r:
                    text_parts.append(str(f"{i}. {r['stored']}"))
                elif "note_id" in r:  # get_full_note in batch
                    text_parts.append(str(f"{i}. Note {r['note_id']} {r.get('summary', '...')}"))
                elif "notes" in r:  # recall in batch
                    text_parts.append(str(f"{i}. Recall {r['notes'].splitlines()[0]}"))  # Just show first line
                elif "key" in r and "value" in r:  # vault_retrieve in batch
                    text_parts.append(str(f"{i}. Vault[{r['key']}] = {r['value']}"))
                elif "msg" in r:
                    text_parts.append(str(f"{i}. {r['msg']}"))
                else:
                    # Convert the whole dict to string for other cases
                    text_parts.append(str(f"{i}. {json.dumps(r)}"))
            else:
                text_parts.append(str(f"{i}. {r}"))
    else:
        # If no conditions match, log the result for debugging
        logging.warning(f"Unhandled result format from {tool_name}: {result}")
        text_parts.append(str(json.dumps(result)))
    
    # Extra safety: ensure all items in text_parts are strings
    text_parts = [str(item) for item in text_parts]
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Ready"
        }]
    }

# Initialize database
migrate_to_v26()
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
                        "description": "Expanded memory view with cleaner output"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "get_status",
                            "description": "See current state with pinned and recent notes",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "remember",
                            "description": "Save note with optional summary and tags",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "What to remember (required)"
                                    },
                                    "summary": {
                                        "type": "string",
                                        "description": "Brief 1-3 sentence summary (optional, auto-generated if not provided)"
                                    },
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Tags for categorization (optional)"
                                    },
                                    "linked_items": {
                                        "type": "array",
                                        "description": "Links to other tools"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "recall",
                            "description": "Search notes or filter by tag",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search term (optional)"
                                    },
                                    "tag": {
                                        "type": "string",
                                        "description": "Filter by tag (optional)"
                                    },
                                    "show_all": {
                                        "type": "boolean",
                                        "description": "Show more results (default: false)"
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
                            "name": "pin_note",
                            "description": "Pin an important note",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Note ID to pin (e.g., '143' or 'p143')"
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "unpin_note",
                            "description": "Unpin a note",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Note ID to unpin (e.g., '143' or 'p143')"
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "get_full_note",
                            "description": "Get complete content of a note",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Note ID (e.g., '143' or 'p143')"
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "vault_store",
                            "description": "Store encrypted secret",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "key": {
                                        "type": "string",
                                        "description": "Unique key"
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Secret value"
                                    }
                                },
                                "required": ["key", "value"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "vault_retrieve",
                            "description": "Retrieve decrypted secret",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "key": {
                                        "type": "string",
                                        "description": "Key to retrieve"
                                    }
                                },
                                "required": ["key"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "vault_list",
                            "description": "List vault keys",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
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
                                                    "description": "Operation type"
                                                },
                                                "args": {
                                                    "type": "object",
                                                    "description": "Arguments"
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
    
    logging.info("Notebook MCP shutting down")

if __name__ == "__main__":
    main()
