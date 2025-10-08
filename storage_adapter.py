"""
Unified storage adapter that switches between PostgreSQL, Redis, and DuckDB backends.

Priority order:
1. PostgreSQL (production-grade, best for multi-AI)
2. Redis (real-time pub/sub, distributed locks)
3. DuckDB (embedded, always available fallback)

This provides a consistent API regardless of which backend is configured.
"""

from typing import Optional, List, Dict, Any
import logging

# Dual import pattern (package vs direct execution)
try:
    from .teambook_config import get_storage_backend
except ImportError:
    from teambook_config import get_storage_backend

logger = logging.getLogger(__name__)


class TeambookStorageAdapter:
    """
    Adapter that routes to PostgreSQL, Redis, or DuckDB backend.
    
    Automatically selects best available backend based on environment:
    - PostgreSQL if POSTGRES_URL set (production-grade)
    - Redis if USE_REDIS=true (real-time features)
    - DuckDB otherwise (zero-setup fallback)

    Usage:
        storage = TeambookStorageAdapter("town-hall-YourComputerName")
        note_id = storage.write_note(content="Hello world")
        notes = storage.read_notes(limit=10)
    """

    def __init__(self, teambook_name: str):
        self.teambook_name = teambook_name
        self._backend = None
        self._backend_type = None
        self._init_backend()

    def _init_backend(self):
        """Initialize the appropriate storage backend with priority fallback."""
        backend_type = get_storage_backend()

        if backend_type == "postgresql":
            try:
                from .teambook_storage_postgresql import PostgreSQLTeambookStorage
                self._backend = PostgreSQLTeambookStorage(self.teambook_name)
                self._backend_type = "postgresql"
                logger.info(f"✓ Using PostgreSQL backend for {self.teambook_name}")
                return
            except Exception as e:
                logger.warning(f"PostgreSQL initialization failed: {e}, falling back to Redis/DuckDB")
                # Fall through to Redis/DuckDB

        if backend_type == "redis" or backend_type == "postgresql":  # Fallback from PostgreSQL
            try:
                from .teambook_storage_redis import RedisTeambookStorage
                self._backend = RedisTeambookStorage(self.teambook_name)
                self._backend_type = "redis"
                logger.info(f"✓ Using Redis backend for {self.teambook_name}")
                return
            except Exception as e:
                if backend_type == "redis":
                    logger.warning(f"Redis initialization failed: {e}, falling back to DuckDB")
                # Fall through to DuckDB

        # DuckDB fallback (always works)
        from .teambook_storage import DuckDBTeambookStorage
        self._backend = DuckDBTeambookStorage(self.teambook_name)
        self._backend_type = "duckdb"
        logger.info(f"✓ Using DuckDB backend for {self.teambook_name}")

    # ==================== NOTES ====================

    def write_note(self, content: str, **kwargs) -> int:
        """Write a note. Args passed through to backend with type conversion."""
        # Convert tags for backend compatibility
        if 'tags' in kwargs and kwargs['tags'] is not None:
            if self._backend_type == "redis" and isinstance(kwargs['tags'], list):
                # Redis expects comma-separated string
                kwargs['tags'] = ','.join(kwargs['tags'])
            elif self._backend_type in ("postgresql", "duckdb") and isinstance(kwargs['tags'], str):
                # PostgreSQL/DuckDB expect list
                kwargs['tags'] = [t.strip() for t in kwargs['tags'].split(',')] if kwargs['tags'] else []

        return self._backend.write_note(content, **kwargs)

    def read_notes(self, **kwargs) -> List[Dict[str, Any]]:
        """Read notes. Args passed through to backend."""
        return self._backend.read_notes(**kwargs)

    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """Get a single note by ID."""
        return self._backend.get_note(note_id)

    def update_note(self, note_id: int, **updates) -> bool:
        """Update note fields."""
        return self._backend.update_note(note_id, **updates)

    def delete_note(self, note_id: int) -> bool:
        """Delete a note."""
        return self._backend.delete_note(note_id)

    # ==================== EDGES ====================

    def add_edge(self, from_id: int, to_id: int, edge_type: str, weight: float = 1.0) -> None:
        """Add a graph edge."""
        return self._backend.add_edge(from_id, to_id, edge_type, weight)

    def get_edges(self, note_id: int, reverse: bool = False) -> List[Dict[str, Any]]:
        """Get edges from/to a note."""
        return self._backend.get_edges(note_id, reverse)

    # ==================== VAULT ====================

    def vault_set(self, key: str, encrypted_value: str, author: str) -> None:
        """Store encrypted value."""
        return self._backend.vault_set(key, encrypted_value, author)

    def vault_get(self, key: str) -> Optional[str]:
        """Retrieve encrypted value."""
        return self._backend.vault_get(key)

    def vault_delete(self, key: str) -> bool:
        """Delete encrypted value."""
        return self._backend.vault_delete(key)

    def vault_list(self) -> List[Dict[str, Any]]:
        """List all vault keys with metadata."""
        return self._backend.vault_list()

    # ==================== SESSIONS ====================

    def create_session(self) -> int:
        """Create a new session."""
        return self._backend.create_session()

    # ==================== STATS ====================

    def get_stats(self) -> Dict[str, int]:
        """Get teambook statistics."""
        stats = self._backend.get_stats()
        stats['backend'] = self._backend_type
        return stats
    
    # ==================== VECTORS ====================

    def store_vector(self, note_id: int, vector: List[float]) -> bool:
        """Store vector embedding for a note."""
        # Check if backend supports vectors
        if hasattr(self._backend, 'store_vector'):
            return self._backend.store_vector(note_id, vector)
        # Fallback: vectors not supported by this backend
        return False

    def search_vectors(self, query_vector: List[float], limit: int = 10) -> List[int]:
        """Search for similar vectors."""
        # Check if backend supports vector search
        if hasattr(self._backend, 'search_vectors'):
            return self._backend.search_vectors(query_vector, limit)
        # Fallback: vector search not supported
        return []

    def has_vector(self, note_id: int) -> bool:
        """Check if note has vector embedding."""
        if hasattr(self._backend, 'has_vector'):
            return self._backend.has_vector(note_id)
        return False

    # ==================== BACKEND INFO ====================

    def get_backend_type(self) -> str:
        """Get the active backend type."""
        return self._backend_type


# Note: DuckDBTeambookStorage wrapper exists in teambook_storage.py
# RedisTeambookStorage exists in teambook_storage_redis.py
# PostgreSQLTeambookStorage exists in teambook_storage_postgresql.py
