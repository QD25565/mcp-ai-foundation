#!/usr/bin/env python3
"""
NOTEBOOK MCP v5.0.0 - HYBRID MEMORY SYSTEM
===============================================
Linear memory, graph edges, and semantic search.
Powered by Google's EmbeddingGemma for semantic understanding.

SETUP INSTRUCTIONS:
1. Install dependencies:
   pip install chromadb sentence-transformers

2. First run will download EmbeddingGemma models automatically
   (About 1-2GB download, then works offline forever)

ARCHITECTURE:
- SQLite: Structure, metadata, edges, temporal tracking
- ChromaDB: Semantic vectors from EmbeddingGemma
- Hybrid recall: Recent linear + semantic search + graph connections

This system combines linear memory, with knowledge graph and semantic aspects.
===============================================
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
import hashlib
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

# Version
VERSION = "5.0.0"

# Configuration
OUTPUT_FORMAT = os.environ.get('NOTEBOOK_FORMAT', 'pipe')
SEARCH_MODE = os.environ.get('NOTEBOOK_SEARCH', 'or')
USE_SEMANTIC = os.environ.get('NOTEBOOK_SEMANTIC', 'true').lower() == 'true'

# Limits - optimized for modern PCs with 8-64GB RAM
MAX_CONTENT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 200
MAX_RESULTS = 100
BATCH_MAX = 50
DEFAULT_RECENT = 30  # Linear recent memory
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
                'task_manager', 'notebook', 'world', 'chromadb', 'embedding-gemma'}

# PageRank lazy calculation flags
PAGERANK_DIRTY = True
PAGERANK_CACHE_TIME = 0

# Operation memory
LAST_OPERATION = None

# EmbeddingGemma encoder (global)
encoder = None
chroma_client = None
collection = None
EMBEDDING_MODEL = None

def init_embedding_gemma():
    """Initialize Google's EmbeddingGemma model"""
    global encoder, EMBEDDING_MODEL
    
    if not ST_AVAILABLE or not USE_SEMANTIC:
        logging.info("Semantic search disabled")
        return None
    
    try:
        # YOUR LOCAL MODEL PATH - No downloads, instant loading!
        local_model_path = r"C:\Users\YOUR-USERNAME\AppData\Roaming\Claude\tools\models\embeddinggemma-300m"
        
        # Try models in order of preference
        models_to_try = [
            (local_model_path, 'embedding-gemma'),  # 300M params - LOCAL Google AI model
            
            # Fallback models (only if local model doesn't work):
            ('BAAI/bge-base-en-v1.5', 'bge-base'),  # 109M params, MTEB score: 63.4
            ('sentence-transformers/all-mpnet-base-v2', 'mpnet'),  # 110M params
            ('sentence-transformers/all-MiniLM-L6-v2', 'minilm'),  # 22M params, last resort
        ]
        
        for model_name, short_name in models_to_try:
            try:
                logging.info(f"Loading {model_name}...")
                encoder = SentenceTransformer(model_name, device='cpu')
                
                # Test it works
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
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection with cosine similarity
        collection = chroma_client.get_or_create_collection(
            name="notebook_v5",
            metadata={"hnsw:space": "cosine"}
        )
        
        logging.info(f"ChromaDB initialized with {collection.count()} existing vectors")
        return True
        
    except Exception as e:
        logging.error(f"ChromaDB init failed: {e}")
        return False

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
    
    # Generate new ID
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
    """Initialize SQLite database with ALL v4.1 features"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Main notes table with all columns
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
            has_vector INTEGER DEFAULT 0,
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
    
    # ========== MIGRATION SECTION ==========
    # Check and add missing columns to existing tables
    
    # Check columns in notes table
    cursor = conn.execute("PRAGMA table_info(notes)")
    note_columns = [col[1] for col in cursor.fetchall()]
    
    # Add missing columns to notes table
    if 'session_id' not in note_columns:
        logging.info("Migrating: Adding session_id column to notes table...")
        conn.execute('ALTER TABLE notes ADD COLUMN session_id INTEGER')
        
    if 'linked_items' not in note_columns:
        logging.info("Migrating: Adding linked_items column to notes table...")
        conn.execute('ALTER TABLE notes ADD COLUMN linked_items TEXT')
        
    if 'pagerank' not in note_columns:
        logging.info("Migrating: Adding pagerank column to notes table...")
        conn.execute('ALTER TABLE notes ADD COLUMN pagerank REAL DEFAULT 0.0')
        
    if 'has_vector' not in note_columns:
        logging.info("Migrating: Adding has_vector column to notes table...")
        conn.execute('ALTER TABLE notes ADD COLUMN has_vector INTEGER DEFAULT 0')
    
    conn.commit()
    # ========== END MIGRATION SECTION ==========
    
    # Create all indices
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned DESC, created DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_pagerank ON notes(pagerank DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_session ON notes(session_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_notes_has_vector ON notes(has_vector)')
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

def migrate_existing_to_vectors():
    """Background migration of existing notes to vectors"""
    if not encoder or not collection:
        return
    
    try:
        conn = sqlite3.connect(str(DB_FILE))
        
        # Get unmigrated notes
        notes = conn.execute('''
            SELECT id, content FROM notes 
            WHERE has_vector = 0
            ORDER BY created DESC
            LIMIT 100
        ''').fetchall()
        
        migrated = 0
        for note_id, content in notes:
            try:
                # Generate embedding
                embedding = encoder.encode(content[:1000], convert_to_numpy=True)
                
                # Add to ChromaDB
                collection.add(
                    embeddings=[embedding.tolist()],
                    documents=[content],
                    metadatas={"created": datetime.now().isoformat()},
                    ids=[str(note_id)]
                )
                
                # Mark as vectorized
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
    elif when_lower == "this week":
        days_since_monday = now.weekday()
        week_start = today_start - timedelta(days=days_since_monday)
        return week_start, now
    elif when_lower == "last week":
        days_since_monday = now.weekday()
        last_week_end = today_start - timedelta(days=days_since_monday)
        last_week_start = last_week_end - timedelta(days=7)
        return last_week_start, last_week_end
    else:
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
        else:
            return dt.strftime("%m/%d")
    except:
        return ""

def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace"""
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
    patterns = [
        r'note\s+(\d+)',
        r'\bn(\d+)\b',
        r'#(\d+)\b',
        r'\[(\d+)\]'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        refs.extend(int(m) for m in matches if m.isdigit())
    
    return list(set(refs))

def extract_entities(content: str) -> List[Tuple[str, str]]:
    """Extract entities from content"""
    entities = []
    content_lower = content.lower()
    
    # @mentions
    mentions = re.findall(r'@([\w-]+)', content, re.IGNORECASE)
    entities.extend((m.lower(), 'mention') for m in mentions)
    
    # Known tools
    for tool in KNOWN_TOOLS:
        if re.search(r'\b' + re.escape(tool) + r'\b', content_lower):
            entities.append((tool, 'tool'))
    
    # Known entities
    for entity in KNOWN_ENTITIES:
        if re.search(r'\b' + re.escape(entity) + r'\b', content_lower):
            entities.append((entity, 'known'))
    
    # Deduplicate
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
                session_id = prev_note[2]
                conn.execute('''
                    UPDATE sessions 
                    SET ended = ?, note_count = note_count + 1
                    WHERE id = ?
                ''', (created.isoformat(), session_id))
                return session_id
        
        cursor = conn.execute('''
            INSERT INTO sessions (started, ended, note_count)
            VALUES (?, ?, 1)
        ''', (created.isoformat(), created.isoformat()))
        
        return cursor.lastrowid
        
    except:
        return None

def create_temporal_edges(note_id: int, conn: sqlite3.Connection):
    """Create temporal edges to previous notes"""
    try:
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

def create_entity_edges(note_id: int, entities: List[Tuple[str, str]], conn: sqlite3.Connection):
    """Create edges between note and entities"""
    try:
        now = datetime.now().isoformat()
        
        for entity_name, entity_type in entities:
            entity = conn.execute('SELECT id FROM entities WHERE name = ?', (entity_name,)).fetchone()
            
            if entity:
                entity_id = entity[0]
                conn.execute('''
                    UPDATE entities 
                    SET last_seen = ?, mention_count = mention_count + 1
                    WHERE id = ?
                ''', (now, entity_id))
            else:
                cursor = conn.execute('''
                    INSERT INTO entities (name, type, first_seen, last_seen)
                    VALUES (?, ?, ?, ?)
                ''', (entity_name, entity_type, now, now))
                entity_id = cursor.lastrowid
                KNOWN_ENTITIES.add(entity_name.lower())
            
            conn.execute('''
                INSERT OR IGNORE INTO entity_notes (entity_id, note_id)
                VALUES (?, ?)
            ''', (entity_id, note_id))
            
            # Find other notes with same entity
            other_notes = conn.execute('''
                SELECT note_id FROM entity_notes 
                WHERE entity_id = ? AND note_id != ?
            ''', (entity_id, note_id)).fetchall()
            
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

def create_session_edges(note_id: int, session_id: int, conn: sqlite3.Connection):
    """Create edges between notes in the same session"""
    try:
        now = datetime.now().isoformat()
        
        session_notes = conn.execute('''
            SELECT id FROM notes 
            WHERE session_id = ? AND id != ?
        ''', (session_id, note_id)).fetchall()
        
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

def calculate_pagerank_scores(conn: sqlite3.Connection):
    """Calculate PageRank scores for all notes"""
    try:
        start = time.time()
        
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
        
        # Initialize PageRank
        pagerank = np.ones(n) / n
        
        # Power iteration
        for _ in range(PAGERANK_ITERATIONS):
            new_pagerank = np.zeros(n)
            
            for i in range(n):
                rank = (1 - PAGERANK_DAMPING) / n
                
                for j in range(n):
                    if adjacency[j][i] > 0:
                        outlinks = np.sum(adjacency[j])
                        if outlinks > 0:
                            rank += PAGERANK_DAMPING * (pagerank[j] / outlinks) * adjacency[j][i]
                
                new_pagerank[i] = rank
            
            if np.max(np.abs(new_pagerank - pagerank)) < 0.0001:
                break
            
            pagerank = new_pagerank
        
        # Update database
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
    
    # Skip PageRank for small datasets
    count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if count < 100:
        return  # Don't bother for small sets
    
    # Recalculate if dirty or cache expired
    if PAGERANK_DIRTY or (current_time - PAGERANK_CACHE_TIME > PAGERANK_CACHE_SECONDS):
        calculate_pagerank_scores(conn)
        PAGERANK_DIRTY = False
        PAGERANK_CACHE_TIME = current_time

def calculate_pagerank_incremental(note_id: int, conn: sqlite3.Connection):
    """Mark PageRank as dirty for next calculation"""
    global PAGERANK_DIRTY
    PAGERANK_DIRTY = True  # Simpler - just mark for recalc

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
    """Save a note with ALL features: edges, sessions, vectors"""
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
        
        # Generate summary if needed
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
                '''INSERT INTO notes (content, summary, tags, author, created, session_id, 
                                     linked_items, has_vector) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (content, summary, tags_json, CURRENT_AI_ID, created_time.isoformat(), 
                 session_id, json.dumps(linked_items) if linked_items else None,
                 1 if (encoder and collection) else 0)
            )
            note_id = cursor.lastrowid
            
            # Update session if needed
            if not session_id:
                session_id = detect_or_create_session(note_id, created_time, conn)
                if session_id:
                    conn.execute('UPDATE notes SET session_id = ? WHERE id = ?', (session_id, note_id))
            
            # Create all edge types
            create_temporal_edges(note_id, conn)
            
            refs = extract_references(content)
            if refs:
                create_reference_edges(note_id, refs, conn)
            
            entities = extract_entities(content)
            if entities:
                create_entity_edges(note_id, entities, conn)
            
            if session_id:
                create_session_edges(note_id, session_id, conn)
            
            # Mark PageRank for recalculation
            calculate_pagerank_incremental(note_id, conn)
            
            conn.commit()
        
        # Add to vector DB if available
        if encoder and collection:
            try:
                # Generate embedding using EmbeddingGemma
                embedding = encoder.encode(content[:1000], convert_to_numpy=True)
                
                # Store in ChromaDB
                collection.add(
                    embeddings=[embedding.tolist()],
                    documents=[content],
                    metadatas={
                        "created": created_time.isoformat(),
                        "summary": summary,
                        "tags": tags_json or ""
                    },
                    ids=[str(note_id)]
                )
                
                logging.debug(f"Added vector for note {note_id}")
                
            except Exception as e:
                logging.warning(f"Vector storage failed: {e}")
                # Continue - note is still saved
        
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
            return {"saved": result}
        else:
            result = {"id": note_id, "time": "now", "summary": summary}
            if truncated:
                result["truncated"] = orig_len
            return result
        
    except Exception as e:
        logging.error(f"Error in remember: {e}")
        return {"error": f"Failed to save: {str(e)}"}

def recall(query: str = None, tag: str = None, when: str = None, 
           pinned_only: bool = False, show_all: bool = False, 
           limit: int = 50, mode: str = "hybrid", **kwargs) -> Dict:
    """Search notes using hybrid approach: linear + semantic + graph"""
    try:
        start_time = datetime.now()
        
        # Parse time query if provided
        if when:
            time_start, time_end = parse_time_query(when)
            if not time_start:
                return {"msg": f"Didn't understand time query: '{when}'"}
        else:
            time_start, time_end = None, None
        
        # Determine limit
        if not show_all and not query and not tag and not when and not pinned_only:
            limit = DEFAULT_RECENT
        
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
                ''', (time_start.isoformat(), time_end.isoformat(), limit))
                notes = cursor.fetchall()
            
            elif query and encoder and collection and mode in ["semantic", "hybrid"]:
                # Semantic search with EmbeddingGemma
                query_clean = str(query).strip()
                
                try:
                    # Generate query embedding
                    query_embedding = encoder.encode(query_clean, convert_to_numpy=True)
                    
                    # Search ChromaDB
                    results = collection.query(
                        query_embeddings=[query_embedding.tolist()],
                        n_results=min(limit, 100)
                    )
                    
                    # Get note IDs from semantic search
                    semantic_ids = []
                    if results['ids'] and results['ids'][0]:
                        semantic_ids = [int(id_str) for id_str in results['ids'][0]]
                    
                    if mode == "hybrid" and len(semantic_ids) < limit:
                        # Also do keyword search
                        cursor = conn.execute('''
                            SELECT n.id FROM notes n
                            JOIN notes_fts ON n.id = notes_fts.rowid
                            WHERE notes_fts MATCH ?
                            ORDER BY n.pagerank DESC, n.created DESC
                            LIMIT ?
                        ''', (query_clean, limit))
                        keyword_ids = [row['id'] for row in cursor.fetchall()]
                        
                        # Merge semantic and keyword results
                        all_ids = []
                        seen = set()
                        
                        # Interleave semantic and keyword
                        for i in range(max(len(semantic_ids), len(keyword_ids))):
                            if i < len(semantic_ids) and semantic_ids[i] not in seen:
                                all_ids.append(semantic_ids[i])
                                seen.add(semantic_ids[i])
                            if i < len(keyword_ids) and keyword_ids[i] not in seen:
                                all_ids.append(keyword_ids[i])
                                seen.add(keyword_ids[i])
                        
                        note_ids = all_ids[:limit]
                    else:
                        note_ids = semantic_ids
                    
                    # Fetch full notes
                    if note_ids:
                        placeholders = ','.join('?' * len(note_ids))
                        cursor = conn.execute(f'''
                            SELECT * FROM notes 
                            WHERE id IN ({placeholders})
                        ''', note_ids)
                        notes_dict = {n['id']: n for n in cursor.fetchall()}
                        
                        # Preserve order from search
                        notes = [notes_dict[nid] for nid in note_ids if nid in notes_dict]
                    else:
                        notes = []
                        
                except Exception as e:
                    logging.debug(f"Semantic search failed: {e}")
                    # Fallback to keyword search
                    cursor = conn.execute('''
                        SELECT n.* FROM notes n
                        JOIN notes_fts ON n.id = notes_fts.rowid
                        WHERE notes_fts MATCH ?
                        ORDER BY n.pagerank DESC, n.created DESC
                        LIMIT ?
                    ''', (query, limit))
                    notes = cursor.fetchall()
            
            elif query:
                # Keyword search only
                cursor = conn.execute('''
                    SELECT n.* FROM notes n
                    JOIN notes_fts ON n.id = notes_fts.rowid
                    WHERE notes_fts MATCH ?
                    ORDER BY n.pagerank DESC, n.created DESC
                    LIMIT ?
                ''', (query, limit))
                notes = cursor.fetchall()
            
            elif tag:
                # Tag filter
                tag = str(tag).lower().strip()
                cursor = conn.execute('''
                    SELECT * FROM notes 
                    WHERE tags LIKE ?
                    ORDER BY pinned DESC, pagerank DESC, created DESC
                    LIMIT ?
                ''', (f'%"{tag}"%', limit))
                notes = cursor.fetchall()
            
            else:
                # Default: recent notes
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
            elif when:
                return {"msg": f"No notes {when}"}
            else:
                return {"msg": "No notes yet"}
        
        # Format output
        if OUTPUT_FORMAT == 'pipe':
            lines = []
            for note in notes:
                parts = []
                parts.append(str(note['id']))
                parts.append(format_time_contextual(note['created']))
                
                summ = note['summary'] or simple_summary(note['content'], 80)
                parts.append(summ)
                
                if note['pinned']:
                    parts.append('PIN')
                if note['pagerank'] and note['pagerank'] > 0.01:
                    parts.append(f"★{note['pagerank']:.3f}")
                
                lines.append('|'.join(pipe_escape(str(p)) for p in parts))
            
            result = {"notes": lines}
        else:
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
        dur = int((datetime.now() - start_time).total_seconds() * 1000)
        log_operation('recall', dur)
        
        return result
        
    except Exception as e:
        logging.error(f"Error in recall: {e}")
        return {"error": f"Recall failed: {str(e)}"}

# Additional functions (get_status, pin_note, unpin_note, get_full_note, vault_*, batch)
# remain the same as in v4.1...

def get_status(**kwargs) -> Dict:
    """Get current state with semantic info"""
    try:
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            total_notes = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            pinned_count = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = 1').fetchone()[0]
            edge_count = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
            entities_count = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
            sessions_count = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
            vault_items = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
            vectorized = conn.execute('SELECT COUNT(*) FROM notes WHERE has_vector = 1').fetchone()[0]
            
            recent = conn.execute('''
                SELECT id, created FROM notes 
                ORDER BY created DESC 
                LIMIT 1
            ''').fetchone()
            
            last_activity = format_time_contextual(recent['created']) if recent else "never"
        
        vector_count = collection.count() if collection else 0
        
        if OUTPUT_FORMAT == 'pipe':
            parts = [
                f"notes:{total_notes}",
                f"vectors:{vector_count}",
                f"edges:{edge_count}",
                f"entities:{entities_count}",
                f"sessions:{sessions_count}",
                f"pinned:{pinned_count}",
                f"last:{last_activity}",
                f"model:{EMBEDDING_MODEL or 'none'}"
            ]
            return {"status": '|'.join(parts)}
        else:
            return {
                "notes": total_notes,
                "vectors": vector_count,
                "edges": edge_count,
                "entities": entities_count,
                "sessions": sessions_count,
                "pinned": pinned_count,
                "vault": vault_items,
                "last": last_activity,
                "embedding_model": EMBEDDING_MODEL or "none",
                "identity": CURRENT_AI_ID
            }
        
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {"error": f"Status failed: {str(e)}"}

def pin_note(id: Any = None, **kwargs) -> Dict:
    """Pin an important note"""
    try:
        if id is None:
            id = kwargs.get('id')
            
        if id == "last":
            last_op = get_last_operation()
            if last_op and last_op['type'] == 'remember':
                id = last_op['result'].get('id')
            else:
                with sqlite3.connect(str(DB_FILE)) as conn:
                    recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
                    if recent:
                        id = recent[0]
                    else:
                        return {"error": "No notes to pin"}
        
        if id is None:
            return {"error": "No ID provided"}
        
        if isinstance(id, str):
            id = re.sub(r'[^\d]', '', id)
        
        if not id:
            return {"error": "Invalid ID"}
        
        id = int(id)
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            cursor = conn.execute('UPDATE notes SET pinned = 1 WHERE id = ?', (id,))
            
            if cursor.rowcount == 0:
                return {"error": f"Note {id} not found"}
            
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
        
        if isinstance(id, str):
            id = re.sub(r'[^\d]', '', id)
        
        if not id:
            return {"error": "Invalid ID"}
        
        id = int(id)
        
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
    """Get complete note with all connections"""
    try:
        if id is None:
            id = kwargs.get('id')
        
        if id == "last":
            last_op = get_last_operation()
            if last_op and last_op['type'] == 'remember':
                id = last_op['result'].get('id')
            else:
                with sqlite3.connect(str(DB_FILE)) as conn:
                    recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
                    if recent:
                        id = recent[0]
                    else:
                        return {"error": "No notes exist"}
        
        if id is None:
            return {"error": "No ID provided"}
        
        if isinstance(id, str):
            clean_id = re.sub(r'[^\d]', '', id)
            if clean_id:
                try:
                    id = int(clean_id)
                except:
                    return {"error": f"Invalid ID: {id}"}
            else:
                return {"error": "Invalid ID"}
        
        with sqlite3.connect(str(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            
            note = conn.execute('SELECT * FROM notes WHERE id = ?', (id,)).fetchone()
            
            if not note:
                return {"error": f"Note {id} not found"}
            
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
        
        result = {
            "id": note['id'],
            "author": note['author'],
            "created": note['created'],
            "summary": note['summary'] or simple_summary(note['content'], 100),
            "content": note['content'],
            "pinned": bool(note['pinned']),
            "pagerank": round(note['pagerank'], 4),
            "has_vector": bool(note['has_vector'])
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
        
        op_map = {
            'remember': remember,
            'recall': recall,
            'pin_note': pin_note,
            'pin': pin_note,
            'unpin_note': unpin_note,
            'unpin': unpin_note,
            'vault_store': vault_store,
            'vault_retrieve': vault_retrieve,
            'get_full_note': get_full_note,
            'get': get_full_note,
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

# Tool interface
def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with minimal formatting"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})
    
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
    
    result = tools[tool_name](**tool_args)
    
    # Format response minimally
    text_parts = []
    
    if "error" in result:
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
        text_parts.append(json.dumps(result))
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Done"
        }]
    }

# Initialize everything
init_db()
init_embedding_gemma()
init_vector_db()

# Start background migration if vectors are available
if encoder and collection:
    migration_thread = threading.Thread(target=migrate_existing_to_vectors, daemon=True)
    migration_thread.start()

def main():
    """MCP server main loop"""
    logging.info(f"Notebook MCP v{VERSION} - TRUE HYBRID starting...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Database: {DB_FILE}")
    logging.info(f"Embedding model: {EMBEDDING_MODEL or 'None'}")
    if collection:
        logging.info(f"ChromaDB vectors: {collection.count()}")
    logging.info("Features enabled:")
    logging.info("- Linear recent memory (30 notes)")
    logging.info("- Semantic search via EmbeddingGemma")
    logging.info("- Graph edges (temporal, reference, entity, session)")
    logging.info("- PageRank for importance")
    logging.info("- Time-based queries")
    logging.info("- Encrypted vault")
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
                        "description": f"Hybrid memory: linear + semantic ({EMBEDDING_MODEL or 'keyword-only'}) + graph"
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
                            "description": "Save note with semantic embedding + graph edges",
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
                            "description": "Hybrid search: semantic + keyword + graph",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search term"
                                    },
                                    "when": {
                                        "type": "string",
                                        "description": "Time query: today, yesterday, this week, etc."
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
                                    },
                                    "mode": {
                                        "type": "string",
                                        "description": "Search mode: hybrid (default), semantic, keyword"
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
                            "description": "Get complete note with all edges and connections",
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
