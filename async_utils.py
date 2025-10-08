#!/usr/bin/env python3
"""
Async Utilities - Non-blocking I/O for AI-First Tools
Provides async network calls and parallel operations
"""
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps

# Check if event loop is available
def get_or_create_event_loop():
    """Get existing event loop or create new one (handles both sync and async contexts)"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    except RuntimeError:
        # No event loop in current thread - create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

# Async network call wrapper
async def async_http_get(url: str, timeout: float = 1.0, **kwargs) -> Optional[Dict]:
    """
    Make async HTTP GET request (non-blocking for AI operations)

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds (default: 1s for AI responsiveness)
        **kwargs: Additional aiohttp.ClientSession.get() parameters

    Returns:
        Response JSON dict or None if failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.debug(f"[ASYNC] HTTP {response.status} for {url}")
                    return None
    except asyncio.TimeoutError:
        logging.debug(f"[ASYNC] Timeout for {url}")
        return None
    except Exception as e:
        logging.debug(f"[ASYNC] Request failed for {url}: {e}")
        return None

# Sync wrapper for async functions (for backward compatibility)
def run_async(coro):
    """
    Run async coroutine in sync context (CLI and MCP compatible)

    Usage:
        result = run_async(async_http_get("https://api.example.com"))
    """
    loop = get_or_create_event_loop()
    try:
        if loop.is_running():
            # Already in async context - create new task
            return asyncio.create_task(coro)
        else:
            # Sync context - run until complete
            return loop.run_until_complete(coro)
    except RuntimeError:
        # Fallback for edge cases
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

# Parallel async execution
async def async_parallel(*coroutines):
    """
    Execute multiple async operations in parallel

    Args:
        *coroutines: Async functions/coroutines to run in parallel

    Returns:
        List of results in same order as input

    Example:
        results = await async_parallel(
            async_http_get("url1"),
            async_http_get("url2"),
            async_http_get("url3")
        )
    """
    return await asyncio.gather(*coroutines, return_exceptions=True)

# Decorator for async-capable functions
def async_capable(func: Callable) -> Callable:
    """
    Decorator to make sync function async-capable

    Automatically handles both sync and async contexts.

    Usage:
        @async_capable
        def my_function(url):
            return run_async(async_http_get(url))
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        # If result is a coroutine, handle it appropriately
        if asyncio.iscoroutine(result):
            return run_async(result)
        return result

    return wrapper

# Async retry logic with exponential backoff
async def async_retry(coro_func: Callable, max_attempts: int = 3, base_delay: float = 0.1):
    """
    Retry async operation with exponential backoff

    Args:
        coro_func: Async function (coroutine) to retry
        max_attempts: Maximum retry attempts
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        Result from successful attempt or None
    """
    for attempt in range(max_attempts):
        try:
            result = await coro_func()
            if result is not None:
                return result
        except Exception as e:
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logging.debug(f"[ASYNC] Retry {attempt + 1}/{max_attempts} after {delay}s")
                await asyncio.sleep(delay)
            else:
                logging.warning(f"[ASYNC] All {max_attempts} attempts failed: {e}")

    return None

# Async cache with TTL (thread-safe)
class AsyncCache:
    """Async-compatible cache with time-to-live"""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value (async-safe)"""
        async with self._lock:
            import time
            if key in self.cache:
                age = time.time() - self.timestamps[key]
                if age < self.ttl_seconds:
                    logging.debug(f"[ASYNC CACHE] Hit: {key} (age: {age:.1f}s)")
                    return self.cache[key]
                else:
                    # Expired - remove
                    del self.cache[key]
                    del self.timestamps[key]
        return None

    async def set(self, key: str, value: Any):
        """Store value in cache (async-safe)"""
        async with self._lock:
            import time
            self.cache[key] = value
            self.timestamps[key] = time.time()
            logging.debug(f"[ASYNC CACHE] Set: {key}")

    async def clear(self):
        """Clear all cached values"""
        async with self._lock:
            self.cache.clear()
            self.timestamps.clear()

# Global async cache instances
location_cache = AsyncCache(ttl_seconds=3600)  # 1 hour
weather_cache = AsyncCache(ttl_seconds=600)    # 10 minutes

# Async batch processor
async def async_batch_process(items: list, async_func: Callable, batch_size: int = 10):
    """
    Process items in batches asynchronously

    Args:
        items: List of items to process
        async_func: Async function to apply to each item
        batch_size: Process this many items in parallel

    Returns:
        List of results
    """
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[async_func(item) for item in batch],
            return_exceptions=True
        )
        results.extend(batch_results)

        logging.debug(f"[ASYNC BATCH] Processed {len(batch)} items")

    return results
