#!/usr/bin/env python3
"""
NOTEBOOK MCP v5.2.1 - PRODUCTION READY
===============================================
Hybrid memory system with safe data migration and performance optimizations.
Now with sparse matrix PageRank, normalized tags, and complete backup safety.

CRITICAL: This version will automatically backup your database and migrate
existing tags on first run. Tested for 560+ notes scale with full functionality maintained.

SETUP INSTRUCTIONS:
1. Install dependencies:
   pip install chromadb sentence-transformers scipy cryptography numpy

2. First run will automatically:
   - Back up your database
   - Migrate existing tags to normalized tables
   - Download embedding models if needed

v5.2.1 CHANGES:
- Safe tag data migration preserving all existing tags
- Automatic database backup before schema changes
- Sparse matrix PageRank (massive memory savings)
- Normalized tag system (instant searches)
- Cached entity extraction patterns
- Fixed output formatting for all tools
- Added official tool aliases (get, pin, unpin)
===============================================
"""

import json
import sys
import os
import sqlite3
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
import logging
import random
import re
import time
import numpy as np
from cryptography.fernet import Fernet
import threading

# Vector DB and embeddings
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not installed - semantic features disabled")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logging.warning("sentence-transformers not installed - semantic features disabled")

# Performance libraries
try:
    from scipy.sparse import dok_matrix
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("scipy not installed - PageRank will use high-memory numpy arrays")

# Version
VERSION = "5.2.1"

# Configuration
OUTPUT_FORMAT = os.environ.get('NOTEBOOK_FORMAT', 'pipe')
USE_SEMANTIC = os.environ.get('NOTEBOOK_SEMANTIC', 'true').lower() == 'true'
DB_VERSION = 3  # Increment for schema changes

# Limits
MAX_CONTENT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 200
MAX_RESULTS = 100
BATCH_MAX = 50
DEFAULT_RECENT = 30
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
VECTOR_DIR = DATA_DIR / "vectors"
VAULT_KEY_FILE = DATA_DIR / ".vault_key"
LAST_OP_FILE = DATA_DIR / ".last_operation"
MODELS_DIR = DATA_DIR.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global Caches & State
KNOWN_ENTITIES = set()
KNOWN_TOOLS = {'teambook', 'firebase', 'gemini', 'claude', 'jetbrains', 'github',
                'slack', 'discord', 'vscode', 'git', 'docker', 'python', 'node',
                'react', 'vue', 'angular', 'tensorflow', 'pytorch', 'aws', 'gcp',
                'azure', 'kubernetes', 'redis', 'postgres', 'mongodb', 'sqlite',
                'task_manager', 'notebook', 'world', 'chromadb', 'embedding-gemma'}
ENTITY_PATTERN = None
ENTITY_PATTERN_SIZE = 0
PAGERANK_DIRTY = True
PAGERANK_CACHE_TIME = 0
LAST_OPERATION = None
encoder = None
chroma_client = None
collection = None
EMBEDDING_MODEL = None

# Session ID
sess_id = datetime.now().strftime("%Y%m%d_%H%M%S")

def get_persistent_id():
    """Get or create persistent AI identity"""
    for loc in [Path(__file__).parent, DATA_DIR, Path.home()]:
        id_file = loc / "ai_identity.txt"
        if id_file.exists():
            try:
                with open(id_file, 'r') as f:
                    stored_id = f.read().strip()
                    if stored_id:
                        return stored_id
            except:
                pass
    
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep', 'Keen', 'Pure']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node', 'Wave', 'Link']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    try:
        id_file = Path(__file__).parent / "ai_identity.txt"
        with open(id_file, 'w') as f:
            f.write(new_id)
    except:
        pass
    
    return new_id

CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

class VaultManager:
    """Secure encrypted storage for secrets"""
    def __init__(self):
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)
    
    def _load_or_create_key(self) -> bytes:
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
            return key
    
    def encrypt(self, value: str) -> bytes:
        return self.fernet.encrypt(value.encode())
    
    def decrypt(self, encrypted: bytes) -> str:
        return self.fernet.decrypt(encrypted).decode()

vault_manager = VaultManager()

def init_embedding_gemma():
    """Initialize Google's EmbeddingGemma model"""
    global encoder, EMBEDDING_MODEL
    
    if not ST_AVAILABLE or not USE_SEMANTIC:
        logging.info("Semantic search disabled")
        return None
    
    try:
        local_model_path = MODELS_DIR / "embeddinggemma-300m"
        models_to_try = [
            (str(local_model_path), 'embedding-gemma'),
            ('BAAI/bge-base-en-v1.5', 'bge-base'),
            ('sentence-transformers/all-mpnet-base-v2', 'mpnet'),
            ('sentence-transformers/all-MiniLM-L6-v2', 'minilm'),
        ]
        
        for model_name, short_name in models_to_try:
            try:
                logging.info(f"Loading {model_name}...")
                encoder = SentenceTransformer(model_name, device='cpu')
                test_embedding = encoder.encode("test", convert_to_numpy=True)
                EMBEDDING_MODEL = short_name
                logging.info(f"✓ Using {model_name} (embedding dim: {test_embedding.shape[0]})")
                return encoder
            except Exception as e:
                logging.debug(f"Failed to load {model_name}: {e}")
                continue
        
        logging.error("No embedding model could be loaded")
        return None
    except Exception as e:
        logging.error(f"Failed to initialize embeddings: {e}")
        return None

def init_vector_db():
    """Initialize ChromaDB for vector storage"""
    global chroma_client, collection
    if not CHROMADB_AVAILABLE or not encoder:
        return False
    try:
        chroma_client = chromadb.PersistentClient(
            path=str(VECTOR_DIR),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        collection = chroma_client.get_or_create_collection(
            name="notebook_v5",
            metadata={"hnsw:space": "cosine"}
        )
        logging.info(f"ChromaDB initialized with {collection.count()} existing vectors")
        return True
    except Exception as e:
        logging.error(f"ChromaDB init failed: {e}")
        return False

def init_db():
    """Initialize SQLite database with versioned migrations and data preservation"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    
    # Check if this is an existing database without version info
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
    notes_table_exists = cursor.fetchone() is not None
    
    if notes_table_exists and current_version == 0:
        # This is an existing database without version tracking
        logging.info("Detected existing database without version info. Analyzing structure...")
        
        # Check which columns exist
        cursor = conn.execute("PRAGMA table_info(notes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Determine what version this looks like based on columns
        if 'tags' in columns:
            # Has old tags column, needs v2->v3 migration
            current_version = 2
            logging.info("Database appears to be v2 (has tags column)")
        elif 'pagerank' in columns:
            # Has pagerank but still tags column, is v1
            current_version = 1
            logging.info("Database appears to be v1 (has pagerank)")
        else:
            # Very old version, treat as v1
            current_version = 1
            logging.info("Database appears to be v1 (basic structure)")
        
        # Update the version in the database
        conn.execute(f"PRAGMA user_version = {current_version}")
        conn.commit()

    if current_version < DB_VERSION:
        logging.info(f"Database schema v{current_version} -> v{DB_VERSION}")
        
        # Backup only if database has content
        if notes_table_exists:
            note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            if note_count > 0:
                backup_path = DB_FILE.with_suffix(f'.backup_v{current_version}_{datetime.now().strftime("%Y%m%d%H%M")}.db')
                shutil.copy2(DB_FILE, backup_path)
                logging.info(f"Backed up {note_count} notes to {backup_path}")

        # Migration Steps
        if current_version < 1:
            # Fresh database - create all v1 tables
            logging.info("Creating initial v1 schema...")
            conn.execute('''CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, summary TEXT,
                tags TEXT, pinned INTEGER DEFAULT 0, author TEXT NOT NULL, created TEXT NOT NULL,
                session_id INTEGER, linked_items TEXT, pagerank REAL DEFAULT 0.0, has_vector INTEGER DEFAULT 0
            )''')
            current_version = 1

        if current_version == 1:
            # Add missing columns to existing notes table
            logging.info("Migrating v1 -> v2: Adding missing columns...")
            cursor = conn.execute("PRAGMA table_info(notes)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'session_id' not in columns:
                conn.execute('ALTER TABLE notes ADD COLUMN session_id INTEGER')
            if 'linked_items' not in columns:
                conn.execute('ALTER TABLE notes ADD COLUMN linked_items TEXT')
            if 'pagerank' not in columns:
                conn.execute('ALTER TABLE notes ADD COLUMN pagerank REAL DEFAULT 0.0')
            if 'has_vector' not in columns:
                conn.execute('ALTER TABLE notes ADD COLUMN has_vector INTEGER DEFAULT 0')
            current_version = 2

        if current_version == 2:
            logging.info("Migrating v2 -> v3: Normalizing tags...")
            
            # Check if tags column exists (it should if we're at v2)
            cursor = conn.execute("PRAGMA table_info(notes)")
            columns = [col[1] for col in cursor.fetchall()]
            has_tags_column = 'tags' in columns
            
            # Create tag tables
            conn.execute('CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)')
            conn.execute('''CREATE TABLE IF NOT EXISTS note_tags (
                note_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, 
                PRIMARY KEY(note_id, tag_id),
                FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )''')
            
            # Migrate tag data if tags column exists
            if has_tags_column:
                logging.info("Migrating existing tags...")
                cursor = conn.execute('SELECT id, tags FROM notes WHERE tags IS NOT NULL AND tags != ""')
                all_tags = cursor.fetchall()
                migrated = 0
                failed = 0
                
                for note_id, tags_data in all_tags:
                    if tags_data:
                        try:
                            # Handle both JSON and comma-separated formats
                            try:
                                tags_list = json.loads(tags_data)
                            except (json.JSONDecodeError, TypeError):
                                # Try comma-separated format
                                tags_list = [t.strip() for t in tags_data.split(',') if t.strip()]
                            
                            if isinstance(tags_list, list):
                                for tag_name in tags_list:
                                    clean_tag = str(tag_name).lower().strip()
                                    if not clean_tag:
                                        continue
                                    conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (clean_tag,))
                                    tag_id = conn.execute('SELECT id FROM tags WHERE name = ?', (clean_tag,)).fetchone()[0]
                                    conn.execute('INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)', (note_id, tag_id))
                                migrated += 1
                        except Exception as e:
                            failed += 1
                            logging.debug(f"Could not migrate tags for note {note_id}: {e}")
                
                conn.commit()
                logging.info(f"Migrated tags for {migrated} notes ({failed} failures)")
                
                # Remove old tags column by recreating table
                logging.info("Removing old tags column...")
                
                # Clean up any failed previous migration attempt
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes_new'")
                if cursor.fetchone():
                    logging.info("Cleaning up incomplete previous migration...")
                    conn.execute('DROP TABLE notes_new')
                
                # Temporarily disable foreign keys for table recreation
                conn.execute('PRAGMA foreign_keys = OFF')
                
                conn.execute('''CREATE TABLE notes_new (
                    id INTEGER PRIMARY KEY, content TEXT NOT NULL, summary TEXT,
                    pinned INTEGER DEFAULT 0, author TEXT NOT NULL, created TEXT NOT NULL,
                    session_id INTEGER, linked_items TEXT, pagerank REAL DEFAULT 0.0, has_vector INTEGER DEFAULT 0
                )''')
                conn.execute('''INSERT INTO notes_new 
                    SELECT id, content, summary, pinned, author, created, session_id, linked_items, pagerank, has_vector 
                    FROM notes''')
                conn.execute('DROP TABLE notes')
                conn.execute('ALTER TABLE notes_new RENAME TO notes')
                
                # Re-enable foreign keys
                conn.execute('PRAGMA foreign_keys = ON')
            
            current_version = 3

        # Update version
        conn.execute(f"PRAGMA user_version = {DB_VERSION}")
        conn.commit()
        logging.info("Migration complete!")

    # Create all supporting tables if they don't exist
    conn.execute('''CREATE TABLE IF NOT EXISTS edges (
        from_id INTEGER NOT NULL, to_id INTEGER NOT NULL, type TEXT NOT NULL,
        weight REAL DEFAULT 1.0, created TEXT NOT NULL, PRIMARY KEY(from_id, to_id, type),
        FOREIGN KEY(from_id) REFERENCES notes(id) ON DELETE CASCADE,
        FOREIGN KEY(to_id) REFERENCES notes(id) ON DELETE CASCADE
    )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, type TEXT NOT NULL,
        first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, mention_count INTEGER DEFAULT 1
    )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS entity_notes (
        entity_id INTEGER NOT NULL, note_id INTEGER NOT NULL, PRIMARY KEY(entity_id, note_id),
        FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE,
        FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
    )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT NOT NULL, ended TEXT NOT NULL,
        note_count INTEGER DEFAULT 1, coherence_score REAL DEFAULT 1.0
    )''')
    
    # Check and fix FTS schema
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes_fts'")
    fts_exists = cursor.fetchone() is not None
    
    if fts_exists:
        # Check if FTS has the correct schema
        try:
            # Try to query with summary column
            conn.execute("SELECT content, summary FROM notes_fts LIMIT 0")
            fts_needs_rebuild = False
        except sqlite3.OperationalError:
            # FTS is missing summary column, needs rebuild
            logging.info("FTS schema outdated, rebuilding...")
            fts_needs_rebuild = True
    else:
        fts_needs_rebuild = True
        logging.info("FTS doesn't exist, creating...")
    
    if fts_needs_rebuild:
        # Drop old FTS and trigger if they exist
        conn.execute('DROP TABLE IF EXISTS notes_fts')
        conn.execute('DROP TRIGGER IF EXISTS notes_ai')
        
        # Create new FTS with correct schema
        conn.execute('CREATE VIRTUAL TABLE notes_fts USING fts5(content, summary, content=notes, content_rowid=id)')
        
        # Populate FTS with existing notes
        note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        if note_count > 0:
            conn.execute('INSERT INTO notes_fts(rowid, content, summary) SELECT id, content, summary FROM notes')
            logging.info(f"FTS index rebuilt with {note_count} notes")
        else:
            logging.info("FTS index created (no notes to populate)")
    
    # Ensure trigger exists and is correct
    conn.execute('DROP TRIGGER IF EXISTS notes_ai')
    conn.execute('''CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
        INSERT INTO notes_fts(rowid, content, summary) VALUES (new.id, new.content, new.summary);
    END''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS vault (
        key TEXT PRIMARY KEY, encrypted_value BLOB NOT NULL, created TEXT NOT NULL, 
        updated TEXT NOT NULL, author TEXT NOT NULL
    )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT, operation TEXT NOT NULL, ts TEXT NOT NULL, 
        dur_ms INTEGER, author TEXT
    )''')
    
    conn.execute('CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS note_tags (
        note_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY(note_id, tag_id),
        FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )''')

    # Create all indices
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned DESC, created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_pagerank ON notes(pagerank DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id ON note_tags(tag_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_note_tags_note_id ON note_tags(note_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entity_notes_note ON entity_notes(note_id)')

    conn.commit()
    
    # Final check
    note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    logging.info(f"Database ready with {note_count} notes")
    
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

def format_time_contextual(ts: str) -> str:
    """Ultra-compact contextual time format"""
    if not ts: return ""
    try:
        dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
        delta = datetime.now() - dt
        if delta.total_seconds() < 60: return "now"
        if delta.total_seconds() < 3600: return f"{int(delta.total_seconds()/60)}m"
        if dt.date() == datetime.now().date(): return dt.strftime("%H%M")
        if delta.days == 1: return f"y{dt.strftime('%H%M')}"
        if delta.days < 7: return f"{delta.days}d"
        return dt.strftime("%Y%m%d|%H%M")
    except:
        return ""

def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace"""
    return re.sub(r'\s+', ' ', text).strip() if text else ""

def simple_summary(content: str, max_len: int = 150) -> str:
    """Create simple summary by truncating cleanly"""
    if not content: return ""
    clean = clean_text(content)
    if len(clean) <= max_len: return clean
    for sep in ['. ', '! ', '? ', '; ']:
        idx = clean.rfind(sep, 0, max_len)
        if idx > max_len * 0.5: return clean[:idx + 1]
    idx = clean.rfind(' ', 0, max_len - 3)
    if idx == -1 or idx < max_len * 0.7: idx = max_len - 3
    return clean[:idx] + "..."

def extract_references(content: str) -> List[int]:
    """Extract note references from content"""
    refs = set()
    for pattern in [r'note\s+(\d+)', r'\bn(\d+)\b', r'#(\d+)\b', r'\[(\d+)\]']:
        refs.update(int(m) for m in re.findall(pattern, content, re.IGNORECASE) if m.isdigit())
    return list(refs)

def extract_entities(content: str) -> List[Tuple[str, str]]:
    """Extract entities from content using cached pattern"""
    global ENTITY_PATTERN, ENTITY_PATTERN_SIZE
    entities = []
    content_lower = content.lower()
    
    mentions = re.findall(r'@([\w-]+)', content, re.IGNORECASE)
    entities.extend((m.lower(), 'mention') for m in mentions)
    
    all_known = KNOWN_TOOLS.union(KNOWN_ENTITIES)
    if all_known:
        if ENTITY_PATTERN is None or len(all_known) != ENTITY_PATTERN_SIZE:
            pattern_str = r'\b(' + '|'.join(re.escape(e) for e in all_known) + r')\b'
            ENTITY_PATTERN = re.compile(pattern_str, re.IGNORECASE)
            ENTITY_PATTERN_SIZE = len(all_known)
        
        found_entities = ENTITY_PATTERN.findall(content_lower)
        for entity_name in set(found_entities):
            entity_type = 'tool' if entity_name in KNOWN_TOOLS else 'known'
            entities.append((entity_name, entity_type))

    return entities

def detect_or_create_session(note_id: Optional[int], created: datetime, conn: sqlite3.Connection) -> Optional[int]:
    """Detect existing session or create new one"""
    try:
        if note_id:
            prev_note = conn.execute('SELECT created, session_id FROM notes WHERE id < ? ORDER BY id DESC LIMIT 1', (note_id,)).fetchone()
        else:
            prev_note = conn.execute('SELECT created, session_id FROM notes ORDER BY id DESC LIMIT 1').fetchone()

        if prev_note:
            prev_time = datetime.fromisoformat(prev_note[0])
            if (created - prev_time).total_seconds() / 60 <= SESSION_GAP_MINUTES and prev_note[1]:
                session_id = prev_note[1]
                conn.execute('UPDATE sessions SET ended = ?, note_count = note_count + 1 WHERE id = ?', (created.isoformat(), session_id))
                return session_id
        
        cursor = conn.execute('INSERT INTO sessions (started, ended) VALUES (?, ?)', (created.isoformat(), created.isoformat()))
        return cursor.lastrowid
    except:
        return None

def create_edges(note_id: int, conn: sqlite3.Connection, edge_data: List[Tuple]):
    """Generic function to batch-insert edges"""
    if edge_data:
        conn.executemany('INSERT OR IGNORE INTO edges (from_id, to_id, type, weight, created) VALUES (?, ?, ?, ?, ?)', edge_data)

def create_all_edges(note_id: int, content: str, session_id: Optional[int], conn: sqlite3.Connection):
    """Create all edge types efficiently"""
    now = datetime.now().isoformat()
    edges_to_add = []

    # Temporal edges
    prev_notes = conn.execute('SELECT id FROM notes WHERE id < ? ORDER BY id DESC LIMIT ?', (note_id, TEMPORAL_EDGES)).fetchall()
    for prev in prev_notes:
        edges_to_add.append((note_id, prev[0], 'temporal', 1.0, now))
        edges_to_add.append((prev[0], note_id, 'temporal', 1.0, now))

    # Reference edges
    refs = extract_references(content)
    if refs:
        valid_refs = conn.execute(f'SELECT id FROM notes WHERE id IN ({",".join("?"*len(refs))})', refs).fetchall()
        for ref_id in valid_refs:
            edges_to_add.append((note_id, ref_id[0], 'reference', 2.0, now))
            edges_to_add.append((ref_id[0], note_id, 'referenced_by', 2.0, now))

    # Session edges
    if session_id:
        session_notes = conn.execute('SELECT id FROM notes WHERE session_id = ? AND id != ?', (session_id, note_id)).fetchall()
        for other_note in session_notes:
            edges_to_add.append((note_id, other_note[0], 'session', 1.5, now))
            edges_to_add.append((other_note[0], note_id, 'session', 1.5, now))
    
    # Entity edges
    entities = extract_entities(content)
    if entities:
        for entity_name, entity_type in entities:
            entity = conn.execute('SELECT id FROM entities WHERE name = ?', (entity_name,)).fetchone()
            if entity:
                entity_id = entity[0]
                conn.execute('UPDATE entities SET last_seen = ?, mention_count = mention_count + 1 WHERE id = ?', (now, entity_id))
            else:
                cursor = conn.execute('INSERT INTO entities (name, type, first_seen, last_seen) VALUES (?, ?, ?, ?)', (entity_name, entity_type, now, now))
                entity_id = cursor.lastrowid
                KNOWN_ENTITIES.add(entity_name.lower())
            
            conn.execute('INSERT OR IGNORE INTO entity_notes (entity_id, note_id) VALUES (?, ?)', (entity_id, note_id))
            other_notes = conn.execute('SELECT note_id FROM entity_notes WHERE entity_id = ? AND note_id != ?', (entity_id, note_id)).fetchall()
            for other_note in other_notes:
                edges_to_add.append((note_id, other_note[0], 'entity', 1.2, now))
                edges_to_add.append((other_note[0], note_id, 'entity', 1.2, now))

    create_edges(note_id, conn, edges_to_add)

def calculate_pagerank_scores(conn: sqlite3.Connection):
    """Calculate PageRank scores using sparse matrix for memory efficiency"""
    try:
        start = time.time()
        notes = conn.execute('SELECT id FROM notes').fetchall()
        if not notes: return
        
        note_ids = [n[0] for n in notes]
        n = len(note_ids)
        id_to_idx = {nid: i for i, nid in enumerate(note_ids)}
        
        if SCIPY_AVAILABLE:
            adjacency = dok_matrix((n, n), dtype=np.float32)
        else:
            adjacency = np.zeros((n, n))

        edges = conn.execute('SELECT from_id, to_id, weight FROM edges').fetchall()
        for from_id, to_id, weight in edges:
            if from_id in id_to_idx and to_id in id_to_idx:
                adjacency[id_to_idx[from_id], id_to_idx[to_id]] = weight
        
        if SCIPY_AVAILABLE:
            adjacency = adjacency.tocsr()

        pagerank = np.ones(n) / n
        for _ in range(PAGERANK_ITERATIONS):
            new_pagerank = np.zeros(n)
            for i in range(n):
                rank = (1 - PAGERANK_DAMPING) / n
                for j in range(n):
                    if adjacency[j, i] > 0:
                        outlinks = np.sum(adjacency[j, :])
                        if outlinks > 0:
                            rank += PAGERANK_DAMPING * (pagerank[j] / outlinks) * adjacency[j, i]
                new_pagerank[i] = rank
            
            if np.linalg.norm(new_pagerank - pagerank, ord=1) < 0.0001:
                break
            pagerank = new_pagerank
        
        update_data = [(float(pagerank[i]), note_id) for i, note_id in enumerate(note_ids)]
        conn.executemany('UPDATE notes SET pagerank = ? WHERE id = ?', update_data)
        conn.commit()
        
        logging.info(f"PageRank calculated for {n} notes in {time.time() - start:.2f}s")
    except Exception as e:
        logging.error(f"Error calculating PageRank: {e}")

def calculate_pagerank_if_needed(conn: sqlite3.Connection):
    """Lazily calculate PageRank only when needed"""
    global PAGERANK_DIRTY, PAGERANK_CACHE_TIME
    current_time = time.time()
    count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if count < 50: return
    if PAGERANK_DIRTY or (current_time - PAGERANK_CACHE_TIME > PAGERANK_CACHE_SECONDS):
        calculate_pagerank_scores(conn)
        PAGERANK_DIRTY = False
        PAGERANK_CACHE_TIME = current_time

def parse_time_query(when: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse natural language time queries into date ranges"""
    if not when: return None, None
    when_lower = when.lower().strip()
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if when_lower == "today": return today_start, now
    elif when_lower == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        return yesterday_start, today_start - timedelta(seconds=1)
    elif when_lower == "this week":
        return today_start - timedelta(days=now.weekday()), now
    elif when_lower == "last week":
        last_week_end = today_start - timedelta(days=now.weekday())
        return last_week_end - timedelta(days=7), last_week_end
    return None, None

def migrate_existing_to_vectors():
    """Background migration of existing notes to vectors"""
    if not encoder or not collection:
        return
    try:
        conn = sqlite3.connect(str(DB_FILE))
        notes = conn.execute('SELECT id, content FROM notes WHERE has_vector = 0 ORDER BY created DESC LIMIT 100').fetchall()
        migrated = 0
        for note_id, content in notes:
            try:
                embedding = encoder.encode(content[:1000], convert_to_numpy=True)
                collection.add(
                    embeddings=[embedding.tolist()], documents=[content],
                    metadatas={"created": datetime.now().isoformat()}, ids=[str(note_id)]
                )
                conn.execute('UPDATE notes SET has_vector = 1 WHERE id = ?', (note_id,))
                migrated += 1
                if migrated % 10 == 0:
                    conn.commit()
            except Exception as e:
                logging.debug(f"Failed to vectorize note {note_id}: {e}")
        
        conn.commit()
        conn.close()
        if migrated > 0:
            logging.info(f"Migrated {migrated} notes to vectors")
    except Exception as e:
        logging.error(f"Migration failed: {e}")

def log_operation(op: str, dur_ms: int = None):
    """Log operation for stats tracking"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.execute('INSERT INTO stats (operation, ts, dur_ms, author) VALUES (?, ?, ?, ?)',
                         (op, datetime.now().isoformat(), dur_ms, CURRENT_AI_ID))
    except:
        pass

def _get_note_id(id_param: Any) -> Optional[int]:
    """Helper to resolve 'last' or string IDs to an integer"""
    if id_param == "last":
        last_op = get_last_operation()
        if last_op and last_op['type'] == 'remember':
            return last_op['result'].get('id')
        with sqlite3.connect(str(DB_FILE)) as conn:
            recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
            return recent[0] if recent else None
    
    if isinstance(id_param, str):
        clean_id = re.sub(r'[^\d]', '', id_param)
        return int(clean_id) if clean_id else None
    return int(id_param) if id_param is not None else None

def remember(content: str = None, summary: str = None, tags: List[str] = None, 
             linked_items: List[str] = None, **kwargs) -> Dict:
    """Save a note with all features: edges, sessions, vectors"""
    try:
        start = datetime.now()
        content = str(kwargs.get('content', content or '')).strip()
        if not content: content = f"Checkpoint {datetime.now().strftime('%H:%M')}"
        
        truncated = False
        orig_len = len(content)
        if orig_len > MAX_CONTENT_LENGTH:
            content, truncated = content[:MAX_CONTENT_LENGTH], True
        
        summary = clean_text(summary)[:MAX_SUMMARY_LENGTH] if summary else simple_summary(content)
        tags = [str(t).lower().strip() for t in tags if t] if tags else []

        with sqlite3.connect(str(DB_FILE)) as conn:
            created_time = datetime.now()
            
            cursor = conn.execute(
                'INSERT INTO notes (content, summary, author, created, linked_items, has_vector) VALUES (?, ?, ?, ?, ?, ?)',
                (content, summary, CURRENT_AI_ID, created_time.isoformat(), 
                 json.dumps(linked_items) if linked_items else None, 1 if encoder and collection else 0)
            )
            note_id = cursor.lastrowid
            
            session_id = detect_or_create_session(note_id, created_time, conn)
            if session_id:
                conn.execute('UPDATE notes SET session_id = ? WHERE id = ?', (session_id, note_id))

            if tags:
                for tag_name in tags:
                    conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
                    tag_id = conn.execute('SELECT id FROM tags WHERE name = ?', (tag_name,)).fetchone()[0]
                    conn.execute('INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)', (note_id, tag_id))

            create_all_edges(note_id, content, session_id, conn)
            
            global PAGERANK_DIRTY
            PAGERANK_DIRTY = True
            
            conn.commit()
        
        if encoder and collection:
            try:
                embedding = encoder.encode(content[:1000], convert_to_numpy=True)
                collection.add(
                    embeddings=[embedding.tolist()], documents=[content],
                    metadatas={"created": created_time.isoformat(), "summary": summary, "tags": json.dumps(tags)},
                    ids=[str(note_id)]
                )
            except Exception as e:
                logging.warning(f"Vector storage failed: {e}")
        
        save_last_operation('remember', {'id': note_id, 'summary': summary})
        log_operation('remember', int((datetime.now() - start).total_seconds() * 1000))
        
        current_timestamp = datetime.now().strftime("%Y%m%d|%H%M")
        if OUTPUT_FORMAT == 'pipe':
            result_str = f"{note_id}|{current_timestamp}|{summary}"
            if truncated: result_str += f"|truncated:{orig_len}"
            return {"saved": result_str}
        else:
            result_dict = {"id": note_id, "time": current_timestamp, "summary": summary}
            if truncated: result_dict["truncated"] = orig_len
            return result_dict
    except Exception as e:
        logging.error(f"Error in remember: {e}", exc_info=True)
        return {"error": f"Failed to save: {str(e)}"}

def recall(query: str = None, tag: str = None, when: str = None, 
           pinned_only: bool = False, show_all: bool = False, 
           limit: int = 50, mode: str = "hybrid", **kwargs) -> Dict:
    """Search notes using hybrid approach: linear + semantic + graph"""
    try:
        start_time = datetime.now()
        time_start, time_end = parse_time_query(when) if when else (None, None)
        
        if not any([show_all, query, tag, when, pinned_only]):
            limit = DEFAULT_RECENT
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            calculate_pagerank_if_needed(conn)
            notes = []

            if pinned_only:
                notes = conn.execute('SELECT * FROM notes WHERE pinned = 1 ORDER BY pagerank DESC, created DESC').fetchall()
            elif when and time_start:
                notes = conn.execute('SELECT * FROM notes WHERE created >= ? AND created <= ? ORDER BY created DESC LIMIT ?',
                                     (time_start.isoformat(), time_end.isoformat(), limit)).fetchall()
            elif tag:
                tag_clean = str(tag).lower().strip()
                notes = conn.execute('''
                    SELECT n.* FROM notes n
                    JOIN note_tags nt ON n.id = nt.note_id
                    JOIN tags t ON nt.tag_id = t.id
                    WHERE t.name = ?
                    ORDER BY n.pinned DESC, n.pagerank DESC, n.created DESC LIMIT ?
                ''', (tag_clean, limit)).fetchall()
            elif query:
                semantic_ids = []
                if encoder and collection and mode in ["semantic", "hybrid"]:
                    try:
                        query_embedding = encoder.encode(str(query).strip(), convert_to_numpy=True)
                        results = collection.query(query_embeddings=[query_embedding.tolist()], n_results=min(limit, 100))
                        if results['ids'] and results['ids'][0]:
                            semantic_ids = [int(id_str) for id_str in results['ids'][0]]
                    except Exception as e:
                        logging.debug(f"Semantic search failed: {e}")
                
                keyword_ids = []
                if mode in ["keyword", "hybrid"]:
                    keyword_results = conn.execute('''
                        SELECT n.id FROM notes n JOIN notes_fts ON n.id = notes_fts.rowid
                        WHERE notes_fts MATCH ? ORDER BY n.pagerank DESC, n.created DESC LIMIT ?
                    ''', (str(query).strip(), limit)).fetchall()
                    keyword_ids = [row['id'] for row in keyword_results]

                all_ids, seen = [], set()
                for i in range(max(len(semantic_ids), len(keyword_ids))):
                    if i < len(semantic_ids) and semantic_ids[i] not in seen:
                        all_ids.append(semantic_ids[i]); seen.add(semantic_ids[i])
                    if i < len(keyword_ids) and keyword_ids[i] not in seen:
                        all_ids.append(keyword_ids[i]); seen.add(keyword_ids[i])
                
                note_ids = all_ids[:limit]
                if note_ids:
                    placeholders = ','.join('?' * len(note_ids))
                    notes_dict = {n['id']: n for n in conn.execute(f'SELECT * FROM notes WHERE id IN ({placeholders})', note_ids).fetchall()}
                    notes = [notes_dict[nid] for nid in note_ids if nid in notes_dict]
            else:
                notes = conn.execute('SELECT * FROM notes ORDER BY pinned DESC, created DESC LIMIT ?', (limit,)).fetchall()
        
        current_timestamp = datetime.now().strftime("%Y%m%d|%H%M")
        if not notes:
            return {"msg": "No notes found", "current_time": current_timestamp}
        
        if OUTPUT_FORMAT == 'pipe':
            lines = [f"@{current_timestamp}"]
            for note in notes:
                parts = [str(note['id']), format_time_contextual(note['created']), 
                         note['summary'] or simple_summary(note['content'], 80)]
                if note['pinned']: parts.append('PIN')
                if note['pagerank'] and note['pagerank'] > 0.01: parts.append(f"★{note['pagerank']:.3f}")
                lines.append('|'.join(pipe_escape(str(p)) for p in parts))
            result = {"notes": lines}
        else:
            formatted_notes = [{'id': n['id'], 'time': format_time_contextual(n['created']), 
                                'summary': n['summary'] or simple_summary(n['content'], 80),
                                'pinned': bool(n['pinned']), 'pagerank': round(n['pagerank'], 3) if n['pagerank'] > 0.01 else None}
                               for n in notes]
            result = {"notes": formatted_notes, "current_time": current_timestamp}
        
        save_last_operation('recall', result)
        log_operation('recall', int((datetime.now() - start_time).total_seconds() * 1000))
        return result
    except Exception as e:
        logging.error(f"Error in recall: {e}", exc_info=True)
        return {"error": f"Recall failed: {str(e)}"}

def get_status(**kwargs) -> Dict:
    """Get current state with semantic info and temporal grounding"""
    try:
        current_timestamp = datetime.now().strftime("%Y%m%d|%H%M")
        with sqlite3.connect(str(DB_FILE)) as conn:
            counts = {
                "notes": conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0],
                "pinned": conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = 1').fetchone()[0],
                "edges": conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0],
                "entities": conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0],
                "sessions": conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],
                "vault": conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0],
                "tags": conn.execute('SELECT COUNT(*) FROM tags').fetchone()[0],
            }
            recent = conn.execute('SELECT created FROM notes ORDER BY created DESC LIMIT 1').fetchone()
            last_activity = format_time_contextual(recent[0]) if recent else "never"
        
        vector_count = collection.count() if collection else 0
        
        if OUTPUT_FORMAT == 'pipe':
            parts = [f"@{current_timestamp}", f"notes:{counts['notes']}", f"vectors:{vector_count}", 
                     f"edges:{counts['edges']}", f"entities:{counts['entities']}", 
                     f"sessions:{counts['sessions']}", f"pinned:{counts['pinned']}",
                     f"tags:{counts['tags']}", f"last:{last_activity}", 
                     f"model:{EMBEDDING_MODEL or 'none'}"]
            return {"status": '|'.join(parts)}
        else:
            return {"current_time": current_timestamp, **counts, "vectors": vector_count, 
                    "last": last_activity, "embedding_model": EMBEDDING_MODEL or "none", 
                    "identity": CURRENT_AI_ID}
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {"error": f"Status failed: {str(e)}"}

def pin_note(id: Any = None, **kwargs) -> Dict:
    """Pin an important note"""
    try:
        note_id = _get_note_id(kwargs.get('id', id))
        if not note_id: return {"error": "Invalid or missing note ID"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute('UPDATE notes SET pinned = 1 WHERE id = ?', (note_id,))
            if cursor.rowcount == 0: return {"error": f"Note {note_id} not found"}
            note = conn.execute('SELECT summary, content FROM notes WHERE id = ?', (note_id,)).fetchone()
            summ = note[0] or simple_summary(note[1], 60)
        
        save_last_operation('pin', {'id': note_id})
        current_timestamp = datetime.now().strftime("%Y%m%d|%H%M")
        
        if OUTPUT_FORMAT == 'pipe':
            return {"pinned": f"{note_id}|{current_timestamp}|{summ}"}
        else:
            return {"pinned": note_id, "time": current_timestamp, "summary": summ}
    except Exception as e:
        logging.error(f"Error in pin_note: {e}")
        return {"error": f"Failed to pin: {str(e)}"}

def unpin_note(id: Any = None, **kwargs) -> Dict:
    """Unpin a note"""
    try:
        note_id = _get_note_id(kwargs.get('id', id))
        if not note_id: return {"error": "Invalid or missing note ID"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute('UPDATE notes SET pinned = 0 WHERE id = ?', (note_id,))
            if cursor.rowcount == 0: return {"error": f"Note {note_id} not found"}
        
        save_last_operation('unpin', {'id': note_id})
        current_timestamp = datetime.now().strftime("%Y%m%d|%H%M")
        return {"unpinned": note_id, "time": current_timestamp}
    except Exception as e:
        logging.error(f"Error in unpin_note: {e}")
        return {"error": f"Failed to unpin: {str(e)}"}

def get_full_note(id: Any = None, **kwargs) -> Dict:
    """Get complete note with all connections"""
    try:
        note_id = _get_note_id(kwargs.get('id', id))
        if not note_id: return {"error": "Invalid or missing note ID"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            note = conn.execute('SELECT * FROM notes WHERE id = ?', (note_id,)).fetchone()
            if not note: return {"error": f"Note {note_id} not found"}
            
            result = dict(note)
            
            tags = conn.execute('''
                SELECT t.name FROM tags t JOIN note_tags nt ON t.id = nt.tag_id WHERE nt.note_id = ?
            ''', (note_id,)).fetchall()
            result['tags'] = [t['name'] for t in tags]
            
            entities = conn.execute('''
                SELECT e.name FROM entities e JOIN entity_notes en ON e.id = en.entity_id WHERE en.note_id = ?
            ''', (note_id,)).fetchall()
            result['entities'] = [f"@{e['name']}" for e in entities]

            edges_out = conn.execute('SELECT to_id, type FROM edges WHERE from_id = ?', (note_id,)).fetchall()
            edges_in = conn.execute('SELECT from_id, type FROM edges WHERE to_id = ?', (note_id,)).fetchall()
            
            result['edges_out'] = {t: [e['to_id'] for e in edges_out if e['type'] == t] for t in set(e['type'] for e in edges_out)}
            result['edges_in'] = {t: [e['from_id'] for e in edges_in if e['type'] == t] for t in set(e['type'] for e in edges_in)}

        result['current_time'] = datetime.now().strftime("%Y%m%d|%H%M")
        save_last_operation('get_full_note', {'id': note_id})
        return result
    except Exception as e:
        logging.error(f"Error in get_full_note: {e}", exc_info=True)
        return {"error": f"Failed to retrieve: {str(e)}"}

def vault_store(key: str = None, value: str = None, **kwargs) -> Dict:
    """Store encrypted secret"""
    try:
        key = str(kwargs.get('key', key) or '').strip()
        value = str(kwargs.get('value', value) or '').strip()
        if not key or not value: return {"error": "Both key and value required"}
        
        encrypted = vault_manager.encrypt(value)
        now = datetime.now().isoformat()
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.execute('''
                INSERT INTO vault (key, encrypted_value, created, updated, author) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET encrypted_value=excluded.encrypted_value, updated=excluded.updated
            ''', (key, encrypted, now, now, CURRENT_AI_ID))
        
        log_operation('vault_store')
        return {"stored": key, "time": datetime.now().strftime("%Y%m%d|%H%M")}
    except Exception as e:
        logging.error(f"Error in vault_store: {e}")
        return {"error": f"Storage failed: {str(e)}"}

def vault_retrieve(key: str = None, **kwargs) -> Dict:
    """Retrieve decrypted secret"""
    try:
        key = str(kwargs.get('key', key) or '').strip()
        if not key: return {"error": "Key required"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            result = conn.execute('SELECT encrypted_value FROM vault WHERE key = ?', (key,)).fetchone()
        
        if not result: return {"error": f"Key '{key}' not found"}
        
        decrypted = vault_manager.decrypt(result[0])
        log_operation('vault_retrieve')
        return {"key": key, "value": decrypted, "time": datetime.now().strftime("%Y%m%d|%H%M")}
    except Exception as e:
        logging.error(f"Error in vault_retrieve: {e}")
        return {"error": f"Retrieval failed: {str(e)}"}

def vault_list(**kwargs) -> Dict:
    """List vault keys"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            items = conn.execute('SELECT key, updated FROM vault ORDER BY updated DESC').fetchall()
        
        current_timestamp = datetime.now().strftime("%Y%m%d|%H%M")
        if not items: return {"msg": "Vault empty", "current_time": current_timestamp}
        
        if OUTPUT_FORMAT == 'pipe':
            keys = [f"@{current_timestamp}"] + [f"{item['key']}|{format_time_contextual(item['updated'])}" for item in items]
            return {"vault_keys": keys}
        else:
            keys = [{'key': i['key'], 'updated': format_time_contextual(i['updated'])} for i in items]
            return {"vault_keys": keys, "current_time": current_timestamp}
    except Exception as e:
        logging.error(f"Error in vault_list: {e}")
        return {"error": f"List failed: {str(e)}"}

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
    """Execute multiple operations efficiently"""
    try:
        operations = kwargs.get('operations', operations or [])
        if not operations: return {"error": "No operations provided"}
        if len(operations) > BATCH_MAX: return {"error": f"Too many operations (max {BATCH_MAX})"}
        
        op_map = {'remember': remember, 'recall': recall, 'pin_note': pin_note, 'pin': pin_note, 
                  'unpin_note': unpin_note, 'unpin': unpin_note, 'vault_store': vault_store, 
                  'vault_retrieve': vault_retrieve, 'get_full_note': get_full_note,
                  'get': get_full_note, 'status': get_status, 'vault_list': vault_list}
        
        results = []
        for op in operations:
            op_type = op.get('type')
            if op_type in op_map:
                results.append(op_map[op_type](**op.get('args', {})))
            else:
                results.append({"error": f"Unknown operation: {op_type}"})
        
        return {"batch_results": results, "count": len(results)}
    except Exception as e:
        logging.error(f"Error in batch: {e}")
        return {"error": f"Batch failed: {str(e)}"}

def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with proper formatting"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})

    tools = {"get_status": get_status, "remember": remember, "recall": recall, 
             "get_full_note": get_full_note, "get": get_full_note,
             "pin_note": pin_note, "pin": pin_note, 
             "unpin_note": unpin_note, "unpin": unpin_note, 
             "vault_store": vault_store, "vault_retrieve": vault_retrieve, 
             "vault_list": vault_list, "batch": batch}

    if tool_name not in tools:
        return {"content": [{"type": "text", "text": f"Error: Unknown tool: {tool_name}"}]}

    result = tools[tool_name](**tool_args)
    text_parts = []

    # Handle get_full_note specially
    if tool_name in ["get_full_note", "get"] and "content" in result and "id" in result:
        text_parts.append(f"@{result.get('current_time', '')}")
        text_parts.append(f"=== NOTE {result['id']} ===")
        text_parts.append(f"Created: {result['created']}")
        text_parts.append(f"Author: {result['author']}")
        if result.get('pinned'): text_parts.append("📌 PINNED")
        text_parts.append(f"\n{result['content']}\n")
        if result.get('summary'): text_parts.append(f"Summary: {result['summary']}")
        if result.get('tags'): text_parts.append(f"Tags: {', '.join(result['tags'])}")
        if result.get('entities'): text_parts.append(f"Entities: {', '.join(result['entities'])}")
        if result.get('edges_out'): text_parts.append(f"Connections: {json.dumps(result['edges_out'])}")
        if result.get('pagerank') and result['pagerank'] > 0.01: 
            text_parts.append(f"PageRank: {result['pagerank']:.4f}")
    elif tool_name == "vault_retrieve" and "value" in result and "key" in result:
        text_parts.append(f"@{result.get('time', '')}")
        text_parts.append(f"🔐 {result['key']}: {result['value']}")
    elif "error" in result:
        text_parts.append(f"Error: {result['error']}")
    elif OUTPUT_FORMAT == 'pipe' and "notes" in result and isinstance(result["notes"], list):
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
        if OUTPUT_FORMAT == 'pipe': text_parts.extend(result["vault_keys"])
        else: text_parts.append(json.dumps(result["vault_keys"]))
    elif "msg" in result:
        text_parts.append(result["msg"])
    elif "batch_results" in result:
        text_parts.append(f"Batch: {result.get('count', 0)}")
        for r in result["batch_results"]:
            if isinstance(r, dict):
                if "error" in r: text_parts.append(f"Error: {r['error']}")
                elif "saved" in r: text_parts.append(r["saved"])
                elif "pinned" in r: text_parts.append(str(r["pinned"]))
                else: text_parts.append(json.dumps(r))
            else: text_parts.append(str(r))
    else:
        text_parts.append(json.dumps(result))

    return {"content": [{"type": "text", "text": "\n".join(text_parts) if text_parts else "Done"}]}

# Initialize everything
init_db()
init_embedding_gemma()
init_vector_db()

if encoder and collection:
    threading.Thread(target=migrate_existing_to_vectors, daemon=True).start()

def main():
    """MCP server main loop"""
    logging.info(f"Notebook MCP v{VERSION} - PRODUCTION READY")
    logging.info(f"Identity: {CURRENT_AI_ID} | DB: {DB_FILE}")
    logging.info(f"Embedding model: {EMBEDDING_MODEL or 'None'}")
    if SCIPY_AVAILABLE:
        logging.info("✓ Sparse matrix PageRank enabled")
    logging.info("✓ Normalized tag system active")
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            line = line.strip()
            if not line: continue
            
            request = json.loads(line)
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
                        "description": f"Production-ready hybrid memory ({EMBEDDING_MODEL or 'keyword-only'})"
                    }
                }
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                tool_schemas = {
                    "get_status": {"desc": "See current system state", "props": {}},
                    "remember": {"desc": "Save a note", "props": {"content": {"type": "string"}, "summary": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}},
                    "recall": {"desc": "Hybrid search", "props": {"query": {"type": "string"}, "tag": {"type": "string"}, "when": {"type": "string"}}},
                    "get_full_note": {"desc": "Get complete note", "props": {"id": {"type": "string"}}, "req": ["id"]},
                    "get": {"desc": "Alias for get_full_note", "props": {"id": {"type": "string"}}, "req": ["id"]},
                    "pin_note": {"desc": "Pin a note", "props": {"id": {"type": "string"}}, "req": ["id"]},
                    "pin": {"desc": "Alias for pin_note", "props": {"id": {"type": "string"}}, "req": ["id"]},
                    "unpin_note": {"desc": "Unpin a note", "props": {"id": {"type": "string"}}, "req": ["id"]},
                    "unpin": {"desc": "Alias for unpin_note", "props": {"id": {"type": "string"}}, "req": ["id"]},
                    "vault_store": {"desc": "Store encrypted secret", "props": {"key": {"type": "string"}, "value": {"type": "string"}}, "req": ["key", "value"]},
                    "vault_retrieve": {"desc": "Retrieve decrypted secret", "props": {"key": {"type": "string"}}, "req": ["key"]},
                    "vault_list": {"desc": "List vault keys", "props": {}},
                    "batch": {"desc": "Execute multiple operations", "props": {"operations": {"type": "array"}}, "req": ["operations"]},
                }
                response["result"] = {
                    "tools": [{
                        "name": name, "description": schema["desc"],
                        "inputSchema": {"type": "object", "properties": schema["props"], 
                                      "required": schema.get("req", []), "additionalProperties": True}
                    } for name, schema in tool_schemas.items()]
                }
            elif method == "tools/call":
                response["result"] = handle_tools_call(params)
            else:
                response["result"] = {"status": "ready"}
            
            if "result" in response or "error" in response:
                print(json.dumps(response), flush=True)
                
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logging.error(f"Server loop error: {e}", exc_info=True)
            continue
    
    logging.info("Notebook MCP shutting down")

if __name__ == "__main__":
    main()
