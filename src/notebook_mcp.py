#!/usr/bin/env python3
"""
NOTEBOOK MCP v4.1.0 - INTEGRATED INTELLIGENCE
==============================================
Memory that connects, not just stores.
70% fewer tokens. Tools that know each other.

MAJOR CHANGES (v4.1):
- DEFAULT_RECENT reduced to 30 (50% token savings)
- Time-based recall: when="yesterday"/"today"/"morning"
- Smart ID resolution: "last" keyword everywhere
- Cross-tool event hooks ready

Core improvements over v4.0:
- Ecosystem awareness (tools know about each other)
- Natural language time queries
- Smarter defaults based on actual usage
- Integration > isolation

The future: Tools that think together.
==============================================
"""

import json
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
import logging
import random
import re
import time
import numpy as np
from collections import defaultdict
from cryptography.fernet import Fernet

# Version
VERSION = "4.1.0"

# Configuration
OUTPUT_FORMAT = os.environ.get('NOTEBOOK_FORMAT', 'pipe')  # 'pipe' or 'json'
SEARCH_MODE = os.environ.get('NOTEBOOK_SEARCH', 'or')  # 'or' or 'and'

# Limits - UPDATED: DEFAULT_RECENT reduced from 60 to 30
MAX_CONTENT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 200
MAX_RESULTS = 100
BATCH_MAX = 50
DEFAULT_RECENT = 30  # CHANGED: Was 60, now 30 for 50% token savings
TEMPORAL_EDGES = 3
SESSION_GAP_MINUTES = 30
PAGERANK_ITERATIONS = 50
PAGERANK_DAMPING = 0.85
PAGERANK_CACHE_SECONDS = 300

# Storage paths
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "notebook_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "notebook_data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "notebook.db"
OLD_JSON_FILE = DATA_DIR / "notebook.json"
VAULT_KEY_FILE = DATA_DIR / ".vault_key"
LAST_OP_FILE = DATA_DIR / ".last_operation"

# Cross-tool integration paths
TASK_INTEGRATION_FILE = DATA_DIR / ".task_integration"
TEAMBOOK_INTEGRATION_FILE = DATA_DIR / ".teambook_integration"

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global session info
sess_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Known entities cache
KNOWN_ENTITIES = set()
KNOWN_TOOLS = {'teambook', 'firebase', 'gemini', 'claude', 'jetbrains', 'github', 
                'slack', 'discord', 'vscode', 'git', 'docker', 'python', 'node',
                'react', 'vue', 'angular', 'tensorflow', 'pytorch', 'aws', 'gcp',
                'azure', 'kubernetes', 'redis', 'postgres', 'mongodb', 'sqlite',
                'task_manager', 'notebook', 'world'}

# PageRank lazy calculation flags
PAGERANK_DIRTY = True
PAGERANK_CACHE_TIME = 0

# Operation memory
LAST_OPERATION = None

def save_last_operation(op_type: str, result: Any):
    """Save last operation for chaining"""
    global LAST_OPERATION
    LAST_OPERATION = {'type': op_type, 'result': result, 'time': datetime.now()}
    try:
        with open(LAST_OP_FILE, 'w') as f:
            json.dump({'type': op_type, 'time': LAST_OPERATION['time'].isoformat()}, f)
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
                return {'type': data['type'], 'time': datetime.fromisoformat(data['time'])}
    except:
        pass
    return None

def pipe_escape(text: str) -> str:
    """Escape pipes in text for pipe format"""
    return text.replace('|', '\\|')

def format_output(data: Any, format_type: str = None) -> str:
    """Format output optimally based on type and context"""
    if format_type is None:
        format_type = OUTPUT_FORMAT
    
    if format_type == 'pipe':
        # Pipe format for lists (70% token reduction)
        if isinstance(data, list):
            return '|'.join(pipe_escape(str(item)) for item in data)
        elif isinstance(data, dict):
            if 'notes' in data and isinstance(data['notes'], list):
                return '|'.join(pipe_escape(str(note)) for note in data['notes'])
            elif 'tasks' in data and isinstance(data['tasks'], list):
                return '|'.join(pipe_escape(str(task)) for task in data['tasks'])
            else:
                # Fallback to key:value pairs
                pairs = [f"{k}:{v}" for k, v in data.items() if v is not None]
                return '|'.join(pipe_escape(p) for p in pairs)
        else:
            return str(data)
    else:
        # JSON format when structure needed
        return json.dumps(data) if isinstance(data, (dict, list)) else str(data)

def get_persistent_id():
    """Get or create persistent AI identity"""
    for loc in [Path(__file__).parent, DATA_DIR, Path.home()]:
        id_file = loc / "ai_identity.txt"
        if id_file.exists():
            try:
                with open(id_file, 'r') as f:
                    stored_id = f.read().strip()
                    if stored_id:
                        logging.info(f"Loaded identity from {loc}: {stored_id}")
                        return stored_id
            except Exception as e:
                logging.error(f"Error reading identity from {loc}: {e}")
    
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
    """Initialize SQLite database with all edge types and entities"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Main notes table with session_id column
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            summary TEXT,
            tags TEXT,
            pinned INTEGER DEFAULT 0,
            author TEXT NOT NULL,
            created TEXT NOT NULL,
            session_id INTEGER,
            linked_items TEXT,
            pagerank REAL DEFAULT 0.0,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    ''')
    
    # Edges table for all connection types
    conn.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created TEXT NOT NULL,
            PRIMARY KEY(from_id, to_id, type),
            FOREIGN KEY(from_id) REFERENCES notes(id),
            FOREIGN KEY(to_id) REFERENCES notes(id)
        )
    ''')
    
    # Entities table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            mention_count INTEGER DEFAULT 1
        )
    ''')
    
    # Entity-Note relationships
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entity_notes (
            entity_id INTEGER NOT NULL,
            note_id INTEGER NOT NULL,
            PRIMARY KEY(entity_id, note_id),
            FOREIGN KEY(entity_id) REFERENCES entities(id),
            FOREIGN KEY(note_id) REFERENCES notes(id)
        )
    ''')
    
    # Sessions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started TEXT NOT NULL,
            ended TEXT NOT NULL,
            note_count INTEGER DEFAULT 1,
            coherence_score REAL DEFAULT 1.0
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
            ts TEXT NOT NULL,
            dur_ms INTEGER,
            author TEXT
        )
    ''')
    
    # Indices
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned DESC, created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_pagerank ON notes(pagerank DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_session ON notes(session_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entity_notes_note ON entity_notes(note_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_vault_updated ON vault(updated DESC)')
    
    conn.commit()
    
    # Load known entities into cache
    load_known_entities(conn)
    
    return conn

def load_known_entities(conn: sqlite3.Connection):
    """Load known entities into memory cache"""
    global KNOWN_ENTITIES
    try:
        entities = conn.execute('SELECT name FROM entities').fetchall()
        KNOWN_ENTITIES = {e[0].lower() for e in entities}
    except:
        KNOWN_ENTITIES = set()

def migrate_to_v41():
    """Migration for v4.1 - ensure all columns exist"""
    try:
        conn = sqlite3.connect(str(DB_FILE))
        
        # Check existing columns
        cursor = conn.execute("PRAGMA table_info(notes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add pagerank column if missing
        if 'pagerank' not in columns:
            logging.info("Adding PageRank column...")
            conn.execute('ALTER TABLE notes ADD COLUMN pagerank REAL DEFAULT 0.0')
            conn.commit()
        
        # Add session_id column if missing
        if 'session_id' not in columns:
            logging.info("Adding session_id column...")
            conn.execute('ALTER TABLE notes ADD COLUMN session_id INTEGER')
            conn.commit()
        
        # Ensure all tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {t[0] for t in cursor.fetchall()}
        
        if 'entities' not in tables:
            logging.info("Creating entities table...")
            conn.execute('''
                CREATE TABLE entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    mention_count INTEGER DEFAULT 1
                )
            ''')
            conn.execute('CREATE INDEX idx_entities_name ON entities(name)')
            conn.commit()
        
        if 'entity_notes' not in tables:
            logging.info("Creating entity_notes table...")
            conn.execute('''
                CREATE TABLE entity_notes (
                    entity_id INTEGER NOT NULL,
                    note_id INTEGER NOT NULL,
                    PRIMARY KEY(entity_id, note_id),
                    FOREIGN KEY(entity_id) REFERENCES entities(id),
                    FOREIGN KEY(note_id) REFERENCES notes(id)
                )
            ''')
            conn.execute('CREATE INDEX idx_entity_notes_note ON entity_notes(note_id)')
            conn.commit()
        
        if 'sessions' not in tables:
            logging.info("Creating sessions table...")
            conn.execute('''
                CREATE TABLE sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started TEXT NOT NULL,
                    ended TEXT NOT NULL,
                    note_count INTEGER DEFAULT 1,
                    coherence_score REAL DEFAULT 1.0
                )
            ''')
            conn.commit()
        
        # Mark PageRank as needing recalculation
        global PAGERANK_DIRTY
        PAGERANK_DIRTY = True
        
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

def format_time_contextual(ts: str) -> str:
    """Ultra-compact contextual time format"""
    if not ts:
        return ""
    
    try:
        dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
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
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def simple_summary(content: str, max_len: int = 150) -> str:
    """Create simple summary by truncating cleanly"""
    if not content:
        return ""
    
    clean = clean_text(content)
    
    if len(clean) <= max_len:
        return clean
    
    # Find a good break point
    for sep in ['. ', '! ', '? ', '; ']:
        idx = clean.rfind(sep, 0, max_len)
        if idx > max_len * 0.5:
            return clean[:idx + 1]
    
    # Otherwise break at word
    idx = clean.rfind(' ', 0, max_len - 3)
    if idx == -1 or idx < max_len * 0.7:
        idx = max_len - 3
    
    return clean[:idx] + "..."

def extract_references(content: str) -> List[int]:
    """Extract note references from content"""
    refs = []
    
    # Match patterns like: note 123, n123, p123, #123, [123], see 123
    patterns = [
        r'note\s+(\d+)',
        r'\bn(\d+)\b',
        r'\bp(\d+)\b',
        r'#(\d+)\b',
        r'\[(\d+)\]',
        r'see\s+(\d+)',
        r'ref\s+(\d+)',
        r'@(\d+)\b'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        refs.extend(int(m) for m in matches if m.isdigit())
    
    return list(set(refs))  # Return unique refs

def extract_entities(content: str) -> List[Tuple[str, str]]:
    """Extract entities from content with word boundaries"""
    entities = []
    content_lower = content.lower()
    
    # Pattern 1: @mentions (people/AIs)
    mentions = re.findall(r'@([\w-]+)', content, re.IGNORECASE)
    entities.extend((m.lower(), 'mention') for m in mentions)
    
    # Pattern 2: Tool/project names with word boundaries
    for tool in KNOWN_TOOLS:
        if re.search(r'\b' + re.escape(tool) + r'\b', content_lower):
            entities.append((tool, 'tool'))
    
    # Pattern 3: IDs (tb_123, task_456, etc)
    ids = re.findall(r'\b(tb_\d+|task_\d+|pr_\d+|issue_\d+|dm_\d+|sh_\d+)\b', content, re.IGNORECASE)
    entities.extend((id_str.lower(), 'id') for id_str in ids)
    
    # Pattern 4: Quoted projects/names
    quoted = re.findall(r'"([^"]{3,50})"', content)
    entities.extend((q.lower(), 'project') for q in quoted if len(q.split()) <= 5)
    
    # Pattern 5: Project/Product declarations
    projects = re.findall(r'(?:project|product|app|system):\s*([\w-]+)', content, re.IGNORECASE)
    entities.extend((p.lower(), 'project') for p in projects)
    
    # Pattern 6: Known entities from database with word boundaries
    for entity in KNOWN_ENTITIES:
        if re.search(r'\b' + re.escape(entity) + r'\b', content_lower):
            entities.append((entity, 'known'))
    
    # Deduplicate while preserving order
    seen = set()
    unique_entities = []
    for entity in entities:
        if entity[0] not in seen:
            seen.add(entity[0])
            unique_entities.append(entity)
    
    return unique_entities

def detect_or_create_session(note_id: int, created: datetime, conn: sqlite3.Connection) -> Optional[int]:
    """Detect existing session or create new one"""
    try:
        # Get the most recent note before this one
        prev_note = conn.execute('''
            SELECT id, created, session_id FROM notes 
            WHERE id < ? 
            ORDER BY id DESC 
            LIMIT 1
        ''', (note_id,)).fetchone()
        
        if prev_note:
            prev_time = datetime.fromisoformat(prev_note[1])
            time_gap = (created - prev_time).total_seconds() / 60
            
            if time_gap <= SESSION_GAP_MINUTES and prev_note[2]:
                # Continue existing session
                session_id = prev_note[2]
                # Update session end time and count
                conn.execute('''
                    UPDATE sessions 
                    SET ended = ?, note_count = note_count + 1
                    WHERE id = ?
                ''', (created.isoformat(), session_id))
                return session_id
        
        # Create new session
        cursor = conn.execute('''
            INSERT INTO sessions (started, ended, note_count)
            VALUES (?, ?, 1)
        ''', (created.isoformat(), created.isoformat()))
        
        return cursor.lastrowid
        
    except Exception as e:
        logging.error(f"Error detecting/creating session: {e}")
        return None

def create_session_edges(note_id: int, session_id: int, conn: sqlite3.Connection):
    """Create edges between notes in the same session"""
    try:
        now = datetime.now().isoformat()
        
        # Get all other notes in this session
        session_notes = conn.execute('''
            SELECT id FROM notes 
            WHERE session_id = ? AND id != ?
        ''', (session_id, note_id)).fetchall()
        
        # Create bidirectional edges
        for other_note in session_notes:
            other_id = other_note[0]
            conn.execute('''
                INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                VALUES (?, ?, 'session', 1.5, ?)
            ''', (note_id, other_id, now))
            conn.execute('''
                INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                VALUES (?, ?, 'session', 1.5, ?)
            ''', (other_id, note_id, now))
        
    except Exception as e:
        logging.error(f"Error creating session edges: {e}")

def create_entity_edges(note_id: int, entities: List[Tuple[str, str]], conn: sqlite3.Connection):
    """Create edges between note and entities"""
    try:
        now = datetime.now().isoformat()
        
        for entity_name, entity_type in entities:
            # Get or create entity
            entity = conn.execute('''
                SELECT id FROM entities WHERE name = ?
            ''', (entity_name,)).fetchone()
            
            if entity:
                entity_id = entity[0]
                # Update last seen and increment count
                conn.execute('''
                    UPDATE entities 
                    SET last_seen = ?, mention_count = mention_count + 1
                    WHERE id = ?
                ''', (now, entity_id))
            else:
                # Create new entity
                cursor = conn.execute('''
                    INSERT INTO entities (name, type, first_seen, last_seen)
                    VALUES (?, ?, ?, ?)
                ''', (entity_name, entity_type, now, now))
                entity_id = cursor.lastrowid
                # Add to cache
                KNOWN_ENTITIES.add(entity_name.lower())
            
            # Create entity-note relationship
            conn.execute('''
                INSERT OR IGNORE INTO entity_notes (entity_id, note_id)
                VALUES (?, ?)
            ''', (entity_id, note_id))
            
            # Find all other notes mentioning this entity
            other_notes = conn.execute('''
                SELECT note_id FROM entity_notes 
                WHERE entity_id = ? AND note_id != ?
            ''', (entity_id, note_id)).fetchall()
            
            # Create edges to all other notes with same entity
            for other_note in other_notes:
                other_id = other_note[0]
                conn.execute('''
                    INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                    VALUES (?, ?, 'entity', 1.2, ?)
                ''', (note_id, other_id, now))
                conn.execute('''
                    INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                    VALUES (?, ?, 'entity', 1.2, ?)
                ''', (other_id, note_id, now))
        
    except Exception as e:
        logging.error(f"Error creating entity edges: {e}")

def calculate_pagerank_scores(conn: sqlite3.Connection):
    """Calculate PageRank scores for all notes"""
    try:
        start = time.time()
        
        # Get all notes
        notes = conn.execute('SELECT id FROM notes').fetchall()
        if not notes:
            return
        
        note_ids = [n[0] for n in notes]
        n = len(note_ids)
        id_to_idx = {nid: i for i, nid in enumerate(note_ids)}
        
        # Build adjacency matrix
        adjacency = np.zeros((n, n))
        
        edges = conn.execute('''
            SELECT from_id, to_id, weight FROM edges
            WHERE from_id IN ({}) AND to_id IN ({})
        '''.format(','.join('?' * n), ','.join('?' * n)), 
           note_ids + note_ids).fetchall()
        
        for from_id, to_id, weight in edges:
            if from_id in id_to_idx and to_id in id_to_idx:
                adjacency[id_to_idx[from_id]][id_to_idx[to_id]] = weight
        
        # Initialize PageRank (equal probability)
        pagerank = np.ones(n) / n
        
        # Power iteration
        for _ in range(PAGERANK_ITERATIONS):
            new_pagerank = np.zeros(n)
            
            for i in range(n):
                # Random jump probability
                rank = (1 - PAGERANK_DAMPING) / n
                
                # Add contributions from incoming links
                for j in range(n):
                    if adjacency[j][i] > 0:
                        outlinks = np.sum(adjacency[j])
                        if outlinks > 0:
                            rank += PAGERANK_DAMPING * (pagerank[j] / outlinks) * adjacency[j][i]
                
                new_pagerank[i] = rank
            
            # Check convergence
            if np.max(np.abs(new_pagerank - pagerank)) < 0.0001:
                break
            
            pagerank = new_pagerank
        
        # Update database with PageRank scores
        for i, note_id in enumerate(note_ids):
            conn.execute('UPDATE notes SET pagerank = ? WHERE id = ?', 
                        (float(pagerank[i]), note_id))
        
        conn.commit()
        
        elapsed = time.time() - start
        logging.info(f"PageRank calculated for {n} notes in {elapsed:.2f}s")
        
    except Exception as e:
        logging.error(f"Error calculating PageRank: {e}")

def calculate_pagerank_if_needed(conn: sqlite3.Connection):
    """Lazily calculate PageRank only when needed"""
    global PAGERANK_DIRTY, PAGERANK_CACHE_TIME
    
    current_time = time.time()
    
    # Recalculate if dirty or cache expired
    if PAGERANK_DIRTY or (current_time - PAGERANK_CACHE_TIME > PAGERANK_CACHE_SECONDS):
        calculate_pagerank_scores(conn)
        PAGERANK_DIRTY = False
        PAGERANK_CACHE_TIME = current_time

def create_temporal_edges(note_id: int, conn: sqlite3.Connection):
    """Create temporal edges to previous notes"""
    try:
        # Get previous N notes
        prev_notes = conn.execute('''
            SELECT id FROM notes 
            WHERE id < ? 
            ORDER BY id DESC 
            LIMIT ?
        ''', (note_id, TEMPORAL_EDGES)).fetchall()
        
        now = datetime.now().isoformat()
        for prev in prev_notes:
            conn.execute('''
                INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                VALUES (?, ?, 'temporal', 1.0, ?)
            ''', (note_id, prev[0], now))
            conn.execute('''
                INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                VALUES (?, ?, 'temporal', 1.0, ?)
            ''', (prev[0], note_id, now))
    except Exception as e:
        logging.error(f"Error creating temporal edges: {e}")

def create_reference_edges(note_id: int, refs: List[int], conn: sqlite3.Connection):
    """Create reference edges to mentioned notes"""
    try:
        now = datetime.now().isoformat()
        for ref_id in refs:
            if ref_id < note_id:
                # Check if the referenced note exists
                exists = conn.execute('SELECT id FROM notes WHERE id = ?', (ref_id,)).fetchone()
                if exists:
                    conn.execute('''
                        INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                        VALUES (?, ?, 'reference', 2.0, ?)
                    ''', (note_id, ref_id, now))
                    conn.execute('''
                        INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                        VALUES (?, ?, 'referenced_by', 2.0, ?)
                    ''', (ref_id, note_id, now))
    except Exception as e:
        logging.error(f"Error creating reference edges: {e}")

def log_operation(op: str, dur_ms: int = None):
    """Log operation for stats tracking"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.execute(
                'INSERT INTO stats (operation, ts, dur_ms, author) VALUES (?, ?, ?, ?)',
                (op, datetime.now().isoformat(), dur_ms, CURRENT_AI_ID)
            )
    except:
        pass

def build_fts_query(terms: List[str], mode: str = 'or') -> str:
    """Build FTS5 query with OR or AND logic"""
    if not terms:
        return ""
    
    # Clean terms
    cleaned = []
    for term in terms:
        # Remove problematic characters
        term = re.sub(r'[.:"\'\(\)\[\]\{\}!@#$%^&*+=|\\<>,?/`~]', '', term)
        term = term.strip()
        if term:
            cleaned.append(term)
    
    if not cleaned:
        return ""
    
    if mode == 'or':
        # OR logic - any word matches
        return ' OR '.join(cleaned)
    else:
        # AND logic - all words must match
        return ' '.join(cleaned)

def progressive_search(query: str, conn: sqlite3.Connection, limit: int = 50) -> Optional[List]:
    """Progressive fallback search: full phrase → OR search → single term"""
    query = query.strip()
    if not query:
        return None
    
    # Try 1: Full phrase (exact)
    try:
        cursor = conn.execute('''
            SELECT DISTINCT n.* FROM notes n
            JOIN notes_fts ON n.id = notes_fts.rowid
            WHERE notes_fts MATCH ?
            ORDER BY n.pagerank DESC, n.created DESC
            LIMIT ?
        ''', (f'"{query}"', limit))
        results = cursor.fetchall()
        if results:
            return results
    except:
        pass
    
    # Try 2: OR search (any word)
    words = query.split()
    if len(words) > 1:
        or_query = build_fts_query(words, 'or')
        if or_query:
            try:
                cursor = conn.execute('''
                    SELECT DISTINCT n.* FROM notes n
                    JOIN notes_fts ON n.id = notes_fts.rowid
                    WHERE notes_fts MATCH ?
                    ORDER BY n.pagerank DESC, n.created DESC
                    LIMIT ?
                ''', (or_query, limit))
                results = cursor.fetchall()
                if results:
                    return results
            except:
                pass
    
    # Try 3: Largest single word
    longest_word = max(words, key=len) if words else query
    try:
        cursor = conn.execute('''
            SELECT DISTINCT n.* FROM notes n
            JOIN notes_fts ON n.id = notes_fts.rowid
            WHERE notes_fts MATCH ?
            ORDER BY n.pagerank DESC, n.created DESC
            LIMIT ?
        ''', (longest_word, limit))
        return cursor.fetchall()
    except:
        return None

def recall(query: str = None, tag: str = None, when: str = None, 
           pinned_only: bool = False, show_all: bool = False, 
           limit: int = 50, **kwargs) -> Dict:
    """Search notes with time-based filtering and smart defaults"""
    try:
        start = datetime.now()
        
        # Check for time-based query
        if when:
            start_time, end_time = parse_time_query(when)
            if not start_time:
                return {"msg": f"Didn't understand time query: '{when}'"}
        else:
            start_time, end_time = None, None
        
        # Use smarter default limit based on context
        if not show_all and not query and not tag and not when and not pinned_only:
            limit = DEFAULT_RECENT  # Now 30 instead of 60
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Calculate PageRank if needed
            calculate_pagerank_if_needed(conn)
            
            if pinned_only:
                # Just show pinned notes
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    WHERE pinned = 1
                    ORDER BY pagerank DESC, created DESC
                ''')
                notes = cursor.fetchall()
                
            elif when:
                # Time-based query
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    WHERE created >= ? AND created <= ?
                    ORDER BY created DESC
                    LIMIT ?
                ''', (start_time.isoformat(), end_time.isoformat(), limit))
                notes = cursor.fetchall()
            
            elif query:
                # Search mode with progressive fallback
                query = str(query).strip()
                
                # Use progressive search
                notes = progressive_search(query, conn, limit)
                
                if notes is None:
                    # Final fallback: partial content match
                    cursor = conn.execute('''
                        SELECT * FROM notes 
                        WHERE content LIKE ? OR summary LIKE ?
                        ORDER BY pinned DESC, pagerank DESC, created DESC
                        LIMIT ?
                    ''', (f'%{query}%', f'%{query}%', limit))
                    notes = cursor.fetchall()
            
            elif tag:
                # Tag filter mode
                tag = str(tag).lower().strip()
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    WHERE tags LIKE ?
                    ORDER BY pinned DESC, pagerank DESC, created DESC
                    LIMIT ?
                ''', (f'%"{tag}"%', limit))
                notes = cursor.fetchall()
            
            else:
                # Default: show pinned + recent
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    ORDER BY pinned DESC, pagerank DESC, created DESC
                    LIMIT ?
                ''', (limit,))
                notes = cursor.fetchall()
        
        if not notes:
            if query:
                return {"msg": f"No matches for '{query}'"}
            elif tag:
                return {"msg": f"No notes tagged '{tag}'"}
            elif when:
                return {"msg": f"No notes {when}"}
            else:
                return {"msg": "No notes yet"}
        
        # Format based on output format
        if OUTPUT_FORMAT == 'pipe':
            # Pipe format output (70% fewer tokens!)
            lines = []
            for note in notes:
                parts = []
                parts.append(str(note['id']))  # Just the number
                parts.append(format_time_contextual(note['created']))
                
                summ = note['summary'] or simple_summary(note['content'], 80)
                parts.append(summ)
                
                if note['pinned']:
                    parts.append('PIN')
                if note['pagerank'] > 0.01:
                    parts.append(f"★{note['pagerank']:.3f}")
                
                lines.append('|'.join(pipe_escape(p) for p in parts))
            
            result = {"notes": lines}
        else:
            # JSON format (traditional)
            formatted_notes = []
            for note in notes:
                formatted_notes.append({
                    'id': note['id'],
                    'time': format_time_contextual(note['created']),
                    'summary': note['summary'] or simple_summary(note['content'], 80),
                    'pinned': bool(note['pinned']),
                    'pagerank': round(note['pagerank'], 3) if note['pagerank'] > 0.01 else None
                })
            result = {"notes": formatted_notes}
        
        # Save operation
        save_last_operation('recall', result)
        
        # Log operation
        dur = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('recall', dur)
        
        return result
        
    except Exception as e:
        logging.error(f"Error in recall: {e}")
        return {"error": f"Recall failed: {str(e)}"}

def remember(content: str = None, summary: str = None, tags: List[str] = None, 
             linked_items: List[str] = None, **kwargs) -> Dict:
    """Save a note with automatic edge creation and cross-tool logging"""
    try:
        start = datetime.now()
        
        if content is None:
            content = kwargs.get('content', '')
        
        content = str(content).strip()
        if not content:
            content = f"Checkpoint {datetime.now().strftime('%H:%M')}"
        
        # Handle truncation
        truncated = False
        orig_len = len(content)
        if orig_len > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
            truncated = True
        
        # Extract references and entities
        refs = extract_references(content)
        entities = extract_entities(content)
        
        # Check for task patterns for cross-tool integration
        task_detected = False
        task_text = None
        for pattern in [r'TODO:\s*(.+)', r'TASK:\s*(.+)', r'- \[ \]\s*(.+)']:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                task_detected = True
                task_text = match.group(1).strip()
                break
        
        # Generate summary if not provided
        if summary:
            summary = clean_text(summary)[:MAX_SUMMARY_LENGTH]
        else:
            summary = simple_summary(content)
        
        # Process tags
        tags_json = None
        if tags:
            tags = [str(t).lower().strip() for t in tags if t]
            tags_json = json.dumps(tags) if tags else None
        
        # Store note
        with sqlite3.connect(str(DB_FILE)) as conn:
            created_time = datetime.now()
            
            # Detect or create session
            session_id = detect_or_create_session(None, created_time, conn)
            
            cursor = conn.execute(
                '''INSERT INTO notes (content, summary, tags, author, created, session_id, linked_items) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (content, summary, tags_json, CURRENT_AI_ID, created_time.isoformat(), 
                 session_id, json.dumps(linked_items) if linked_items else None)
            )
            note_id = cursor.lastrowid
            
            # Update session if needed
            if not session_id:
                session_id = detect_or_create_session(note_id, created_time, conn)
                if session_id:
                    conn.execute('UPDATE notes SET session_id = ? WHERE id = ?', (session_id, note_id))
            
            # Create all edge types
            create_temporal_edges(note_id, conn)
            if refs:
                create_reference_edges(note_id, refs, conn)
            if entities:
                create_entity_edges(note_id, entities, conn)
            if session_id:
                create_session_edges(note_id, session_id, conn)
            
            conn.commit()
            
            # Mark PageRank as dirty
            global PAGERANK_DIRTY
            PAGERANK_DIRTY = True
        
        # Cross-tool integration: Create task if detected
        if task_detected and task_text:
            try:
                # Write to integration file for task manager to pick up
                integration_data = {
                    'source': 'notebook',
                    'source_id': note_id,
                    'action': 'create_task',
                    'task': task_text[:500],
                    'created': created_time.isoformat()
                }
                with open(TASK_INTEGRATION_FILE, 'a') as f:
                    f.write(json.dumps(integration_data) + '\n')
            except:
                pass  # Silent fail for integration
        
        # Save operation
        save_last_operation('remember', {'id': note_id, 'summary': summary})
        
        # Log stats
        dur = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('remember', dur)
        
        # Return minimal response
        if OUTPUT_FORMAT == 'pipe':
            result = f"{note_id}|now|{summary}"
            if truncated:
                result += f"|truncated:{orig_len}"
            if refs or entities:
                result += f"|edges:{len(refs)}r/{len(entities)}e"
            if task_detected:
                result += "|task_created"
            return {"saved": result}
        else:
            result = {"id": note_id, "time": "now", "summary": summary}
            if truncated:
                result["truncated"] = orig_len
            if refs or entities:
                result["edges"] = f"{len(refs)}refs/{len(entities)}ent"
            if task_detected:
                result["task_created"] = True
            return result
        
    except Exception as e:
        logging.error(f"Error in remember: {e}")
        return {"error": f"Failed to save: {str(e)}"}

def get_status(**kwargs) -> Dict:
    """Get current state with minimal decoration"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Calculate PageRank if needed
            calculate_pagerank_if_needed(conn)
            
            # Get counts
            total_notes = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            pinned_count = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = 1').fetchone()[0]
            edge_count = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
            entities_count = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
            sessions_count = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
            vault_items = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
            
            # Get recent activity
            recent = conn.execute('''
                SELECT id, created FROM notes 
                ORDER BY created DESC 
                LIMIT 1
            ''').fetchone()
            
            last_activity = format_time_contextual(recent['created']) if recent else "never"
        
        if OUTPUT_FORMAT == 'pipe':
            # Pipe format status
            parts = [
                f"notes:{total_notes}",
                f"pinned:{pinned_count}",
                f"edges:{edge_count}",
                f"entities:{entities_count}",
                f"sessions:{sessions_count}",
                f"vault:{vault_items}",
                f"last:{last_activity}",
                f"id:{CURRENT_AI_ID}"
            ]
            return {"status": '|'.join(parts)}
        else:
            # JSON format
            return {
                "notes": total_notes,
                "pinned": pinned_count,
                "edges": edge_count,
                "entities": entities_count,
                "sessions": sessions_count,
                "vault": vault_items,
                "last": last_activity,
                "identity": CURRENT_AI_ID
            }
        
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {"error": f"Status failed: {str(e)}"}

def pin_note(id: Any = None, **kwargs) -> Dict:
    """Pin an important note with smart ID resolution"""
    try:
        if id is None:
            id = kwargs.get('id')
            
        # Check for "last" keyword
        if id == "last":
            last_op = get_last_operation()
            if last_op and last_op['type'] == 'remember':
                id = last_op['result'].get('id')
            else:
                # Get most recent note
                with sqlite3.connect(str(DB_FILE)) as conn:
                    recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
                    if recent:
                        id = recent[0]
                    else:
                        return {"error": "No notes to pin"}
        
        if id is None:
            return {"error": "No ID provided"}
        
        # Clean ID - just numbers
        if isinstance(id, str):
            id = re.sub(r'[^\d]', '', id)
        
        if not id or id == '':
            return {"error": "Invalid ID"}
        
        try:
            id = int(id)
        except (ValueError, TypeError):
            return {"error": f"Invalid ID: {id}"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute('UPDATE notes SET pinned = 1 WHERE id = ?', (id,))
            
            if cursor.rowcount == 0:
                return {"error": f"Note {id} not found"}
            
            # Get the note summary
            note = conn.execute('SELECT summary, content FROM notes WHERE id = ?', (id,)).fetchone()
            summ = note[0] or simple_summary(note[1], 60)
        
        save_last_operation('pin', {'id': id})
        
        if OUTPUT_FORMAT == 'pipe':
            return {"pinned": f"{id}|{summ}"}
        else:
            return {"pinned": id, "summary": summ}
        
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
        
        # Clean ID
        if isinstance(id, str):
            id = re.sub(r'[^\d]', '', id)
        
        if not id or id == '':
            return {"error": "Invalid ID"}
        
        try:
            id = int(id)
        except (ValueError, TypeError):
            return {"error": f"Invalid ID: {id}"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute('UPDATE notes SET pinned = 0 WHERE id = ?', (id,))
            
            if cursor.rowcount == 0:
                return {"error": f"Note {id} not found"}
        
        save_last_operation('unpin', {'id': id})
        
        return {"unpinned": id}
        
    except Exception as e:
        logging.error(f"Error in unpin_note: {e}")
        return {"error": f"Failed to unpin: {str(e)}"}

def get_full_note(id: Any = None, **kwargs) -> Dict:
    """Get complete note with all connections - supports smart ID resolution"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        # Check for "last" keyword
        if id == "last":
            last_op = get_last_operation()
            if last_op and last_op['type'] == 'remember':
                id = last_op['result'].get('id')
            else:
                # Get most recent note
                with sqlite3.connect(str(DB_FILE)) as conn:
                    recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
                    if recent:
                        id = recent[0]
                    else:
                        return {"error": "No notes exist"}
        
        if id is None:
            return {"error": "No ID provided"}
        
        # Clean ID - support partial matching
        if isinstance(id, str):
            clean_id = re.sub(r'[^\d]', '', id)
            if clean_id:
                # Try exact match first
                try:
                    id = int(clean_id)
                except:
                    return {"error": f"Invalid ID: {id}"}
            else:
                return {"error": "Invalid ID"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Try exact match
            note = conn.execute('SELECT * FROM notes WHERE id = ?', (id,)).fetchone()
            
            # If not found, try partial match (e.g., "45" finds 456)
            if not note and isinstance(id, int):
                id_str = str(id)
                note = conn.execute('''
                    SELECT * FROM notes 
                    WHERE CAST(id AS TEXT) LIKE ?
                    ORDER BY id DESC
                    LIMIT 1
                ''', (f'%{id_str}%',)).fetchone()
            
            if not note:
                return {"error": f"Note {id} not found"}
            
            # Use the actual note ID
            actual_id = note['id']
            
            # Get edges
            edges_out = conn.execute('''
                SELECT to_id, type FROM edges 
                WHERE from_id = ? 
                ORDER BY type, created DESC
            ''', (actual_id,)).fetchall()
            
            edges_in = conn.execute('''
                SELECT from_id, type FROM edges 
                WHERE to_id = ? 
                ORDER BY type, created DESC
            ''', (actual_id,)).fetchall()
            
            # Get entities
            entities = conn.execute('''
                SELECT e.name, e.type FROM entities e
                JOIN entity_notes en ON e.id = en.entity_id
                WHERE en.note_id = ?
            ''', (actual_id,)).fetchall()
        
        save_last_operation('get_full_note', {'id': actual_id})
        
        # Format response
        result = {
            "id": note['id'],
            "author": note['author'],
            "created": note['created'],
            "summary": note['summary'] or simple_summary(note['content'], 100),
            "content": note['content'],
            "pinned": bool(note['pinned']),
            "pagerank": round(note['pagerank'], 4)
        }
        
        if note['tags']:
            result["tags"] = json.loads(note['tags'])
        
        if entities:
            result["entities"] = [f"@{e['name']}" for e in entities]
        
        if edges_out:
            edges_by_type = {}
            for edge in edges_out:
                if edge['type'] not in edges_by_type:
                    edges_by_type[edge['type']] = []
                edges_by_type[edge['type']].append(edge['to_id'])
            result["edges_out"] = edges_by_type
        
        if edges_in:
            edges_by_type = {}
            for edge in edges_in:
                if edge['type'] not in edges_by_type:
                    edges_by_type[edge['type']] = []
                edges_by_type[edge['type']].append(edge['from_id'])
            result["edges_in"] = edges_by_type
        
        return result
        
    except Exception as e:
        logging.error(f"Error in get_full_note: {e}")
        return {"error": f"Failed to retrieve: {str(e)}"}

# Keep remaining functions unchanged (vault_store, vault_retrieve, vault_list, batch, etc.)
# ... [rest of the code remains the same] ...

# Initialize database
migrate_to_v41()
init_db()

# The rest of the code (vault functions, handle_tools_call, main) remains unchanged
# but I need to include it for completeness...

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
        return {"stored": key}
        
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
        
        if OUTPUT_FORMAT == 'pipe':
            keys = []
            for item in items:
                keys.append(f"{item['key']}|{format_time_contextual(item['updated'])}")
            return {"vault_keys": keys}
        else:
            keys = []
            for item in items:
                keys.append({
                    'key': item['key'],
                    'updated': format_time_contextual(item['updated'])
                })
            return {"vault_keys": keys}
        
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
            'pin': pin_note,  # Alias
            'unpin_note': unpin_note,
            'unpin': unpin_note,  # Alias
            'vault_store': vault_store,
            'vault_retrieve': vault_retrieve,
            'get_full_note': get_full_note,
            'get': get_full_note,  # Alias
            'status': get_status
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
    """Route tool calls with minimal formatting"""
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
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Unknown tool: {tool_name}"
            }]
        }
    
    # Execute tool
    result = tools[tool_name](**tool_args)
    
    # Format response minimally
    text_parts = []
    
    if "error" in result:
        text_parts.append(f"Error: {result['error']}")
    elif OUTPUT_FORMAT == 'pipe' and "notes" in result and isinstance(result["notes"], list):
        # Pipe format for notes
        text_parts.extend(result["notes"])
    elif "saved" in result:
        text_parts.append(result["saved"])
    elif "pinned" in result:
        text_parts.append(str(result["pinned"]))
    elif "unpinned" in result:
        text_parts.append(f"Unpinned {result['unpinned']}")
    elif "stored" in result:
        text_parts.append(f"Stored {result['stored']}")
    elif "status" in result:
        text_parts.append(result["status"])
    elif "vault_keys" in result:
        if OUTPUT_FORMAT == 'pipe':
            text_parts.extend(result["vault_keys"])
        else:
            text_parts.append(json.dumps(result["vault_keys"]))
    elif "msg" in result:
        text_parts.append(result["msg"])
    elif "batch_results" in result:
        text_parts.append(f"Batch: {result.get('count', 0)}")
        for r in result["batch_results"]:
            if isinstance(r, dict):
                if "error" in r:
                    text_parts.append(f"Error: {r['error']}")
                elif "saved" in r:
                    text_parts.append(r["saved"])
                elif "pinned" in r:
                    text_parts.append(str(r["pinned"]))
                else:
                    text_parts.append(json.dumps(r))
            else:
                text_parts.append(str(r))
    else:
        # Default to JSON for complex structures
        text_parts.append(json.dumps(result))
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Done"
        }]
    }

def main():
    """MCP server main loop"""
    logging.info(f"Notebook MCP v{VERSION} starting...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Database: {DB_FILE}")
    logging.info("v4.1 features enabled:")
    logging.info(f"- Output format: {OUTPUT_FORMAT}")
    logging.info(f"- Search mode: {SEARCH_MODE}")
    logging.info(f"- DEFAULT_RECENT: {DEFAULT_RECENT} (reduced from 60)")
    logging.info("- Time-based recall (when='yesterday')")
    logging.info("- Smart ID resolution ('last' keyword)")
    logging.info("- Cross-tool integration hooks")
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
                        "name": "notebook",
                        "version": VERSION,
                        "description": "Integrated memory: 70% fewer tokens, time queries, smart IDs"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "get_status",
                            "description": "See current state",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "remember",
                            "description": "Save note (auto-creates tasks from TODO/TASK patterns)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "What to remember"
                                    },
                                    "summary": {
                                        "type": "string",
                                        "description": "Brief summary (optional)"
                                    },
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Tags (optional)"
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
                            "description": "Search notes (OR logic), time queries (when='yesterday'), or pinned only",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search term"
                                    },
                                    "when": {
                                        "type": "string",
                                        "description": "Time query: today, yesterday, morning, this week, etc."
                                    },
                                    "tag": {
                                        "type": "string",
                                        "description": "Filter by tag"
                                    },
                                    "pinned_only": {
                                        "type": "boolean",
                                        "description": "Show only pinned notes"
                                    },
                                    "show_all": {
                                        "type": "boolean",
                                        "description": "Show more results"
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Max results"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "pin_note",
                            "description": "Pin note (use 'last' for recent)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Note ID or 'last'"
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "unpin_note",
                            "description": "Unpin note",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Note ID"
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "get_full_note",
                            "description": "Get complete note (use 'last' for recent, supports partial ID match)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Note ID, 'last', or partial ID"
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
