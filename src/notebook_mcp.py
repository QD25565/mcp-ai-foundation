#!/usr/bin/env python3
"""
NOTEBOOK MCP v3.0.0 - KNOWLEDGE GRAPH EDITION
=============================================
Linear memory transformed into an intelligent knowledge graph.
Now with entity extraction, session detection, AND PageRank scoring!

Core improvements (v3.0):
- Entity extraction: Auto-links @mentions, tools, projects
- Session detection: Groups work bursts (30-min windows)
- PageRank scoring: Important notes naturally surface
- Auto-references: Detects note 417, p123, #456
- Temporal edges: Links to previous 3 notes
- All invisible to API - same simple interface!

Performance optimizations (thanks @Gemini):
- Lazy PageRank calculation (only on read operations)
- Word-boundary entity matching (no false positives)
- Proper session table usage (enables analytics)

Core functions (unchanged API):
- remember(content, summary=None, tags=None) - Now with 5 edge types!
- recall(query=None, tag=None, limit=50) - PageRank-scored results
- pin_note(id) - Pin important note
- unpin_note(id) - Unpin note
- get_status() - Shows graph stats
- get_full_note(id) - See all connections
- vault_store/retrieve/list - Secure storage

The magic happens automatically!
=============================================
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
VERSION = "3.0.0"

# Limits
MAX_CONTENT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 200
MAX_RESULTS = 100
BATCH_MAX = 50
DEFAULT_RECENT = 60
TEMPORAL_EDGES = 3  # Link to 3 previous notes
SESSION_GAP_MINUTES = 30  # New session after 30 min gap
PAGERANK_ITERATIONS = 50  # PageRank convergence iterations
PAGERANK_DAMPING = 0.85  # PageRank damping factor
PAGERANK_CACHE_SECONDS = 300  # Cache PageRank for 5 minutes

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
sess_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Known entities cache (populated from DB)
KNOWN_ENTITIES = set()
KNOWN_TOOLS = {'teambook', 'firebase', 'gemini', 'claude', 'jetbrains', 'github', 
                'slack', 'discord', 'vscode', 'git', 'docker', 'python', 'node',
                'react', 'vue', 'angular', 'tensorflow', 'pytorch', 'aws', 'gcp',
                'azure', 'kubernetes', 'redis', 'postgres', 'mongodb', 'sqlite'}

# PageRank lazy calculation flags
PAGERANK_DIRTY = True
PAGERANK_CACHE_TIME = 0

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
    
    # Sessions table (PROPERLY USED in v3.0)
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

def migrate_to_v30():
    """Migration for v3.0 - add entity, session, and PageRank support"""
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
        
        # Check if entities table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
        if not cursor.fetchone():
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
        
        # Check if entity_notes table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entity_notes'")
        if not cursor.fetchone():
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
        
        # Check if sessions table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if not cursor.fetchone():
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
    """Extract entities from content with WORD BOUNDARIES (FIX from @Gemini)
    Returns: List of (entity_name, entity_type) tuples
    """
    entities = []
    content_lower = content.lower()
    
    # Pattern 1: @mentions (people/AIs)
    mentions = re.findall(r'@([\w-]+)', content, re.IGNORECASE)
    entities.extend((m.lower(), 'mention') for m in mentions)
    
    # Pattern 2: Tool/project names with WORD BOUNDARIES (FIX)
    for tool in KNOWN_TOOLS:
        # Use word boundaries to prevent substring matches
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
    
    # Pattern 6: Known entities from database with WORD BOUNDARIES
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
    """Detect existing session or create new one (PROPERLY USES sessions table)"""
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
        
        # Create bidirectional edges between this note and all session notes
        for other_note in session_notes:
            other_id = other_note[0]
            # Edge from this note to other
            conn.execute('''
                INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                VALUES (?, ?, 'session', 1.5, ?)
            ''', (note_id, other_id, now))
            # Edge from other to this note
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
                # Create bidirectional entity edges
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
    """Calculate PageRank scores for all notes (EXPENSIVE - call lazily)"""
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
    """Lazily calculate PageRank only when needed (FIX from @Gemini)"""
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
            # Also create reverse edge for bidirectional traversal
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
            if ref_id < note_id:  # Only link to existing notes
                # Check if the referenced note exists
                exists = conn.execute('SELECT id FROM notes WHERE id = ?', (ref_id,)).fetchone()
                if exists:
                    # Create reference edge with higher weight
                    conn.execute('''
                        INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created)
                        VALUES (?, ?, 'reference', 2.0, ?)
                    ''', (note_id, ref_id, now))
                    # Also create reverse edge
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

def remember(content: str = None, summary: str = None, tags: List[str] = None, 
             linked_items: List[str] = None, **kwargs) -> Dict:
    """Save a note with ALL FIVE edge types (NO PageRank calculation here!)"""
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
        
        # Extract references
        refs = extract_references(content)
        
        # Extract entities
        entities = extract_entities(content)
        
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
            
            # Detect or create session (PROPERLY using sessions table)
            session_id = detect_or_create_session(None, created_time, conn)  # We'll update after insert
            
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
            
            # Mark PageRank as dirty (needs recalculation) but DON'T calculate now
            global PAGERANK_DIRTY
            PAGERANK_DIRTY = True
        
        # Log stats
        dur = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('remember', dur)
        
        # Return result with edge info
        result = {"saved": f"{note_id} now {summary}"}
        if truncated:
            result["truncated"] = f"from {orig_len} chars"
        
        # Report connections made
        connections = []
        if refs:
            connections.append(f"→{len(refs)}refs")
        if entities:
            connections.append(f"@{len(entities)}entities")
        if session_id:
            connections.append(f"ses{session_id}")
        if connections:
            result["edges"] = " ".join(connections)
        
        return result
        
    except Exception as e:
        logging.error(f"Error in remember: {e}")
        return {"error": f"Failed to save: {str(e)}"}

def recall(query: str = None, tag: str = None, show_all: bool = False, 
           limit: int = 50, **kwargs) -> Dict:
    """Search notes with LAZY PageRank calculation and scoring"""
    try:
        start = datetime.now()
        
        # Use higher default limit
        if not show_all and not query and not tag:
            limit = DEFAULT_RECENT
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Calculate PageRank if needed (LAZY!)
            calculate_pagerank_if_needed(conn)
            
            if query:
                # Search mode with ALL edge types and PageRank
                query = str(query).strip()
                
                # Get direct matches and ALL edge-connected notes
                cursor = conn.execute('''
                    WITH direct_matches AS (
                        SELECT DISTINCT n.id FROM notes n
                        JOIN notes_fts ON n.id = notes_fts.rowid
                        WHERE notes_fts MATCH ?
                    ),
                    edge_matches AS (
                        SELECT DISTINCT e.to_id as id
                        FROM edges e
                        WHERE e.from_id IN (SELECT id FROM direct_matches)
                        UNION
                        SELECT DISTINCT e.from_id as id
                        FROM edges e
                        WHERE e.to_id IN (SELECT id FROM direct_matches)
                    )
                    SELECT n.*, 
                           CASE WHEN n.id IN (SELECT id FROM direct_matches) THEN 1 ELSE 0 END as is_direct
                    FROM notes n
                    WHERE n.id IN (
                        SELECT id FROM direct_matches
                        UNION
                        SELECT id FROM edge_matches
                    )
                    ORDER BY 
                        is_direct DESC,
                        n.pinned DESC,
                        (n.pagerank * 1000) DESC,  -- PageRank weighted heavily
                        n.created DESC
                    LIMIT ?
                ''', (query, limit))
            
            elif tag:
                # Tag filter mode with PageRank
                tag = str(tag).lower().strip()
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    WHERE tags LIKE ?
                    ORDER BY pinned DESC, (pagerank * 1000) DESC, created DESC
                    LIMIT ?
                ''', (f'%"{tag}"%', limit))
            
            else:
                # Default: show pinned + recent, weighted by PageRank
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    ORDER BY pinned DESC, (pagerank * 100) DESC, created DESC
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
        
        # Format results
        lines = []
        
        # Get counts including new edge types
        with sqlite3.connect(str(DB_FILE)) as conn:
            total = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            pinned = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = 1').fetchone()[0]
            edges_all = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
            ref_edges = conn.execute("SELECT COUNT(*) FROM edges WHERE type = 'reference'").fetchone()[0]
            entity_edges = conn.execute("SELECT COUNT(*) FROM edges WHERE type = 'entity'").fetchone()[0]
            session_edges = conn.execute("SELECT COUNT(*) FROM edges WHERE type = 'session'").fetchone()[0]
            entities_count = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
            sessions_count = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
        
        # Header with graph stats
        header = f"{total} notes"
        if pinned > 0:
            header += f" | {pinned} pinned"
        if edges_all > 0:
            header += f" | {edges_all} edges"
            edge_info = []
            if ref_edges > 0:
                edge_info.append(f"{ref_edges}ref")
            if entity_edges > 0:
                edge_info.append(f"{entity_edges}ent")
            if session_edges > 0:
                edge_info.append(f"{session_edges}ses")
            if edge_info:
                header += f" ({'/'.join(edge_info)})"
        if entities_count > 0:
            header += f" | {entities_count} entities"
        if sessions_count > 0:
            header += f" | {sessions_count} sessions"
        if query:
            header += f" | searching '{query}'"
        elif tag:
            header += f" | tag '{tag}'"
        header += f" | last {format_time_contextual(notes[0]['created'])}"
        lines.append(header)
        
        # Group by importance (PageRank) and pinned status
        pinned_notes = [n for n in notes if n['pinned']]
        high_rank_notes = [n for n in notes if not n['pinned'] and n['pagerank'] > 0.01]
        regular_notes = [n for n in notes if not n['pinned'] and n['pagerank'] <= 0.01]
        
        if pinned_notes:
            lines.append("\nPINNED")
            for note in pinned_notes:
                time_str = format_time_contextual(note['created'])
                summ = note['summary'] or simple_summary(note['content'])
                pr = f" ★{note['pagerank']:.3f}" if note['pagerank'] > 0.01 else ""
                lines.append(f"p{note['id']} {time_str} {summ}{pr}")
        
        if high_rank_notes:
            lines.append("\nIMPORTANT")  # High PageRank notes
            for note in high_rank_notes:
                time_str = format_time_contextual(note['created'])
                summ = note['summary'] or simple_summary(note['content'])
                pr = f" ★{note['pagerank']:.3f}"
                lines.append(f"{note['id']} {time_str} {summ}{pr}")
        
        if regular_notes:
            if pinned_notes or high_rank_notes:
                lines.append("\nRECENT")
            for note in regular_notes:
                time_str = format_time_contextual(note['created'])
                summ = note['summary'] or simple_summary(note['content'])
                lines.append(f"{note['id']} {time_str} {summ}")
        
        # Log operation
        dur = int((datetime.now() - start).total_seconds() * 1000)
        log_operation('recall', dur)
        
        return {"notes": "\n".join(lines)}
        
    except Exception as e:
        logging.error(f"Error in recall: {e}")
        return {"error": f"Recall failed: {str(e)}"}

def get_status(**kwargs) -> Dict:
    """Get current state with graph statistics (WITH LAZY PageRank)"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Calculate PageRank if needed (LAZY!)
            calculate_pagerank_if_needed(conn)
            
            # Get comprehensive counts
            total_notes = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            my_notes = conn.execute('SELECT COUNT(*) FROM notes WHERE author = ?', 
                                   (CURRENT_AI_ID,)).fetchone()[0]
            pinned_count = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = 1').fetchone()[0]
            vault_items = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
            
            # Edge counts by type
            edge_count = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
            edge_types = conn.execute('''
                SELECT type, COUNT(*) as cnt FROM edges 
                GROUP BY type
            ''').fetchall()
            
            # Entity and session counts
            entities_count = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
            sessions_count = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
            top_entities = conn.execute('''
                SELECT name, mention_count FROM entities 
                ORDER BY mention_count DESC 
                LIMIT 5
            ''').fetchall()
            
            # Get highest PageRank notes
            top_pagerank = conn.execute('''
                SELECT id, summary, content, pagerank FROM notes 
                WHERE pagerank > 0.01
                ORDER BY pagerank DESC 
                LIMIT 5
            ''').fetchall()
            
            # Get ALL pinned notes
            pinned = conn.execute('''
                SELECT id, summary, content, created FROM notes 
                WHERE pinned = 1
                ORDER BY created DESC
            ''').fetchall()
            
            # Get recent notes
            recent = conn.execute('''
                SELECT id, summary, content, created, pagerank FROM notes 
                WHERE pinned = 0
                ORDER BY created DESC 
                LIMIT 20
            ''').fetchall()
            
            last_activity = format_time_contextual(recent[0]['created'] if recent else 
                                                  (pinned[0]['created'] if pinned else None))
        
        # Build response
        lines = []
        
        # Header with comprehensive stats
        header = f"{total_notes} notes"
        if pinned_count > 0:
            header += f" | {pinned_count} pinned"
        header += f" | {edge_count} edges"
        
        # Edge breakdown
        edge_info = []
        for edge_type in edge_types:
            edge_info.append(f"{edge_type['cnt']}{edge_type['type'][:3]}")
        if edge_info:
            header += f" ({'/'.join(edge_info)})"
        
        header += f" | {entities_count} entities | {sessions_count} sessions | {vault_items} vault | last {last_activity}"
        lines.append(header)
        
        # Top entities
        if top_entities:
            lines.append("\nTOP ENTITIES")
            for entity in top_entities:
                lines.append(f"@{entity['name']} ({entity['mention_count']}×)")
        
        # Highest PageRank (most important notes)
        if top_pagerank:
            lines.append("\nMOST REFERENCED")
            for note in top_pagerank:
                summ = note['summary'] or simple_summary(note['content'])
                lines.append(f"{note['id']} ★{note['pagerank']:.3f} {summ}")
        
        # Pinned notes
        if pinned:
            lines.append("\nPINNED")
            for note in pinned:
                time_str = format_time_contextual(note['created'])
                summ = note['summary'] or simple_summary(note['content'])
                lines.append(f"p{note['id']} {time_str} {summ}")
        
        # Recent notes
        if recent:
            lines.append("\nRECENT")
            for note in recent:
                time_str = format_time_contextual(note['created'])
                summ = note['summary'] or simple_summary(note['content'])
                pr = f" ★{note['pagerank']:.3f}" if note['pagerank'] > 0.01 else ""
                lines.append(f"{note['id']} {time_str} {summ}{pr}")
        
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
        
        # Handle string IDs
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
            summ = note[0] or simple_summary(note[1])
        
        return {"pinned": f"p{id} {summ}"}
        
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
        
        # Handle string IDs
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
    """Retrieve complete content with all edges, entities, and session info"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        if id is None:
            return {"error": "No ID provided"}
        
        # Handle string IDs
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
            
            # Get ALL edges
            edges_out = conn.execute('''
                SELECT to_id, type FROM edges 
                WHERE from_id = ? 
                ORDER BY type, created DESC
            ''', (id,)).fetchall()
            
            edges_in = conn.execute('''
                SELECT from_id, type FROM edges 
                WHERE to_id = ? 
                ORDER BY type, created DESC
            ''', (id,)).fetchall()
            
            # Get entities
            entities = conn.execute('''
                SELECT e.name, e.type FROM entities e
                JOIN entity_notes en ON e.id = en.entity_id
                WHERE en.note_id = ?
            ''', (id,)).fetchall()
            
            # Get session info if exists
            session_info = None
            if note['session_id']:
                session = conn.execute('''
                    SELECT * FROM sessions WHERE id = ?
                ''', (note['session_id'],)).fetchone()
                if session:
                    session_info = {
                        'id': session['id'],
                        'started': session['started'],
                        'ended': session['ended'],
                        'note_count': session['note_count']
                    }
        
        result = {
            "note_id": note['id'],
            "author": note['author'],
            "created": note['created'],
            "summary": note['summary'] or simple_summary(note['content']),
            "content": note['content'],
            "length": len(note['content']),
            "pinned": note['pinned'],
            "pagerank": note['pagerank']
        }
        
        # Include session
        if session_info:
            result["session"] = session_info
        
        # Include tags
        if note['tags']:
            result["tags"] = json.loads(note['tags'])
        
        if note['linked_items']:
            result["linked"] = json.loads(note['linked_items'])
        
        # Include entities
        if entities:
            result["entities"] = [f"@{e['name']}({e['type']})" for e in entities]
        
        # Include edges organized by type
        if edges_out:
            edges_by_type = {}
            for edge in edges_out:
                edge_type = edge['type']
                if edge_type not in edges_by_type:
                    edges_by_type[edge_type] = []
                edges_by_type[edge_type].append(edge['to_id'])
            result["edges_out"] = edges_by_type
        
        if edges_in:
            edges_by_type = {}
            for edge in edges_in:
                edge_type = edge['type']
                if edge_type not in edges_by_type:
                    edges_by_type[edge_type] = []
                edges_by_type[edge_type].append(edge['from_id'])
            result["edges_in"] = edges_by_type
        
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
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Unknown tool: {tool_name}\nAvailable: {', '.join(tools.keys())}"
            }]
        }
    
    # Execute tool
    result = tools[tool_name](**tool_args)
    
    # Format response
    text_parts = []
    
    if not isinstance(result, dict):
        text_parts.append(str(result))
    elif "error" in result:
        text_parts.append(f"Error {result['error']}")
    elif "note_id" in result:  # get_full_note
        text_parts.append(f"{result['note_id']} by {result.get('author', 'Unknown')}")
        text_parts.append(f"Created {result.get('created', '')}")
        text_parts.append(f"Summary {result.get('summary', '')}")
        text_parts.append(f"PageRank ★{result.get('pagerank', 0):.4f}")
        if result.get('pinned'):
            text_parts.append("Status PINNED")
        if result.get('session'):
            ses = result['session']
            text_parts.append(f"Session #{ses['id']} ({ses['note_count']} notes)")
        if result.get('tags'):
            tags_str = ', '.join(str(tag) for tag in result['tags'])
            text_parts.append(f"Tags {tags_str}")
        if result.get('entities'):
            text_parts.append(f"Entities {', '.join(result['entities'])}")
        if result.get('edges_out'):
            for edge_type, ids in result['edges_out'].items():
                ids_str = ', '.join(str(i) for i in ids[:5])  # Show first 5
                if len(ids) > 5:
                    ids_str += f" +{len(ids)-5}"
                text_parts.append(f"→ {edge_type}: {ids_str}")
        if result.get('edges_in'):
            for edge_type, ids in result['edges_in'].items():
                ids_str = ', '.join(str(i) for i in ids[:5])  # Show first 5
                if len(ids) > 5:
                    ids_str += f" +{len(ids)-5}"
                text_parts.append(f"← {edge_type}: {ids_str}")
        text_parts.append(f"Length {result.get('length', 0)} chars")
        text_parts.append("---")
        text_parts.append(result.get("content", ""))
    elif "status" in result:
        text_parts.append(result["status"])
    elif "notes" in result:
        text_parts.append(result["notes"])
    elif "saved" in result:
        parts = [result["saved"]]
        if "truncated" in result:
            parts.append(f"({result['truncated']})")
        if "edges" in result:
            parts.append(result["edges"])
        text_parts.append(" ".join(parts))
    elif "pinned" in result:
        text_parts.append(result["pinned"])
    elif "unpinned" in result:
        text_parts.append(result["unpinned"])
    elif "stored" in result:
        text_parts.append(result["stored"])
    elif "key" in result and "value" in result:
        text_parts.append(f"Vault[{result['key']}] = {result['value']}")
    elif "vault_keys" in result:
        text_parts.append(f"Vault ({result.get('count', 0)} keys)")
        text_parts.extend(str(k) for k in result["vault_keys"])
    elif "msg" in result:
        text_parts.append(result["msg"])
    elif "batch_results" in result:
        text_parts.append(f"Batch {result.get('count', 0)} operations")
        for i, r in enumerate(result["batch_results"], 1):
            if isinstance(r, dict):
                if "error" in r:
                    text_parts.append(f"{i}. Error {r['error']}")
                elif "saved" in r:
                    text_parts.append(f"{i}. {r['saved']}")
                elif "pinned" in r:
                    text_parts.append(f"{i}. {r['pinned']}")
                elif "unpinned" in r:
                    text_parts.append(f"{i}. {r['unpinned']}")
                elif "stored" in r:
                    text_parts.append(f"{i}. {r['stored']}")
                elif "note_id" in r:
                    text_parts.append(f"{i}. Note {r['note_id']} {r.get('summary', '...')}")
                elif "notes" in r:
                    text_parts.append(f"{i}. Recall {r['notes'].splitlines()[0]}")
                elif "key" in r and "value" in r:
                    text_parts.append(f"{i}. Vault[{r['key']}] = {r['value']}")
                elif "msg" in r:
                    text_parts.append(f"{i}. {r['msg']}")
                else:
                    text_parts.append(f"{i}. {json.dumps(r)}")
            else:
                text_parts.append(f"{i}. {r}")
    else:
        logging.warning(f"Unhandled result format from {tool_name}: {result}")
        text_parts.append(json.dumps(result))
    
    text_parts = [str(item) for item in text_parts]
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Ready"
        }]
    }

# Initialize database
migrate_to_v30()
init_db()

def main():
    """MCP server main loop"""
    logging.info(f"Notebook MCP v{VERSION} starting...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Database: {DB_FILE}")
    logging.info("Knowledge Graph features:")
    logging.info("- Entity extraction (word-boundary matching)")
    logging.info("- Session detection (proper sessions table)")
    logging.info("- PageRank scoring (lazy calculation)")
    logging.info("- Reference detection (note 123, p456)")
    logging.info("- Temporal edges (last 3 notes)")
    
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
                        "description": "Knowledge Graph Memory - production-ready with optimizations"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "get_status",
                            "description": "See current state with edges",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "remember",
                            "description": "Save note + auto temporal links + auto reference detection",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "What to remember (required)"
                                    },
                                    "summary": {
                                        "type": "string",
                                        "description": "Brief 1-3 sentence summary (optional)"
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
                            "description": "Search with edge traversal",
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
                            "description": "Get complete content with all edges",
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
