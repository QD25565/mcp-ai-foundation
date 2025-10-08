#!/usr/bin/env python3
"""
NOTEBOOK MCP v1.0.0 - STORAGE MODULE
=====================================
Database operations, vector storage, and persistence for the Notebook MCP tool.
Handles DuckDB, ChromaDB, and all data interactions.

v1.0.0 - First Public Release:
- Separated storage logic from main application
- Enhanced with directory tracking integration
- Fixed pinned_only query bug
=====================================
"""

import json
import sys
import os
import shutil
import time
import sqlite3
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging
from cryptography.fernet import Fernet

# Try to import compression utilities for storage optimization
try:
    from compression_utils import compress_content, decompress_content
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False
    compress_content = lambda x: x.encode('utf-8') if isinstance(x, str) else x
    decompress_content = lambda x: x.decode('utf-8') if isinstance(x, bytes) else x

# Suppress noisy third-party library logs
logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
logging.getLogger('chromadb').setLevel(logging.WARNING)

# Fix import path for src/ structure
sys.path.insert(0, str(Path(__file__).parent))

# Import shared utilities
from notebook_shared import *

# Database Engine
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

# Module-level storage state
encoder = None
chroma_client = None
collection = None
EMBEDDING_MODEL = None
FTS_ENABLED = False
_embeddings_initialized = False  # Track lazy initialization
_logged_once = set()  # Track one-time log messages to reduce noise

class VaultManager:
    """Secure encrypted storage for secrets"""
    def __init__(self):
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)
    
    def _load_or_create_key(self) -> bytes:
        # Security: Validate vault file path to prevent path traversal
        vault_file = VAULT_KEY_FILE
        try:
            vault_file_resolved = vault_file.resolve()
            if '..' in str(vault_file) or '~' in str(vault_file):
                raise ValueError("Invalid vault file path")
        except Exception as e:
            logging.error(f"Vault path validation failed: {e}")
            raise

        # Security: Fix race condition with atomic file operations
        try:
            # Try to open existing file first (atomic)
            with open(vault_file, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            # File doesn't exist, create it atomically
            key = Fernet.generate_key()

            # Use os.open with exclusive creation to prevent race condition
            import stat
            try:
                fd = os.open(vault_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, stat.S_IRUSR | stat.S_IWUSR)
                try:
                    os.write(fd, key)
                finally:
                    os.close(fd)
            except FileExistsError:
                # Another process created it, read it
                with open(vault_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logging.error(f"Failed to create secure vault file: {e}")
                # Clean up on failure
                if os.path.exists(vault_file):
                    try:
                        os.remove(vault_file)
                    except:
                        pass
                raise

            return key
    
    def encrypt(self, value: str) -> bytes:
        return self.fernet.encrypt(value.encode())
    
    def decrypt(self, encrypted: bytes) -> str:
        return self.fernet.decrypt(encrypted).decode()

vault_manager = VaultManager()

def _get_db_conn() -> duckdb.DuckDBPyConnection:
    """Returns a pooled connection to the DuckDB database (CLI and MCP compatible)"""
    # Try to use connection pooling if available
    try:
        from performance_utils import get_pooled_connection
        return get_pooled_connection(str(DB_FILE))
    except ImportError:
        # Fallback to direct connection if performance_utils not available
        return duckdb.connect(database=str(DB_FILE), read_only=False)

def _migrate_simple_table(sqlite_conn, duck_conn, table_name: str):
    """Helper to migrate a simple table from SQLite to DuckDB"""
    try:
        rows = sqlite_conn.execute(f"SELECT * FROM {table_name}").fetchall()
        if rows:
            placeholders = ','.join(['?'] * len(rows[0]))
            duck_conn.executemany(
                f"INSERT INTO {table_name} VALUES ({placeholders})",
                rows
            )
    except Exception as e:
        logging.warning(f"Could not migrate {table_name}: {e}")

def _create_duckdb_schema(conn: duckdb.DuckDBPyConnection):
    """Create all tables and indices for DuckDB"""
    
    conn.execute("CREATE SEQUENCE IF NOT EXISTS notes_id_seq START 1")
    
    # Main notes table with native array for tags
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id BIGINT PRIMARY KEY,
            content TEXT,
            summary TEXT,
            tags VARCHAR[],
            pinned BOOLEAN DEFAULT FALSE,
            author VARCHAR NOT NULL,
            created TIMESTAMPTZ NOT NULL,
            session_id BIGINT,
            linked_items TEXT,
            pagerank DOUBLE DEFAULT 0.0,
            has_vector BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Directory tracking table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS directory_access (
            id BIGINT PRIMARY KEY,
            path TEXT NOT NULL,
            accessed TIMESTAMPTZ NOT NULL,
            note_id BIGINT,
            operation VARCHAR
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned DESC, created DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_pagerank ON notes(pagerank DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dir_access_time ON directory_access(accessed DESC)")
    
    # Try to set up FTS
    global FTS_ENABLED
    try:
        # DuckDB FTS needs proper installation
        conn.execute("INSTALL fts")
        conn.execute("LOAD fts")
        # Create FTS index for notes table
        try:
            conn.execute("PRAGMA create_fts_index('notes', 'id', 'content', 'summary')")
            FTS_ENABLED = True
            logging.info("DuckDB FTS extension loaded and index created")
        except:
            # Alternative: create a simple FTS table if pragma fails
            conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts 
                           USING fts(content, summary, content=notes, content_rowid=id)""")
            FTS_ENABLED = True
            logging.info("DuckDB FTS table created")
    except Exception as e:
        FTS_ENABLED = False
        logging.warning(f"FTS not available: {e}")

def migrate_from_sqlite():
    """Migrate from SQLite to DuckDB if needed"""
    if DB_FILE.exists() or not SQLITE_DB_FILE.exists():
        return False
    
    logging.info("Migrating from SQLite to DuckDB...")
    
    try:
        import sqlite3
        sqlite_conn = sqlite3.connect(str(SQLITE_DB_FILE))
        sqlite_conn.row_factory = sqlite3.Row
        
        with _get_db_conn() as duck_conn:
            _create_duckdb_schema(duck_conn)
            
            note_count = sqlite_conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            logging.info(f"Migrating {note_count} notes...")
            
            duck_conn.execute("BEGIN TRANSACTION")
            
            try:
                # Migrate notes with tags
                notes = sqlite_conn.execute("SELECT * FROM notes").fetchall()
                for note in notes:
                    # Get tags for this note
                    try:
                        tags = sqlite_conn.execute('''
                            SELECT t.name FROM tags t 
                            JOIN note_tags nt ON t.id = nt.tag_id 
                            WHERE nt.note_id = ?
                        ''', (note['id'],)).fetchall()
                        tag_list = [t['name'] for t in tags] if tags else []
                    except sqlite3.OperationalError:
                        tag_list = []
                        if 'tags' in note.keys():
                            tags_data = note['tags']
                            if tags_data:
                                try:
                                    tag_list = json.loads(tags_data) if isinstance(tags_data, str) else []
                                except: 
                                    pass
                    
                    duck_conn.execute('''
                        INSERT INTO notes (
                            id, content, summary, tags, pinned, author,
                            created, session_id, linked_items, pagerank, has_vector
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        note['id'], note['content'], note['summary'], tag_list,
                        bool(note['pinned']), note['author'], note['created'],
                        note['session_id'], note['linked_items'],
                        note['pagerank'], bool(note['has_vector'])
                    ))
                
                # Migrate edges
                edges = sqlite_conn.execute("SELECT * FROM edges").fetchall()
                for edge in edges:
                    duck_conn.execute('''
                        INSERT INTO edges (from_id, to_id, type, weight, created)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (edge['from_id'], edge['to_id'], edge['type'],
                          edge['weight'], edge['created']))
                
                # Migrate other tables
                _migrate_simple_table(sqlite_conn, duck_conn, 'entities')
                _migrate_simple_table(sqlite_conn, duck_conn, 'entity_notes')
                _migrate_simple_table(sqlite_conn, duck_conn, 'sessions')
                _migrate_simple_table(sqlite_conn, duck_conn, 'vault')
                _migrate_simple_table(sqlite_conn, duck_conn, 'stats')
                
                duck_conn.execute("COMMIT")
                logging.info("Migration committed successfully!")
                
                max_id = duck_conn.execute("SELECT MAX(id) FROM notes").fetchone()[0]
                if max_id:
                    duck_conn.execute(f"ALTER SEQUENCE notes_id_seq RESTART WITH {max_id + 1}")
                    logging.info(f"Sequence reset to start at {max_id + 1}")
                
            except Exception as e:
                duck_conn.execute("ROLLBACK")
                logging.error(f"Migration failed, rolled back: {e}")
                raise
        
        sqlite_conn.close()
        
        backup_path = SQLITE_DB_FILE.with_suffix(
            f'.backup_{datetime.now().strftime("%Y%m%d%H%M")}.db'
        )
        shutil.move(SQLITE_DB_FILE, backup_path)
        logging.info(f"Old database backed up to {backup_path}")
        
        return True
        
    except Exception as e:
        logging.error(f"Migration failed: {e}", exc_info=True)
        if DB_FILE.exists():
            os.remove(DB_FILE)
        sys.exit(1)

def init_db():
    """Initialize DuckDB database"""
    migrate_from_sqlite()

    with _get_db_conn() as conn:
        tables = conn.execute("SHOW TABLES").fetchall()
        if not any(t[0] == 'notes' for t in tables):
            logging.info("Creating new database schema...")
            _create_duckdb_schema(conn)
        else:
            # Check for directory_access table (new in v6.2)
            if not any(t[0] == 'directory_access' for t in tables):
                logging.info("Adding directory tracking table...")
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS directory_access (
                        id BIGINT PRIMARY KEY,
                        path TEXT NOT NULL,
                        accessed TIMESTAMPTZ NOT NULL,
                        note_id BIGINT,
                        operation VARCHAR
                    )
                ''')
                conn.execute("CREATE INDEX IF NOT EXISTS idx_dir_access_time ON directory_access(accessed DESC)")
            
            try:
                max_id = conn.execute("SELECT MAX(id) FROM notes").fetchone()[0]
                if max_id:
                    # DuckDB doesn't support setval, just use ALTER SEQUENCE
                    conn.execute(f"ALTER SEQUENCE notes_id_seq RESTART WITH {max_id + 1}")
                    logging.info(f"Reset sequence to start at {max_id + 1}")
            except Exception as e:
                # DuckDB may not support ALTER SEQUENCE - this is expected and non-critical
                # We use manual ID management in remember() so sequence issues don't break functionality
                pass
        
        load_known_entities(conn)
        
        note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        if 'db_ready' not in _logged_once:
            logging.info(f"Database ready with {note_count} notes")
            _logged_once.add('db_ready')

def load_known_entities(conn: duckdb.DuckDBPyConnection):
    """Load known entities into memory cache"""
    global KNOWN_ENTITIES
    try:
        entities = conn.execute('SELECT name FROM entities').fetchall()
        KNOWN_ENTITIES = {e[0].lower() for e in entities}
    except:
        KNOWN_ENTITIES = set()

def _ensure_embeddings_loaded():
    """Lazy-load embeddings only when needed (on first semantic search)"""
    global _embeddings_initialized, encoder, chroma_client, collection

    # Check both flag AND encoder object existence (fix for "Dark Memory" bug)
    if _embeddings_initialized and encoder is not None and collection is not None:
        return True

    if 'embedding_init' not in _logged_once:
        logging.info("Lazy-loading embedding model (first semantic search)...")
        _logged_once.add('embedding_init')
    encoder_result = _init_embedding_model()
    vector_result = _init_vector_db()

    # Only set initialized flag if embeddings actually loaded successfully
    if encoder is not None and collection is not None:
        _embeddings_initialized = True

    return encoder is not None

def _init_embedding_model():
    """Initialize embedding model - automatically discover local models first"""
    global encoder, EMBEDDING_MODEL

    if not ST_AVAILABLE or not USE_SEMANTIC:
        logging.debug("Semantic search disabled")
        return None
    
    try:
        # First check for ANY local models in the models folder
        # Check both tools/models and parent models directory
        models_dirs = [
            Path(__file__).parent / "models",
            Path(__file__).parent.parent / "models"
        ]

        for models_dir in models_dirs:
            if not (models_dir.exists() and models_dir.is_dir()):
                continue

            # Find all subdirectories that might contain models
            for model_folder in models_dir.iterdir():
                if model_folder.is_dir():
                    # Check if it looks like a valid model folder
                    # Should have config.json and either pytorch_model.bin or model.safetensors
                    config_file = model_folder / "config.json"
                    has_model = (
                        config_file.exists() and
                        ((model_folder / "model.safetensors").exists() or
                         (model_folder / "pytorch_model.bin").exists())
                    )

                    if has_model:
                        try:
                            model_name = model_folder.name
                            if 'model_discovery' not in _logged_once:
                                logging.info(f"Found local model: {model_name} at {model_folder}")
                                _logged_once.add('model_discovery')
                            if 'model_load_attempt' not in _logged_once:
                                logging.info(f"Attempting to load {model_name}...")
                                _logged_once.add('model_load_attempt')
                            encoder = SentenceTransformer(str(model_folder), device='cpu')
                            test = encoder.encode("test", convert_to_numpy=True)
                            EMBEDDING_MODEL = f'local-{model_name}'
                            if 'model_success' not in _logged_once:
                                logging.info(f"✓ Successfully loaded local model: {model_name}")
                                logging.info(f"✓ Embedding dimensions: {test.shape[0]}")
                                _logged_once.add('model_success')
                            return encoder
                        except Exception as e:
                            logging.warning(f"Failed to load local model {model_name}: {e}")
                            continue
        
        # Fall back to downloading models if no local models work
        logging.info("No local models found or loaded, trying online models...")
        models = [
            ('nomic-ai/nomic-embed-text-v1.5', 'nomic-1.5'),
            ('mixedbread-ai/mxbai-embed-large-v1', 'mxbai'),
            ('BAAI/bge-small-en-v1.5', 'bge-small'),
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

def _init_vector_db():
    """Initialize ChromaDB for vector storage"""
    global chroma_client, collection
    if not CHROMADB_AVAILABLE or not encoder:
        return False
    try:
        chroma_client = chromadb.PersistentClient(
            path=str(VECTOR_DIR),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        # Use model-specific collection to avoid embedding mismatches
        collection_name = f"notebook_v6_{EMBEDDING_MODEL or 'default'}"
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        if 'chromadb_init' not in _logged_once:
            logging.info(f"ChromaDB initialized with {collection.count()} vectors")
            _logged_once.add('chromadb_init')
        return True
    except Exception as e:
        logging.error(f"ChromaDB init failed: {e}")
        return False

def _detect_or_create_session(note_id: int, created: datetime, conn: duckdb.DuckDBPyConnection) -> Optional[int]:
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

def _create_all_edges(note_id: int, content: str, session_id: Optional[int], conn: duckdb.DuckDBPyConnection):
    """Create all edge types efficiently - backend only, never shown"""
    now = datetime.now()
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
    refs = _extract_references(content)
    if refs:
        # Security: placeholders generated from list length (safe)
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
    entities = _extract_entities(content)
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
    if edges_to_add:
        for edge in edges_to_add:
            conn.execute(
                'INSERT INTO edges (from_id, to_id, type, weight, created) VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING',
                edge
            )

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

def _calculate_pagerank_if_needed(conn: duckdb.DuckDBPyConnection):
    """Calculate PageRank when needed"""
    global PAGERANK_DIRTY, PAGERANK_CACHE_TIME
    
    count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if count < 50:
        return
    
    current_time = time.time()
    if PAGERANK_DIRTY or (current_time - PAGERANK_CACHE_TIME > PAGERANK_CACHE_SECONDS):
        calculate_pagerank_duckdb(conn)
        PAGERANK_DIRTY = False
        PAGERANK_CACHE_TIME = current_time

def _log_operation(op: str, dur_ms: int = None):
    """Log operation for stats"""
    try:
        with _get_db_conn() as conn:
            # Get next ID for stats table
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM stats").fetchone()[0]
            new_id = max_id + 1
            
            conn.execute(
                'INSERT INTO stats (id, operation, ts, dur_ms, author) VALUES (?, ?, ?, ?, ?)',
                [new_id, op, datetime.now(), dur_ms, CURRENT_AI_ID]
            )
    except:
        pass

def _log_directory_access(path: str, note_id: Optional[int] = None, operation: Optional[str] = None):
    """Log directory access to database"""
    try:
        with _get_db_conn() as conn:
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM directory_access").fetchone()[0]
            new_id = max_id + 1
            
            conn.execute('''
                INSERT INTO directory_access (id, path, accessed, note_id, operation)
                VALUES (?, ?, ?, ?, ?)
            ''', [new_id, path, datetime.now(), note_id, operation])
            
            # Also track in memory
            track_directory(path)
            
    except Exception as e:
        logging.debug(f"Could not log directory access: {e}")

def _vacuum_database():
    """Perform VACUUM to reclaim space and optimize database"""
    try:
        logging.info("Starting database VACUUM operation...")
        start_time = time.time()
        
        with _get_db_conn() as conn:
            # Get size before
            size_before = os.path.getsize(DB_FILE)
            
            # Perform VACUUM
            conn.execute("VACUUM")
            
            # Get size after
            size_after = os.path.getsize(DB_FILE)
            
            elapsed = time.time() - start_time
            reduction = size_before - size_after
            percent = (reduction / size_before * 100) if size_before > 0 else 0
            
            logging.info(f"VACUUM completed in {elapsed:.2f}s")
            logging.info(f"Size reduced by {reduction / 1024 / 1024:.1f}MB ({percent:.1f}%)")
            
            return {
                "before_mb": size_before / 1024 / 1024,
                "after_mb": size_after / 1024 / 1024,
                "saved_mb": reduction / 1024 / 1024,
                "percent_saved": percent
            }
            
    except Exception as e:
        logging.error(f"VACUUM failed: {e}")
        return {"error": str(e)}

def get_storage_stats() -> Dict:
    """Get storage statistics"""
    try:
        with _get_db_conn() as conn:
            stats = {
                "db_size_mb": os.path.getsize(DB_FILE) / 1024 / 1024,
                "notes": conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0],
                "edges": conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
                "entities": conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
                "sessions": conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                "vectors": collection.count() if collection else 0,
                "recent_dirs": len(RECENT_DIRECTORIES)
            }
            return stats
    except Exception as e:
        logging.error(f"Could not get storage stats: {e}")
        return {}

# Initialize storage on module import
init_db()
# NOTE: Embeddings are now lazy-loaded on first use via ensure_embeddings_loaded()
# This saves 7+ seconds on startup when semantic search isn't needed
