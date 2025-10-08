#!/usr/bin/env python3
"""
TEAMBOOK AMBIENT AWARENESS
==========================
Object permanence through time for AI collaboration.

Provides peripheral awareness of team activity without breaking focus.
"""

import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from functools import wraps

# Fix import path
sys.path.insert(0, str(Path(__file__).parent))

from teambook_shared import CURRENT_AI_ID, CURRENT_TEAMBOOK, logging

# ====================  HELPER ====================

def get_storage_adapter(teambook_name):
    """Late import to avoid circular dependency"""
    try:
        from .teambook_api import get_storage_adapter as _get_adapter
        return _get_adapter(teambook_name)
    except ImportError:
        from teambook_api import get_storage_adapter as _get_adapter
        return _get_adapter(teambook_name)

# Storage available by default (actual check happens in get_postgres_pool)
STORAGE_AVAILABLE = True

def get_postgres_pool():
    """Get PostgreSQL connection pool from storage adapter"""
    try:
        adapter = get_storage_adapter(CURRENT_TEAMBOOK)
        if not adapter:
            return None

        # Check if using PostgreSQL backend
        if adapter.get_backend_type() != 'postgresql':
            return None

        # Access the internal pool (adapter._backend._pool if postgres)
        if hasattr(adapter, '_backend') and hasattr(adapter._backend, '_pool'):
            return adapter._backend._pool

        return None
    except Exception as e:
        logging.debug(f"Could not get postgres pool: {e}")
        return None


# ==================== EVENT LOGGING ====================

def _log_coordination_event(
    event_type: str,
    ai_id: str = None,
    task_id: int = None,
    project_id: int = None,
    summary: str = None,
    metadata: dict = None
):
    """
    Log a coordination event for ambient awareness.

    Event Types:
    - project_created
    - task_created
    - task_claimed
    - task_completed
    - task_unclaimed
    - help_requested
    - broadcast
    """
    if not STORAGE_AVAILABLE:
        logging.debug(f"Storage not available, cannot log event {event_type}")
        return

    ai_id = ai_id or CURRENT_AI_ID

    try:
        pool = get_postgres_pool()
        if not pool:
            logging.debug(f"PostgreSQL pool not available, cannot log event {event_type}")
            return  # Events only supported on PostgreSQL

        import psycopg2.extras

        with pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO coordination_events
                    (timestamp, event_type, ai_id, task_id, project_id, summary, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    datetime.now(timezone.utc),
                    event_type,
                    ai_id,
                    task_id,
                    project_id,
                    summary,
                    psycopg2.extras.Json(metadata or {})
                ))

    except Exception as e:
        logging.debug(f"Event logging failed (non-critical): {e}")


# ==================== LAST-SEEN TRACKING ====================

def update_last_seen(ai_id: str = None):
    """Update last ambient check timestamp for AI"""
    if not STORAGE_AVAILABLE:
        return

    ai_id = ai_id or CURRENT_AI_ID

    try:
        pool = get_postgres_pool()
        if not pool:
            return

        with pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO ai_last_seen (ai_id, last_ambient_check, last_full_sync)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ai_id) DO UPDATE
                    SET last_ambient_check = EXCLUDED.last_ambient_check
                ''', (ai_id, datetime.now(timezone.utc), datetime.now(timezone.utc)))

    except Exception as e:
        logging.debug(f"Last-seen update failed (non-critical): {e}")


def get_last_seen(ai_id: str = None) -> datetime:
    """Get when AI last checked for ambient updates"""
    if not STORAGE_AVAILABLE:
        return datetime.now(timezone.utc) - timedelta(minutes=30)  # Default: 30min ago

    ai_id = ai_id or CURRENT_AI_ID

    try:
        pool = get_postgres_pool()
        if not pool:
            return datetime.now(timezone.utc) - timedelta(minutes=30)

        with pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT last_ambient_check FROM ai_last_seen WHERE ai_id = %s
                ''', (ai_id,))
                row = cur.fetchone()
                if row:
                    return row[0]
                else:
                    # First time - return 30min ago
                    return datetime.now(timezone.utc) - timedelta(minutes=30)

    except Exception as e:
        logging.debug(f"Get last-seen failed: {e}")
        return datetime.now(timezone.utc) - timedelta(minutes=30)


# ==================== EVENT RETRIEVAL & FILTERING ====================

def get_relevant_events(ai_id: str = None, since: datetime = None, limit: int = 3) -> List[Dict]:
    """
    Get events relevant to this AI since last check.

    Relevance Rules:
    - Always: Completions in my projects
    - Always: Urgent tasks (p:9) created
    - Always: Help requests in my projects
    - Sometimes: Activity in my projects
    - Never: My own actions
    """
    if not STORAGE_AVAILABLE:
        return []

    ai_id = ai_id or CURRENT_AI_ID

    if since is None:
        since = get_last_seen(ai_id)

    try:
        adapter = get_storage_adapter(CURRENT_TEAMBOOK)
        if not adapter or adapter.get_backend_type() != 'postgresql':
            return []

        # Get AI's current work context
        my_tasks = adapter.read_notes(note_type='task', limit=100, mode='recent')
        my_task_ids = [t['id'] for t in my_tasks if (t.get('claimed_by') == ai_id or t.get('owner') == ai_id)]
        my_project_ids = list(set([t.get('parent_id') for t in my_tasks if t.get('parent_id')]))

        # Fetch recent events
        pool = get_postgres_pool()
        if not pool:
            return []

        with pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT id, timestamp, event_type, ai_id, task_id, project_id, summary, metadata
                    FROM coordination_events
                    WHERE timestamp > %s
                    ORDER BY timestamp DESC
                    LIMIT 50
                ''', (since,))

                events = []
                for row in cur.fetchall():
                    event_id, timestamp, event_type, event_ai, task_id, project_id, summary, metadata_dict = row
                    events.append({
                        'id': event_id,
                        'timestamp': timestamp,
                        'event_type': event_type,
                        'ai_id': event_ai,
                        'task_id': task_id,
                        'project_id': project_id,
                        'summary': summary,
                        'metadata': metadata_dict if metadata_dict else {}
                    })

        # Filter for relevance
        relevant = []

        logging.debug(f"Filtering {len(events)} events for AI {ai_id}. My projects: {my_project_ids}")

        for event in events:
            # Skip own actions
            if event['ai_id'] == ai_id:
                logging.debug(f"  Skip (own action): {event['event_type']} by {event['ai_id']}")
                continue

            # Always show: Completions in my projects
            if event['event_type'] == 'task_completed' and event['project_id'] in my_project_ids:
                logging.debug(f"  Include (completion in my project): {event['event_type']}")
                relevant.append(event)
                continue

            # Always show: Urgent tasks created
            if event['event_type'] == 'task_created':
                priority = event['metadata'].get('priority', 0)
                if priority >= 9:
                    logging.debug(f"  Include (urgent task p:{priority}): {event['event_type']}")
                    relevant.append(event)
                    continue

            # Always show: Help requests in my projects
            if event['event_type'] == 'help_requested' and event['project_id'] in my_project_ids:
                logging.debug(f"  Include (help in my project): {event['event_type']}")
                relevant.append(event)
                continue

            # Always show: Task claims in my projects
            if event['event_type'] == 'task_claimed' and event['project_id'] in my_project_ids:
                logging.debug(f"  Include (claim in my project): {event['event_type']}")
                relevant.append(event)
                continue

            # Always show: New projects created
            if event['event_type'] == 'project_created':
                logging.debug(f"  Include (project created): {event['event_type']} by {event['ai_id']}")
                relevant.append(event)

        # Update last-seen timestamp
        update_last_seen(ai_id)

        return relevant[:limit]

    except Exception as e:
        logging.debug(f"Get relevant events failed: {e}")
        return []


# ==================== AMBIENT INJECTION ====================

def format_ambient_update(events: List[Dict]) -> str:
    """
    Format events into ambient injection string.

    Format: [AMBIENT] HH:MM | Event summary, Event summary
    """
    if not events:
        return ""

    current_time = datetime.now(timezone.utc).strftime('%H:%M')

    # Format each event
    event_summaries = []
    for event in events:
        if event['event_type'] == 'task_completed':
            event_summaries.append(f"{event['ai_id']} completed #{event['task_id']}")

        elif event['event_type'] == 'task_created':
            priority = event['metadata'].get('priority', 5)
            event_summaries.append(f"{event['ai_id']} created urgent #{event['task_id']} [p:{priority}]")

        elif event['event_type'] == 'task_claimed':
            event_summaries.append(f"{event['ai_id']} claimed #{event['task_id']}")

        elif event['event_type'] == 'project_created':
            task_count = event['metadata'].get('task_count', 0)
            project_name = event['summary'] or f"project #{event['project_id']}"
            event_summaries.append(f"{event['ai_id']} created {project_name} ({task_count} tasks)")

        elif event['event_type'] == 'help_requested':
            event_summaries.append(f"{event['ai_id']} requested help on #{event['task_id']}")

    # Join with commas
    summary = ", ".join(event_summaries)

    return f"\n\n[AMBIENT] {current_time} | {summary}"


def get_ambient_updates(ai_id: str = None) -> str:
    """
    Get formatted ambient updates for AI.

    Returns empty string if no relevant updates.
    """
    events = get_relevant_events(ai_id)
    if not events:
        return ""

    return format_ambient_update(events)


# ==================== INJECTION DECORATOR ====================

# Throttle: Track last injection time per AI
_last_injection = {}
INJECTION_THROTTLE_SECONDS = 30

def should_inject(ai_id: str = None) -> bool:
    """Check if we should inject ambient updates (throttle check)"""
    ai_id = ai_id or CURRENT_AI_ID

    now = datetime.now(timezone.utc)
    last = _last_injection.get(ai_id)

    if last is None:
        _last_injection[ai_id] = now
        return True

    if (now - last).total_seconds() >= INJECTION_THROTTLE_SECONDS:
        _last_injection[ai_id] = now
        return True

    return False


def with_ambient_awareness(func):
    """
    Decorator to inject ambient awareness into function returns.

    Usage:
        @with_ambient_awareness
        def complete_project_task(...):
            return "task:123|completed"

    Result:
        "task:123|completed\n\n[AMBIENT] 03:25 | Sage completed #456, QD created urgent #789 [p:9]"
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Execute original function
        result = func(*args, **kwargs)

        # Check if we should inject
        if not should_inject():
            return result

        # Get ambient updates
        ambient = get_ambient_updates()

        if not ambient:
            return result

        # Inject based on result type
        if isinstance(result, str):
            # String result - append ambient
            return result + ambient

        elif isinstance(result, dict):
            # Dict result - add ambient key
            result['ambient'] = ambient.strip()
            return result

        else:
            # Unknown type - return as-is
            return result

    return wrapper


# ==================== MANUAL CHECK ====================

def check_ambient(**kwargs) -> str:
    """
    Manually check for ambient updates.

    Usage:
        teambook check_ambient

    Returns:
        Formatted ambient updates or message if none
    """
    ambient = get_ambient_updates()

    if ambient:
        return ambient.strip()  # Remove leading newlines
    else:
        return "No recent updates"


# ==================== EVENT CLEANUP ====================

def cleanup_old_events(days: int = 7):
    """
    Delete events older than N days.

    Run as background job or manual cleanup.
    """
    if not STORAGE_AVAILABLE:
        return

    try:
        pool = get_postgres_pool()
        if not pool:
            return

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        with pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    DELETE FROM coordination_events WHERE timestamp < %s
                ''', (cutoff,))
                deleted = cur.rowcount

                logging.info(f"Cleaned up {deleted} old coordination events")

    except Exception as e:
        logging.error(f"Event cleanup failed: {e}")
