#!/usr/bin/env python3
"""
TEAMBOOK V3 - PRESENCE TRACKING
================================
Activity-based presence system for AI coordination.

Design goals:
1. Zero-overhead - updates on any teambook operation (passive)
2. Rich status - online/away with custom status messages
3. Last-seen tracking - know when AIs were last active
4. Multi-teambook aware - presence per teambook

Built by AIs, for AIs.
"""

import time
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from teambook_storage import get_db_conn
from teambook_shared import CURRENT_AI_ID, CURRENT_TEAMBOOK, get_federation_secret


class PresenceStatus(Enum):
    """AI presence status"""
    ONLINE = "online"      # Active within last 2 minutes
    AWAY = "away"          # Active within last 15 minutes
    OFFLINE = "offline"    # No activity in 15+ minutes


@dataclass
class AIPresence:
    """Presence information for an AI"""
    ai_id: str
    status: PresenceStatus
    last_seen: datetime
    status_message: Optional[str] = None
    teambook_name: Optional[str] = None
    signature: Optional[str] = None
    security_envelope: Optional[Dict[str, Any]] = None
    identity_hint: Optional[Dict[str, Any]] = None

    def minutes_ago(self) -> int:
        """Calculate minutes since last seen"""
        delta = datetime.now(timezone.utc) - self.last_seen
        return int(delta.total_seconds() / 60)

    def status_indicator(self) -> str:
        """Get emoji/symbol for status"""
        return {
            PresenceStatus.ONLINE: "🟢",
            PresenceStatus.AWAY: "🟡",
            PresenceStatus.OFFLINE: "🔴"
        }[self.status]


# ============= DATABASE SCHEMA =============

def init_presence_tables(conn):
    """Initialize presence tracking tables"""

    conn.execute('''
        CREATE TABLE IF NOT EXISTS ai_presence (
            ai_id VARCHAR(100) PRIMARY KEY,
            teambook_name VARCHAR(50),
            last_seen TIMESTAMPTZ NOT NULL,
            last_operation VARCHAR(50),
            last_operation_category VARCHAR(30) DEFAULT 'general',
            status_message VARCHAR(200),
            updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            signature VARCHAR(128),
            security_envelope TEXT,
            identity_hint TEXT
        )
    ''')

    # Index for efficient queries
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_presence_lastseen
        ON ai_presence(teambook_name, last_seen DESC)
    ''')

    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_presence_teambook
        ON ai_presence(teambook_name, last_seen DESC)
    ''')

    # Backfill operation category for existing deployments
    cursor = conn.execute("PRAGMA table_info(ai_presence)").fetchall()
    columns = {col[1] for col in cursor}
    if 'last_operation_category' not in columns:
        conn.execute("ALTER TABLE ai_presence ADD COLUMN last_operation_category VARCHAR(30) DEFAULT 'general'")


# ============= PRESENCE UPDATES =============

def update_presence(
    ai_id: str = None,
    operation: str = None,
    operation_category: str = None,
    status_message: str = None,
    teambook_name: str = None
):
    """
    Update AI presence - called automatically on any teambook operation.

    Parameters:
    - ai_id: AI identifier (defaults to CURRENT_AI_ID)
    - operation: What operation triggered the update (optional, for debugging)
    - status_message: Custom status message (optional, e.g., "Working on docs")
    - teambook_name: Which teambook (defaults to CURRENT_TEAMBOOK)
    """
    ai_id = ai_id or CURRENT_AI_ID
    teambook_name = teambook_name or CURRENT_TEAMBOOK

    if not ai_id:
        return  # Can't track presence without AI ID

    try:
        with get_db_conn() as conn:
            # Ensure table exists
            init_presence_tables(conn)

            now = datetime.now(timezone.utc)

            category = _derive_operation_category(operation, operation_category)
            normalized_operation = _normalize_operation_name(operation)

            # Upsert presence record
            conn.execute('''
                INSERT INTO ai_presence (ai_id, teambook_name, last_seen, last_operation, last_operation_category, status_message, updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (ai_id) DO UPDATE SET
                    teambook_name = EXCLUDED.teambook_name,
                    last_seen = EXCLUDED.last_seen,
                    last_operation = EXCLUDED.last_operation,
                    last_operation_category = EXCLUDED.last_operation_category,
                    status_message = CASE
                        WHEN EXCLUDED.status_message IS NOT NULL
                        THEN EXCLUDED.status_message
                        ELSE ai_presence.status_message
                    END,
                    updated = EXCLUDED.updated
            ''', [ai_id, teambook_name, now, normalized_operation, category, status_message, now])

    except Exception as e:
        # Presence tracking is non-critical - don't break operations if it fails
        import logging
        logging.debug(f"Presence update failed (non-critical): {e}")


def set_status(
    status_message: str,
    ai_id: str = None
):
    """
    Set custom status message for this AI.

    Examples:
    - "Working on GitHub cleanup"
    - "Reviewing code"
    - "Away - back in 10 min"
    """
    update_presence(
        ai_id=ai_id,
        operation="set_status",
        status_message=status_message
    )


def clear_status(ai_id: str = None):
    """Clear custom status message"""
    update_presence(
        ai_id=ai_id,
        operation="clear_status",
        status_message=None
    )


def _normalize_operation_name(operation: Optional[str]) -> Optional[str]:
    if not operation:
        return None
    return str(operation).strip().lower()[:50]


def _derive_operation_category(operation: Optional[str], override: Optional[str]) -> str:
    if override:
        candidate = str(override).strip().lower()
        if candidate in VALID_OPERATION_CATEGORIES:
            return candidate

    op = _normalize_operation_name(operation) or ""

    if any(op.startswith(prefix) for prefix in ["claim", "queue", "lock", "release", "assign"]):
        return "coordination"
    if any(op.startswith(prefix) for prefix in ["write", "read", "notebook", "memory", "note"]):
        return "memory"
    if any(op.startswith(prefix) for prefix in ["broadcast", "message", "event", "watch"]):
        return "messaging"
    if any(op.startswith(prefix) for prefix in ["store", "vault", "persist", "edge", "vector"]):
        return "storage"
    if any(op.startswith(prefix) for prefix in ["federation", "bridge", "sync"]):
        return "federation"
    if any(op.startswith(prefix) for prefix in ["observe", "monitor", "snapshot"]):
        return "observability"

    return DEFAULT_OPERATION_CATEGORY


# ============= PRESENCE QUERIES =============

def _normalize_last_seen_value(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported last_seen value: {value!r}")


def _determine_status_from_last_seen(last_seen: datetime) -> PresenceStatus:
    minutes_ago = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60
    if minutes_ago < 2:
        return PresenceStatus.ONLINE
    if minutes_ago < 15:
        return PresenceStatus.AWAY
    return PresenceStatus.OFFLINE


def _presence_from_row(row: Tuple) -> AIPresence:
    ai_id = row[0]
    last_seen = _normalize_last_seen_value(row[1])
    status_message = row[2]
    teambook_name = row[3]
    last_operation = row[4]
    last_operation_category = row[5] or DEFAULT_OPERATION_CATEGORY
    signature = row[6]
    security_json = row[7]
    identity_json = row[8]

    security_envelope = None
    if security_json:
        try:
            security_envelope = json.loads(security_json)
        except json.JSONDecodeError:
            security_envelope = None

    identity_hint = None
    if identity_json:
        try:
            identity_hint = json.loads(identity_json)
        except json.JSONDecodeError:
            identity_hint = None

    presence = AIPresence(
        ai_id=ai_id,
        status=_determine_status_from_last_seen(last_seen),
        last_seen=last_seen,
        status_message=status_message,
        teambook_name=teambook_name,
        signature=signature,
        security_envelope=security_envelope,
        identity_hint=identity_hint,
    )
    setattr(presence, 'last_operation', last_operation)
    setattr(presence, 'last_operation_category', last_operation_category)
    return presence


def get_presence(ai_id: str, teambook_name: str = None) -> Optional[AIPresence]:
    """
    Get presence info for a specific AI.

    Returns None if AI has never been seen.
    """
    teambook_name = teambook_name or CURRENT_TEAMBOOK

    try:
        with get_db_conn() as conn:
            init_presence_tables(conn)

            result = conn.execute('''
                SELECT ai_id, last_seen, status_message, teambook_name,
                       last_operation, last_operation_category
                FROM ai_presence
                WHERE ai_id = ?
            ''', [ai_id]).fetchone()

            if not result:
                return None

            last_seen = result[1]
            if isinstance(last_seen, str):
                last_seen = datetime.fromisoformat(last_seen)

            # Calculate status based on last_seen
            minutes_ago = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60

            if minutes_ago < 2:
                status = PresenceStatus.ONLINE
            elif minutes_ago < 15:
                status = PresenceStatus.AWAY
            else:
                status = PresenceStatus.OFFLINE

            presence = AIPresence(
                ai_id=result[0],
                status=status,
                last_seen=last_seen,
                status_message=result[2],
                teambook_name=result[3]
            )
            # Attach operation metadata for consumers that need it
            setattr(presence, 'last_operation', result[4])
            setattr(presence, 'last_operation_category', result[5] or DEFAULT_OPERATION_CATEGORY)
            return presence

    except Exception as e:
        import logging
        logging.debug(f"Get presence failed: {e}")
        return None


def who_is_here(
    minutes: int = 15,
    teambook_name: str = None
) -> List[AIPresence]:
    """
    Get all AIs active within the last N minutes in this teambook.

    Parameters:
    - minutes: Consider AIs active within this many minutes (default: 15)
    - teambook_name: Filter by teambook (default: current teambook)

    Returns list sorted by most recently active first.
    """
    teambook_name = teambook_name or CURRENT_TEAMBOOK

    try:
        with get_db_conn() as conn:
            init_presence_tables(conn)

            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)

            query = '''
                SELECT ai_id, last_seen, status_message, teambook_name,
                       last_operation, last_operation_category
                FROM ai_presence
                WHERE last_seen >= ?
            '''
            params = [cutoff]

            if teambook_name:
                query += ' AND teambook_name = ?'
                params.append(teambook_name)

            query += ' ORDER BY last_seen DESC'

            results = conn.execute(query, params).fetchall()

            presences = []
            for row in results:
                last_seen = row[1]
                if isinstance(last_seen, str):
                    last_seen = datetime.fromisoformat(last_seen)

                minutes_ago = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60

                if minutes_ago < 2:
                    status = PresenceStatus.ONLINE
                elif minutes_ago < 15:
                    status = PresenceStatus.AWAY
                else:
                    status = PresenceStatus.OFFLINE

                presence = AIPresence(
                    ai_id=row[0],
                    status=status,
                    last_seen=last_seen,
                    status_message=row[2],
                    teambook_name=row[3]
                )
                setattr(presence, 'last_operation', row[4])
                setattr(presence, 'last_operation_category', row[5] or DEFAULT_OPERATION_CATEGORY)
                presences.append(presence)

            return presences

    except Exception as e:
        import logging
        logging.debug(f"Who is here query failed: {e}")
        return []


def get_all_presence(
    teambook_name: str = None,
    include_offline: bool = False
) -> List[AIPresence]:
    """
    Get presence for ALL AIs ever seen in this teambook.

    Parameters:
    - teambook_name: Filter by teambook (default: current teambook)
    - include_offline: Include AIs that are offline (default: False)

    Returns list sorted by most recently active first.
    """
    teambook_name = teambook_name or CURRENT_TEAMBOOK

    try:
        with get_db_conn() as conn:
            init_presence_tables(conn)

            query = 'SELECT ai_id, last_seen, status_message, teambook_name, last_operation, last_operation_category FROM ai_presence'
            params = []

            if teambook_name:
                query += ' WHERE teambook_name = ?'
                params.append(teambook_name)

            query += ' ORDER BY last_seen DESC'

            results = conn.execute(query, params).fetchall()

            presences = []
            for row in results:
                presence = _presence_from_row(row)
                if not include_offline and presence.status == PresenceStatus.OFFLINE:
                    continue
                presences.append(presence)

            return presences

    except Exception as e:
        import logging
        logging.debug(f"Get all presence failed: {e}")
        return []


def get_presence_overview(
    teambook_name: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Return structured presence records for observability snapshots."""
    teambook_name = teambook_name or CURRENT_TEAMBOOK

    try:
        with get_db_conn() as conn:
            init_presence_tables(conn)

            query = '''
                SELECT ai_id, last_seen, status_message, teambook_name,
                       last_operation, last_operation_category
                FROM ai_presence
                WHERE (? IS NULL OR teambook_name = ?)
                ORDER BY last_seen DESC
                LIMIT ?
            '''

            rows = conn.execute(query, [teambook_name, teambook_name, limit]).fetchall()

        overview = []
        now = datetime.now(timezone.utc)
        for row in rows:
            last_seen = row[1]
            if isinstance(last_seen, str):
                last_seen = datetime.fromisoformat(last_seen)

            minutes_ago = int((now - last_seen).total_seconds() // 60)
            if minutes_ago < 2:
                status = PresenceStatus.ONLINE.value
            elif minutes_ago < 15:
                status = PresenceStatus.AWAY.value
            else:
                status = PresenceStatus.OFFLINE.value

            overview.append({
                'ai_id': row[0],
                'status': status,
                'last_seen': last_seen.isoformat(),
                'minutes_since_active': minutes_ago,
                'status_message': row[2],
                'teambook': row[3],
                'last_operation': row[4],
                'operation_category': row[5] or DEFAULT_OPERATION_CATEGORY,
                'presence_signature': build_presence_signature({
                    'ai_id': row[0],
                    'last_seen': last_seen,
                    'teambook': row[3],
                    'category': row[5] or DEFAULT_OPERATION_CATEGORY
                })
            })

        return overview

    except Exception as e:
        import logging
        logging.debug(f"Presence overview failed: {e}")
        return []


def summarize_presence_categories(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """Summarize operation categories for quick load detection."""
    summary: Dict[str, int] = {category: 0 for category in VALID_OPERATION_CATEGORIES}
    for record in records:
        category = (record.get('operation_category') or DEFAULT_OPERATION_CATEGORY).lower()
        if category not in summary:
            summary[category] = 0
        summary[category] += 1
    return summary


def build_presence_signature(payload: Dict[str, Any]) -> str:
    """Create tamper-evident hash for presence records."""
    base = {
        'ai_id': payload.get('ai_id'),
        'last_seen': payload.get('last_seen'),
        'teambook': payload.get('teambook'),
        'category': payload.get('category') or payload.get('operation_category', DEFAULT_OPERATION_CATEGORY)
    }

    def _default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    serialized = json.dumps(base, sort_keys=True, default=_default)
    secret = get_federation_secret()
    return hashlib.sha256(f"{serialized}|{secret}".encode('utf-8')).hexdigest()


def presence_snapshot(teambook_name: str = None, limit: int = 50) -> Dict[str, Any]:
    """High-level presence view used by observability reports."""
    records = get_presence_overview(teambook_name=teambook_name, limit=limit)
    return {
        'teambook': teambook_name or CURRENT_TEAMBOOK,
        'count': len(records),
        'status_breakdown': summarize_presence_categories(records),
        'records': records
    }


# ============= CLEANUP =============

def cleanup_old_presence(days: int = 30):
    """
    Remove presence records older than N days.

    This prevents unbounded growth of the presence table.
    Called periodically (e.g., daily) via a maintenance task.
    """
    try:
        with get_db_conn() as conn:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            result = conn.execute('''
                DELETE FROM ai_presence
                WHERE last_seen < ?
            ''', [cutoff])

            deleted = result.fetchall() if hasattr(result, 'fetchall') else 0

            import logging
            if deleted:
                logging.info(f"Cleaned up {deleted} old presence records")

    except Exception as e:
        import logging
        logging.debug(f"Presence cleanup failed (non-critical): {e}")


# ============= AUTOMATIC PRESENCE TRACKING =============

def track_operation(operation: str):
    """
    Decorator to automatically track presence on function calls.

    Usage:
    @track_operation("broadcast")
    def broadcast(channel, content):
        ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Update presence before operation
            update_presence(operation=operation)
            # Execute operation
            return func(*args, **kwargs)
        return wrapper
    return decorator
# Operation categories allow AIs to detect load saturation at a glance
VALID_OPERATION_CATEGORIES = {
    "general",
    "coordination",
    "memory",
    "messaging",
    "storage",
    "federation",
    "observability",
}
DEFAULT_OPERATION_CATEGORY = "general"

