#!/usr/bin/env python3
"""
TEAMBOOK STORAGE MCP v7.0.0 - DATA PERSISTENCE LAYER
=====================================================
All database operations, vector storage, and persistence for teambook.
This layer handles DuckDB, ChromaDB, vault encryption, and PageRank calculations.

Built by AIs, for AIs.
=====================================================
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Any
from pathlib import Path
from cryptography.fernet import Fernet

# Database engine
try:
    import duckdb
except ImportError:
    print("FATAL: DuckDB not installed. Please run 'pip install duckdb'", file=sys.stderr)
    sys.exit(1)

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

import numpy as np

# Import shared utilities
from teambook_shared import (
    get_db_file, get_vector_dir, get_vault_key_file,
    KNOWN_ENTITIES, CURRENT_AI_ID, CURRENT_TEAMBOOK,
    TEMPORAL_EDGES, SESSION_GAP_MINUTES, PAGERANK_ITERATIONS,
    PAGERANK_DAMPING, USE_SEMANTIC, extract_references,
    extract_entities, logging
)



# ============= GLOBAL STORAGE STATE =============
encoder = None
chroma_client = None
collection = None
vault_manager = None
EMBEDDING_MODEL = None
FTS_ENABLED = False

# ============= VAULT MANAGER =============
class VaultManager:
    """Secure encrypted storage for secrets"""
    def __init__(self):
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key) if self.key else None
    
    def _load_or_create_key(self) -> bytes:
        vault_file = get_vault_key_file()
        if vault_file.exists():
            with open(vault_file, 'rb') as f:
                return f.read()
        
        key = Fernet.generate_key()
        with open(vault_file, 'wb') as f:
            f.write(key)
        
        try:
            import stat
            os.chmod(vault_file, stat.S_IRUSR | stat.S_IWUSR)
        except:
            pass
        
        return key
    
    def encrypt(self, value: str) -> bytes:
        if not self.fernet:
            self.key = self._load_or_create_key()
            self.fernet = Fernet(self.key)
        return self.fernet.encrypt(value.encode())
    
    def decrypt(self, encrypted: bytes) -> str:
        if not self.fernet:
            self.key = self._load_or_create_key()
            self.fernet = Fernet(self.key)
        return self.fernet.decrypt(encrypted).decode()

# ============= DATABASE CONNECTION =============
def get_db_conn() -> duckdb.DuckDBPyConnection:
    """Returns a new connection to the DuckDB database"""
    db_path = str(get_db_file())
    try:
        return duckdb.connect(database=db_path, read_only=False)
    except duckdb.IOException as e:
        if "being used by another process" in str(e):
            logging.warning(f"Database locked, waiting 0.5s...")
            time.sleep(0.5)
            try:
                return duckdb.connect(database=db_path, read_only=False)
            except:
                temp_db = db_path.replace('.duckdb', f'_temp_{int(time.time())}.duckdb')
                logging.warning(f"Creating temporary database: {temp_db}")
                return duckdb.connect(database=temp_db, read_only=False)
        else:
            raise

# ============= DATABASE SCHEMA =============
def create_duckdb_schema(conn: duckdb.DuckDBPyConnection):
    """Create all tables and indices for DuckDB"""
    
    conn.execute("CREATE SEQUENCE IF NOT EXISTS notes_id_seq START 1")
    
    # Main notes table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id BIGINT PRIMARY KEY,
            content TEXT,
            summary TEXT,
            tags VARCHAR[],
            pinned BOOLEAN DEFAULT FALSE,
            author VARCHAR NOT NULL,
            owner VARCHAR,
            teambook_name VARCHAR,
            type VARCHAR,
            parent_id BIGINT,
            created TIMESTAMPTZ NOT NULL,
            session_id BIGINT,
            linked_items TEXT,
            pagerank DOUBLE DEFAULT 0.0,
            has_vector BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Edges table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            from_id BIGINT NOT NULL,
            to_id BIGINT NOT NULL,
            type VARCHAR NOT NULL,
            weight DOUBLE DEFAULT 1.0,
            created TIMESTAMPTZ NOT NULL,
            PRIMARY KEY(from_id, to_id, type)
        )
    ''')
    
    # Evolution outputs table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS evolution_outputs (
            id BIGINT PRIMARY KEY,
            evolution_id BIGINT NOT NULL,
            output_path TEXT NOT NULL,
            created TIMESTAMPTZ NOT NULL,
            author VARCHAR NOT NULL
        )
    ''')
    
    # Teambooks registry
    conn.execute('''
        CREATE TABLE IF NOT EXISTS teambooks (
            name VARCHAR PRIMARY KEY,
            created TIMESTAMPTZ NOT NULL,
            created_by VARCHAR NOT NULL,
            last_active TIMESTAMPTZ
        )
    ''')
    
    # Other tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id BIGINT PRIMARY KEY,
            name VARCHAR UNIQUE NOT NULL,
            type VARCHAR NOT NULL,
            first_seen TIMESTAMPTZ NOT NULL,
            last_seen TIMESTAMPTZ NOT NULL,
            mention_count INTEGER DEFAULT 1
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entity_notes (
            entity_id BIGINT NOT NULL,
            note_id BIGINT NOT NULL,
            PRIMARY KEY(entity_id, note_id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id BIGINT PRIMARY KEY,
            started TIMESTAMPTZ NOT NULL,
            ended TIMESTAMPTZ NOT NULL,
            note_count INTEGER DEFAULT 1,
            coherence_score DOUBLE DEFAULT 1.0
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS vault (
            key VARCHAR PRIMARY KEY,
            encrypted_value BLOB NOT NULL,
            created TIMESTAMPTZ NOT NULL,
            updated TIMESTAMPTZ NOT NULL,
            author VARCHAR NOT NULL
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id BIGINT PRIMARY KEY,
            operation VARCHAR NOT NULL,
            ts TIMESTAMPTZ NOT NULL,
            dur_ms INTEGER,
            author VARCHAR
        )
    ''')
    
    # Create indices
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created DESC)",
        "CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned DESC, created DESC)",
        "CREATE INDEX IF NOT EXISTS idx_notes_pagerank ON notes(pagerank DESC)",
        "CREATE INDEX IF NOT EXISTS idx_notes_owner ON notes(owner)",
        "CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(type)",
        "CREATE INDEX IF NOT EXISTS idx_notes_parent ON notes(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)"
    ]
    
    for idx in indices:
        conn.execute(idx)
    
    # Try to set up FTS with correct DuckDB syntax
    global FTS_ENABLED
    FTS_ENABLED = False
    
    try:
        conn.execute("INSTALL fts")
        conn.execute("LOAD fts")
        # Create FTS index - this creates a virtual table fts_main_notes
        conn.execute("PRAGMA create_fts_index('notes', 'id', 'content', 'summary')")
        # Test that it works
        conn.execute("SELECT COUNT(*) FROM fts_main_notes WHERE fts_main_notes MATCH 'test'").fetchone()
        FTS_ENABLED = True
        logging.info("DuckDB FTS extension loaded and configured")
    except Exception as e1:
        if "already exists" in str(e1):
            # FTS index already exists, just test if it works
            try:
                conn.execute("LOAD fts")
                # Test FTS works
                conn.execute("SELECT COUNT(*) FROM fts_main_notes WHERE fts_main_notes MATCH 'test'").fetchone()
                FTS_ENABLED = True
                logging.info("DuckDB FTS already configured")
            except Exception as e2:
                logging.warning(f"FTS index exists but not working: {e2}")
        else:
            # FTS not available for other reasons
            logging.info(f"FTS not available, will use LIKE queries (this is fine): {str(e1)[:100]}")

def init_db():
    """Initialize DuckDB database"""
    with get_db_conn() as conn:
        tables = conn.execute("SHOW TABLES").fetchall()
        if not any(t[0] == 'notes' for t in tables):
            logging.info("Creating new database schema...")
            create_duckdb_schema(conn)
        else:
            # Check for missing columns and add them
            cursor = conn.execute("PRAGMA table_info(notes)")
            columns = [col[1] for col in cursor.fetchall()]
            
            migrations = [
                ('owner', 'ALTER TABLE notes ADD COLUMN owner VARCHAR'),
                ('teambook_name', 'ALTER TABLE notes ADD COLUMN teambook_name VARCHAR'),
                ('type', 'ALTER TABLE notes ADD COLUMN type VARCHAR'),
                ('parent_id', 'ALTER TABLE notes ADD COLUMN parent_id BIGINT')
            ]
            
            for col_name, sql in migrations:
                if col_name not in columns:
                    logging.info(f"Adding {col_name} column...")
                    conn.execute(sql)
            
            # Ensure all tables exist
            if not any(t[0] == 'evolution_outputs' for t in tables):
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS evolution_outputs (
                        id BIGINT PRIMARY KEY,
                        evolution_id BIGINT NOT NULL,
                        output_path TEXT NOT NULL,
                        created TIMESTAMPTZ NOT NULL,
                        author VARCHAR NOT NULL
                    )
                ''')
            
            if not any(t[0] == 'teambooks' for t in tables):
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS teambooks (
                        name VARCHAR PRIMARY KEY,
                        created TIMESTAMPTZ NOT NULL,
                        created_by VARCHAR NOT NULL,
                        last_active TIMESTAMPTZ
                    )
                ''')
            
            # Try to initialize FTS again if not enabled
            global FTS_ENABLED
            if not FTS_ENABLED:
                try:
                    conn.execute("LOAD fts")
                    # Test if FTS works
                    conn.execute("SELECT COUNT(*) FROM fts_main_notes WHERE fts_main_notes MATCH 'test'").fetchone()
                    FTS_ENABLED = True
                    logging.info("FTS enabled on existing database")
                except Exception as e:
                    # Try to create the index if it doesn't exist
                    try:
                        conn.execute("INSTALL fts")
                        conn.execute("LOAD fts")
                        conn.execute("PRAGMA create_fts_index('notes', 'id', 'content', 'summary')")
                        # Test FTS works
                        conn.execute("SELECT COUNT(*) FROM fts_main_notes WHERE fts_main_notes MATCH 'test'").fetchone()
                        FTS_ENABLED = True
                        logging.info("FTS index created and enabled")
                    except:
                        # FTS not available, that's OK
                        pass
        
        load_known_entities(conn)
        
        note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        logging.info(f"Database ready with {note_count} notes")

def load_known_entities(conn: duckdb.DuckDBPyConnection):
    """Load known entities into memory cache"""
    global KNOWN_ENTITIES
    try:
        entities = conn.execute('SELECT name FROM entities').fetchall()
        KNOWN_ENTITIES.clear()
        KNOWN_ENTITIES.update(e[0].lower() for e in entities)
    except:
        pass

# ============= EMBEDDING AND VECTOR DB =============
def init_embedding_model():
    """Initialize embedding model with automatic local model detection"""
    global encoder, EMBEDDING_MODEL
    
    if not ST_AVAILABLE or not USE_SEMANTIC:
        logging.info("Semantic search disabled")
        return None
    
    # First, try to find local models
    search_paths = [
        Path.cwd() / "models",  # Current dir
        Path.cwd().parent / "models",  # Parent dir  
        Path(__file__).parent / "models" if '__file__' in globals() else None,  # Script location
    ]
    
    for path in search_paths:
        if not path or not path.exists():
            continue
            
        # Look for EmbeddingGemma specifically
        embeddinggemma_path = path / "embeddinggemma-300m"
        if embeddinggemma_path.exists():
            # Check if it has the required files
            required = ["config.json", "model.safetensors", "tokenizer.json"]
            if all((embeddinggemma_path / f).exists() for f in required):
                try:
                    logging.info(f"Loading EmbeddingGemma 300m from {embeddinggemma_path}...")
                    encoder = SentenceTransformer(str(embeddinggemma_path), device='cpu')
                    test = encoder.encode("test", convert_to_numpy=True)
                    EMBEDDING_MODEL = 'embeddinggemma-300m'
                    logging.info(f"✅ Using local EmbeddingGemma 300m (dim: {test.shape[0]})")
                    return encoder
                except Exception as e:
                    logging.warning(f"Failed to load EmbeddingGemma: {e}")
    
    # Fallback to downloading models
    logging.info("No local models found, downloading online models...")
    
    try:
        models = [
            ('sentence-transformers/all-MiniLM-L6-v2', 'minilm'),
            ('BAAI/bge-base-en-v1.5', 'bge-base'),
        ]
        
        for model_name, short_name in models:
            try:
                logging.info(f"Loading {model_name}...")
                encoder = SentenceTransformer(model_name, device='cpu')
                test = encoder.encode("test", convert_to_numpy=True)
                EMBEDDING_MODEL = short_name
                logging.info(f"✓ Using {short_name} (dim: {test.shape[0]})")
                return encoder
            except Exception as e:
                logging.debug(f"Failed to load {model_name}: {e}")
        
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
        vector_dir = get_vector_dir()
        vector_dir.mkdir(parents=True, exist_ok=True)
        
        chroma_client = chromadb.PersistentClient(
            path=str(vector_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        collection_name = f"teambook_{CURRENT_TEAMBOOK}_v7" if CURRENT_TEAMBOOK else "teambook_private_v7"
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logging.info(f"ChromaDB initialized with {collection.count()} vectors for {collection_name}")
        return True
    except Exception as e:
        logging.error(f"ChromaDB init failed: {e}")
        return False

def init_vault_manager():
    """Initialize or reinitialize vault manager for current teambook"""
    global vault_manager
    vault_manager = VaultManager()

# ============= SESSION MANAGEMENT =============
def detect_or_create_session(note_id: int, created: datetime, conn: duckdb.DuckDBPyConnection) -> Optional[int]:
    """Detect existing session or create new one"""
    try:
        prev = conn.execute(
            'SELECT created, session_id FROM notes WHERE id < ? ORDER BY id DESC LIMIT 1',
            [note_id]
        ).fetchone()
        
        if prev:
            prev_time = prev[0] if isinstance(prev[0], datetime) else datetime.fromisoformat(prev[0])
            if (created - prev_time).total_seconds() / 60 <= SESSION_GAP_MINUTES and prev[1]:
                conn.execute(
                    'UPDATE sessions SET ended = ?, note_count = note_count + 1 WHERE id = ?',
                    [created, prev[1]]
                )
                return prev[1]
        
        max_session_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM sessions").fetchone()[0]
        new_session_id = max_session_id + 1
        
        conn.execute(
            'INSERT INTO sessions (id, started, ended) VALUES (?, ?, ?)',
            [new_session_id, created, created]
        )
        return new_session_id
    except:
        return None

# ============= EDGE CREATION =============
def create_all_edges(note_id: int, content: str, session_id: Optional[int], conn: duckdb.DuckDBPyConnection):
    """Create all edge types efficiently"""
    now = datetime.now(timezone.utc)
    edges_to_add = []
    
    # Temporal edges
    prev_notes = conn.execute(
        'SELECT id FROM notes WHERE id < ? ORDER BY id DESC LIMIT ?',
        [note_id, TEMPORAL_EDGES]
    ).fetchall()
    
    for prev in prev_notes:
        edges_to_add.extend([
            (note_id, prev[0], 'temporal', 1.0, now),
            (prev[0], note_id, 'temporal', 1.0, now)
        ])
    
    # Reference edges
    refs = extract_references(content)
    if refs:
        placeholders = ','.join(['?'] * len(refs))
        valid_refs = conn.execute(
            f'SELECT id FROM notes WHERE id IN ({placeholders})',
            refs
        ).fetchall()
        
        for ref_id in valid_refs:
            edges_to_add.extend([
                (note_id, ref_id[0], 'reference', 2.0, now),
                (ref_id[0], note_id, 'referenced_by', 2.0, now)
            ])
    
    # Session edges
    if session_id:
        session_notes = conn.execute(
            'SELECT id FROM notes WHERE session_id = ? AND id != ?',
            [session_id, note_id]
        ).fetchall()
        
        for other in session_notes:
            edges_to_add.extend([
                (note_id, other[0], 'session', 1.5, now),
                (other[0], note_id, 'session', 1.5, now)
            ])
    
    # Entity edges
    entities = extract_entities(content)
    for entity_name, entity_type in entities:
        entity = conn.execute(
            'SELECT id FROM entities WHERE name = ?',
            [entity_name]
        ).fetchone()
        
        if entity:
            entity_id = entity[0]
            conn.execute(
                'UPDATE entities SET last_seen = ?, mention_count = mention_count + 1 WHERE id = ?',
                [now, entity_id]
            )
        else:
            max_entity_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM entities").fetchone()[0]
            entity_id = max_entity_id + 1
            
            conn.execute(
                'INSERT INTO entities (id, name, type, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)',
                [entity_id, entity_name, entity_type, now, now]
            )
            
            if entity_id:
                KNOWN_ENTITIES.add(entity_name.lower())
        
        if entity_id:
            conn.execute(
                'INSERT INTO entity_notes (entity_id, note_id) VALUES (?, ?) ON CONFLICT DO NOTHING',
                [entity_id, note_id]
            )
            
            other_notes = conn.execute(
                'SELECT note_id FROM entity_notes WHERE entity_id = ? AND note_id != ?',
                [entity_id, note_id]
            ).fetchall()
            
            for other in other_notes:
                edges_to_add.extend([
                    (note_id, other[0], 'entity', 1.2, now),
                    (other[0], note_id, 'entity', 1.2, now)
                ])
    
    # Batch insert edges
    for edge in edges_to_add:
        conn.execute(
            'INSERT INTO edges (from_id, to_id, type, weight, created) VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING',
            edge
        )

# ============= PAGERANK CALCULATION =============
def calculate_pagerank_duckdb(conn: duckdb.DuckDBPyConnection):
    """Calculate PageRank using DuckDB's native SQL"""
    try:
        start = time.time()
        
        conn.execute(f'''
            CREATE OR REPLACE TEMPORARY TABLE pagerank_scores AS
            WITH RECURSIVE
            nodes AS (
                SELECT DISTINCT id FROM notes
            ),
            node_count AS (
                SELECT COUNT(*)::DOUBLE as total FROM nodes
            ),
            outlinks AS (
                SELECT from_id, SUM(weight) as total_weight
                FROM edges
                GROUP BY from_id
            ),
            pagerank(iteration, id, rank) AS (
                SELECT 0, id, 1.0 / node_count.total
                FROM nodes, node_count
                
                UNION ALL
                
                SELECT 
                    pr.iteration + 1,
                    n.id,
                    (1 - {PAGERANK_DAMPING}) / nc.total + 
                    {PAGERANK_DAMPING} * COALESCE(SUM(pr.rank * e.weight / ol.total_weight), 0)
                FROM nodes n
                CROSS JOIN node_count nc
                LEFT JOIN edges e ON e.to_id = n.id
                LEFT JOIN pagerank pr ON pr.id = e.from_id AND pr.iteration < {PAGERANK_ITERATIONS}
                LEFT JOIN outlinks ol ON ol.from_id = e.from_id
                WHERE pr.iteration < {PAGERANK_ITERATIONS}
                GROUP BY pr.iteration, n.id, nc.total
            )
            SELECT id, rank 
            FROM pagerank 
            WHERE iteration = {PAGERANK_ITERATIONS}
        ''')
        
        conn.execute('''
            UPDATE notes 
            SET pagerank = pr.rank
            FROM pagerank_scores pr
            WHERE notes.id = pr.id
        ''')
        
        elapsed = time.time() - start
        note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        logging.info(f"PageRank calculated for {note_count} notes in {elapsed:.2f}s")
        
    except Exception as e:
        logging.error(f"DuckDB PageRank failed, using fallback: {e}")
        conn.execute('''
            UPDATE notes 
            SET pagerank = COALESCE((
                SELECT COUNT(*) * 0.01 
                FROM edges 
                WHERE edges.to_id = notes.id
            ), 0.01)
        ''')

def calculate_pagerank_if_needed(conn: duckdb.DuckDBPyConnection):
    """Calculate PageRank when needed"""
    from teambook_shared import PAGERANK_DIRTY, PAGERANK_CACHE_TIME, PAGERANK_CACHE_SECONDS
    
    count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if count < 50:
        return
    
    current_time = time.time()
    if PAGERANK_DIRTY or (current_time - PAGERANK_CACHE_TIME > PAGERANK_CACHE_SECONDS):
        calculate_pagerank_duckdb(conn)
        # Update shared state
        import teambook_shared
        teambook_shared.PAGERANK_DIRTY = False
        teambook_shared.PAGERANK_CACHE_TIME = current_time

# ============= STATS TRACKING =============
def log_operation_to_db(op: str, dur_ms: int = None):
    """Log operation to database"""
    try:
        with get_db_conn() as conn:
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM stats").fetchone()[0]
            conn.execute(
                'INSERT INTO stats (id, operation, ts, dur_ms, author) VALUES (?, ?, ?, ?, ?)',
                [max_id + 1, op, datetime.now(timezone.utc), dur_ms, CURRENT_AI_ID]
            )
    except:
        pass

# ============= NOTE ID RESOLUTION =============
def resolve_note_id(id_param: Any) -> Optional[int]:
    """Resolve note ID including database lookup for 'last'"""
    from teambook_shared import get_note_id, get_last_operation
    
    if id_param == "last":
        last_op = get_last_operation()
        if last_op and last_op['type'] in ['remember', 'write']:
            return last_op['result'].get('id')
        
        # Database lookup for most recent
        with get_db_conn() as conn:
            recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
            return recent[0] if recent else None
    
    return get_note_id(id_param)

# ============= VECTOR OPERATIONS =============
def add_to_vector_store(note_id: int, content: str, summary: str, tags: List[str]):
    """Add a note to the vector store"""
    if not encoder or not collection:
        return False
    
    try:
        embedding = encoder.encode(content[:1000], convert_to_numpy=True)
        collection.add(
            embeddings=[embedding.tolist()],
            documents=[content],
            metadatas={
                "created": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "tags": json.dumps(tags)
            },
            ids=[str(note_id)]
        )
        return True
    except Exception as e:
        logging.warning(f"Vector storage failed: {e}")
        return False

def search_vectors(query: str, limit: int = 100) -> List[int]:
    """Search vector store for similar content"""
    if not encoder or not collection:
        return []
    
    try:
        query_embedding = encoder.encode(query, convert_to_numpy=True)
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=min(limit, 100)
        )
        if results['ids'] and results['ids'][0]:
            return [int(id_str) for id_str in results['ids'][0]]
    except Exception as e:
        logging.debug(f"Vector search failed: {e}")
    
    return []


