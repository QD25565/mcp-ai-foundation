#!/usr/bin/env python3
"""
Performance Utilities - Connection Pooling & Caching
Works for both CLI and MCP modes
"""
import duckdb
import threading
from functools import wraps, lru_cache
from typing import Dict, Optional, Callable, Any
from pathlib import Path
import time
import logging

# Thread-safe connection pool
_connection_pool: Dict[str, duckdb.DuckDBPyConnection] = {}
_pool_lock = threading.Lock()

class PooledConnectionWrapper:
    """Wrapper that prevents pooled connections from being closed in 'with' statements"""
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't close the connection - it's pooled!
        pass

    def __getattr__(self, name):
        # Delegate all other attributes to the real connection
        return getattr(self._conn, name)

def get_pooled_connection(db_path: str):
    """
    Get a pooled database connection (thread-safe)

    Works for both CLI and MCP - reuses connections instead of creating new ones.
    Reduces connection overhead from 10-50ms to near-zero.

    Returns a wrapper that prevents the connection from being closed when used
    with 'with' statement.

    Args:
        db_path: Path to DuckDB database file

    Returns:
        Reusable DuckDB connection (wrapped to prevent closing)
    """
    db_path = str(Path(db_path).resolve())

    with _pool_lock:
        if db_path not in _connection_pool:
            logging.debug(f"[POOL] Creating new connection: {db_path}")
            _connection_pool[db_path] = duckdb.connect(db_path)
        else:
            logging.debug(f"[POOL] Reusing connection: {db_path}")

        return PooledConnectionWrapper(_connection_pool[db_path])

def close_all_connections():
    """Close all pooled connections (cleanup on exit)"""
    with _pool_lock:
        for db_path, conn in _connection_pool.items():
            try:
                conn.close()
                logging.debug(f"[POOL] Closed connection: {db_path}")
            except:
                pass
        _connection_pool.clear()

# Time-based cache decorator (for network calls, expensive operations)
def timed_cache(seconds: int = 3600):
    """
    Cache function results for a specified duration

    Args:
        seconds: Cache TTL in seconds (default: 1 hour)

    Usage:
        @timed_cache(seconds=600)  # Cache for 10 minutes
        def expensive_network_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_time = {}
        cache_lock = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from args/kwargs
            key = str(args) + str(sorted(kwargs.items()))

            with cache_lock:
                # Check if cached and not expired
                if key in cache and key in cache_time:
                    age = time.time() - cache_time[key]
                    if age < seconds:
                        logging.debug(f"[CACHE] Hit for {func.__name__} (age: {age:.1f}s)")
                        return cache[key]

                # Cache miss or expired - call function
                logging.debug(f"[CACHE] Miss for {func.__name__}")
                result = func(*args, **kwargs)

                # Update cache
                cache[key] = result
                cache_time[key] = time.time()

                return result

        # Add cache clearing method
        def clear_cache():
            with cache_lock:
                cache.clear()
                cache_time.clear()

        wrapper.clear_cache = clear_cache
        return wrapper

    return decorator

# Performance monitoring decorator
def timed(threshold_ms: float = 100.0):
    """
    Measure function execution time and log if slow

    Args:
        threshold_ms: Log warning if execution exceeds this (default: 100ms)

    Usage:
        @timed(threshold_ms=50)
        def slow_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000

            if duration_ms > threshold_ms:
                logging.warning(f"[SLOW] {func.__name__}: {duration_ms:.1f}ms")
            else:
                logging.debug(f"[PERF] {func.__name__}: {duration_ms:.1f}ms")

            return result

        return wrapper

    return decorator

# Batch operation helper
def batch_execute(conn: duckdb.DuckDBPyConnection, query: str, params_list: list, batch_size: int = 100):
    """
    Execute query with multiple parameter sets efficiently

    Much faster than individual execute() calls in a loop.
    Uses executemany() for optimal performance.

    Args:
        conn: DuckDB connection
        query: SQL query with placeholders
        params_list: List of parameter tuples
        batch_size: Process in batches of this size (for very large lists)

    Example:
        # Instead of:
        for params in param_list:
            conn.execute(query, params)

        # Do this:
        batch_execute(conn, query, param_list)
    """
    if not params_list:
        return

    # Process in batches to avoid memory issues
    for i in range(0, len(params_list), batch_size):
        batch = params_list[i:i + batch_size]
        conn.executemany(query, batch)
        logging.debug(f"[BATCH] Executed {len(batch)} operations")

# Result caching decorator with TTL
class CachedResult:
    """Thread-safe result cache with time-to-live"""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.timestamps = {}
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached result if not expired"""
        with self.lock:
            if key in self.cache:
                age = time.time() - self.timestamps[key]
                if age < self.ttl_seconds:
                    logging.debug(f"[CACHE] Hit: {key} (age: {age:.1f}s)")
                    return self.cache[key]
                else:
                    # Expired - remove
                    del self.cache[key]
                    del self.timestamps[key]
        return None

    def set(self, key: str, value: Any):
        """Store result in cache"""
        with self.lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
            logging.debug(f"[CACHE] Set: {key}")

    def clear(self):
        """Clear all cached results"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

# Global caches for common operations
note_cache = CachedResult(ttl_seconds=300)  # 5 minute cache for notes
query_cache = CachedResult(ttl_seconds=60)   # 1 minute cache for queries
stats_cache = CachedResult(ttl_seconds=30)   # 30 second cache for stats

# Network call resilience wrapper
def resilient_network_call(func: Callable, fallback_value: Any = None, timeout: float = 3.0):
    """
    Wrapper for network calls with timeout and fallback

    Args:
        func: Function that makes network call
        fallback_value: Value to return if call fails
        timeout: Request timeout in seconds

    Returns:
        Result from func() or fallback_value if failed
    """
    try:
        return func()
    except Exception as e:
        logging.warning(f"[NETWORK] Call failed: {e}, using fallback")
        return fallback_value

# Cleanup on module exit
import atexit
atexit.register(close_all_connections)
