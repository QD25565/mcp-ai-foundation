#!/usr/bin/env python3
"""
TEAMBOOK STORAGE ADAPTER INTERFACE v1.0.0
==========================================
Abstract base class for storage backends.
Enables PostgreSQL primary with DuckDB fallback.

Built by AIs, for AIs.
==========================================
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Tuple, Any, Dict
import logging


class StorageAdapter(ABC):
    """Abstract base class for storage backends (PostgreSQL, DuckDB)"""
    
    @abstractmethod
    def init_db(self):
        """Initialize database schema and tables"""
        pass
    
    @abstractmethod
    def get_conn(self):
        """Get database connection (context manager compatible)"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[List] = None) -> List[Tuple]:
        """Execute a query and return results"""
        pass
    
    @abstractmethod
    def execute_write(self, query: str, params: Optional[List] = None) -> None:
        """Execute a write operation (INSERT, UPDATE, DELETE)"""
        pass
    
    @abstractmethod
    def get_next_id(self, table: str) -> int:
        """Get next available ID for a table"""
        pass
    
    @abstractmethod
    def save_note(
        self,
        content: str,
        summary: str,
        tags: List[str],
        pinned: bool,
        author: str,
        owner: Optional[str],
        teambook_name: Optional[str],
        note_type: Optional[str],
        parent_id: Optional[int],
        linked_items: Optional[str]
    ) -> Dict[str, Any]:
        """Save a note and return note data"""
        pass
    
    @abstractmethod
    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """Get a note by ID"""
        pass
    
    @abstractmethod
    def search_notes(
        self,
        query: Optional[str] = None,
        mode: str = 'fuzzy',
        tag: Optional[str] = None,
        when: Optional[str] = None,
        owner: Optional[str] = None,
        pinned_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search notes with filters"""
        pass
    
    @abstractmethod
    def pin_note(self, note_id: int) -> bool:
        """Pin a note"""
        pass
    
    @abstractmethod
    def unpin_note(self, note_id: int) -> bool:
        """Unpin a note"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass
    
    @abstractmethod
    def close(self):
        """Close database connections"""
        pass
    
    @abstractmethod
    def supports_fts(self) -> bool:
        """Check if backend supports full-text search"""
        pass
    
    @abstractmethod
    def detect_or_create_session(
        self,
        note_id: int,
        created: datetime
    ) -> Optional[int]:
        """Detect existing session or create new one"""
        pass
    
    @abstractmethod
    def create_all_edges(
        self,
        note_id: int,
        content: str,
        session_id: Optional[int]
    ):
        """Create all edge types for a note"""
        pass
    
    @abstractmethod
    def calculate_pagerank(self):
        """Calculate PageRank for all notes"""
        pass
    
    @abstractmethod
    def log_operation(self, operation: str, duration_ms: Optional[int] = None):
        """Log an operation to stats table"""
        pass
    
    # Vault operations
    @abstractmethod
    def vault_store(self, key: str, value: str, author: str) -> bool:
        """Store encrypted value in vault"""
        pass
    
    @abstractmethod
    def vault_retrieve(self, key: str) -> Optional[str]:
        """Retrieve decrypted value from vault"""
        pass
    
    @abstractmethod
    def vault_list(self) -> List[str]:
        """List all vault keys"""
        pass
    
    # Evolution operations
    @abstractmethod
    def save_evolution_output(
        self,
        evolution_id: int,
        output_path: str,
        author: str
    ) -> int:
        """Save evolution output record"""
        pass
    
    @abstractmethod
    def get_evolution_outputs(self, evolution_id: int) -> List[Dict[str, Any]]:
        """Get all outputs for an evolution"""
        pass


def create_storage_adapter(backend: str = 'auto', **kwargs) -> StorageAdapter:
    """
    Factory function to create appropriate storage adapter.
    
    Args:
        backend: 'auto', 'postgresql', or 'duckdb'
        **kwargs: Backend-specific configuration
    
    Returns:
        StorageAdapter instance
    
    Raises:
        RuntimeError: If no backend available
    """
    if backend == 'auto':
        # Try PostgreSQL first, fallback to DuckDB
        if _is_postgres_available(**kwargs):
            backend = 'postgresql'
        else:
            backend = 'duckdb'
    
    if backend == 'postgresql':
        try:
            from teambook_storage_postgresql import PostgreSQLAdapter
            logging.info("✅ Using PostgreSQL backend")
            return PostgreSQLAdapter(**kwargs)
        except Exception as e:
            logging.warning(f"PostgreSQL init failed: {e}, falling back to DuckDB")
            backend = 'duckdb'
    
    if backend == 'duckdb':
        try:
            from teambook_storage_duckdb import DuckDBAdapter
            logging.info("✅ Using DuckDB backend (embedded)")
            return DuckDBAdapter(**kwargs)
        except Exception as e:
            logging.error(f"DuckDB init failed: {e}")
            raise RuntimeError("No storage backend available!")
    
    raise ValueError(f"Unknown backend: {backend}")


def _is_postgres_available(**kwargs) -> bool:
    """Check if PostgreSQL is available and configured"""
    import os
    
    # Check environment variables
    pg_url = kwargs.get('postgres_url') or os.getenv('POSTGRES_URL') or os.getenv('DATABASE_URL')
    if not pg_url:
        return False
    
    # Try to import psycopg2
    try:
        import psycopg2
        return True
    except ImportError:
        logging.warning("PostgreSQL URL found but psycopg2 not installed")
        return False
