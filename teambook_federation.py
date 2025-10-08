#!/usr/bin/env python3
"""
TEAMBOOK FEDERATION BRIDGE v1.0.0
=================================
Redis-stream-based synchronization channel for multi-device Town Halls.

This bridge composes presence, coordination, and observability data into
tamper-evident payloads that remote swarms can consume safely.
"""

from __future__ import annotations

import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from teambook_shared import (
    CURRENT_AI_ID,
    CURRENT_TEAMBOOK,
    get_federation_secret,
)
from teambook_presence import (
    get_presence_overview,
    summarize_presence_categories,
    build_presence_signature,
)
from teambook_storage import get_db_conn
from teambook_events import init_events_tables
from teambook_coordination import get_coordination_backend, init_coordination_tables

try:
    from redis_pool import get_connection

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


logger = logging.getLogger(__name__)
STREAM_PREFIX = "teambook:federation"


def _collect_coordination_state(teambook_name: str) -> Dict[str, Any]:
    backend_type, get_conn = get_coordination_backend()

    try:
        with get_conn() as conn:
            init_coordination_tables(conn)

            stats = conn.execute(
                '''
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN status = 'claimed' THEN 1 END) as claimed,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN claimed_by = ? THEN 1 END) as owned
                FROM task_queue
                WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                ''',
                [CURRENT_AI_ID, teambook_name, teambook_name],
            ).fetchone()

            by_priority = conn.execute(
                '''
                SELECT priority, COUNT(*)
                FROM task_queue
                WHERE status = 'pending'
                  AND (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                GROUP BY priority
                ORDER BY priority DESC
                LIMIT 5
                ''',
                [teambook_name, teambook_name],
            ).fetchall()

        priority_hotspots = {str(row[0]): row[1] for row in by_priority}

        return {
            'backend': backend_type,
            'total': stats[0] if stats else 0,
            'pending': stats[1] if stats else 0,
            'claimed': stats[2] if stats else 0,
            'completed': stats[3] if stats else 0,
            'owned_by_caller': stats[4] if stats else 0,
            'priority_hotspots': priority_hotspots,
        }

    except Exception as exc:  # Defensive: coordination backend may be offline
        logger.debug(f"Coordination snapshot failed: {exc}")
        return {
            'backend': backend_type,
            'error': 'coordination_snapshot_failed',
        }


def _collect_event_state(teambook_name: str) -> Dict[str, Any]:
    try:
        with get_db_conn() as conn:
            init_events_tables(conn)

            unseen = conn.execute(
                '''
                SELECT COUNT(*)
                FROM event_deliveries d
                JOIN events e ON e.id = d.event_id
                WHERE d.seen = FALSE AND (? IS NULL OR e.teambook_name = ? OR e.teambook_name IS NULL)
                ''',
                [teambook_name, teambook_name],
            ).fetchone()[0]

            recent_events = conn.execute(
                '''
                SELECT item_type, event_type, actor_ai_id, created_at
                FROM events
                WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                ORDER BY created_at DESC
                LIMIT 10
                ''',
                [teambook_name, teambook_name],
            ).fetchall()

            watches = conn.execute(
                '''
                SELECT item_type, COUNT(*), MAX(last_activity)
                FROM watches
                WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                GROUP BY item_type
                ORDER BY MAX(last_activity) DESC
                LIMIT 10
                ''',
                [teambook_name, teambook_name],
            ).fetchall()

        return {
            'unseen_events': unseen,
            'recent_events': [
                {
                    'item_type': row[0],
                    'event_type': row[1],
                    'actor': row[2],
                    'created_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3]),
                }
                for row in recent_events
            ],
            'watch_focus': [
                {
                    'item_type': row[0],
                    'watchers': row[1],
                    'last_activity': row[2].isoformat() if row[2] else None,
                }
                for row in watches
            ],
        }

    except Exception as exc:
        logger.debug(f"Event snapshot failed: {exc}")
        return {'error': 'event_snapshot_failed'}


def _compose_payload(teambook_name: str, include_events: bool = True) -> Dict[str, Any]:
    presence_records = get_presence_overview(teambook_name=teambook_name, limit=100)
    presence_summary = summarize_presence_categories(presence_records)

    payload: Dict[str, Any] = {
        'teambook': teambook_name,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'publisher': CURRENT_AI_ID,
        'presence': {
            'records': presence_records,
            'category_summary': presence_summary,
        },
        'coordination': _collect_coordination_state(teambook_name),
    }

    if include_events:
        payload['events'] = _collect_event_state(teambook_name)

    secret = get_federation_secret()
    serialized = json.dumps(payload, sort_keys=True, default=str)
    payload['signature'] = hashlib.sha256(f"{serialized}|{secret}".encode('utf-8')).hexdigest()

    # Also attach per-record signatures for downstream validation
    for record in payload['presence']['records']:
        record['presence_signature'] = build_presence_signature(record)

    return payload


def teambook_federation_bridge(
    mode: str = 'publish',
    teambook_name: Optional[str] = None,
    since: Optional[str] = None,
    batch_size: int = 50,
    include_events: bool = True,
) -> Any:
    """Synchronize observability state across Teambook instances."""

    teambook_name = teambook_name or CURRENT_TEAMBOOK
    if not teambook_name:
        return {"error": "teambook_context_required"}

    if not REDIS_AVAILABLE:
        if mode == 'publish':
            return {"error": "redis_not_available"}
        # For consumers we still allow local payload generation for debugging
        if mode == 'generate':
            return _compose_payload(teambook_name, include_events=include_events)
        return {"error": "redis_not_available"}

    stream_key = f"{STREAM_PREFIX}:{teambook_name}"
    redis_conn = get_connection()

    if mode == 'publish':
        payload = _compose_payload(teambook_name, include_events=include_events)
        entry_id = redis_conn.xadd(stream_key, {
            'payload': json.dumps(payload, separators=(',', ':'), sort_keys=True),
            'signature': payload['signature'],
        })
        return f"published:{entry_id}"

    if mode == 'generate':
        return _compose_payload(teambook_name, include_events=include_events)

    if mode == 'consume':
        count = max(1, min(int(batch_size or 1), 200))
        start = since or '0-0'
        entries = redis_conn.xread({stream_key: start}, count=count, block=2000)

        if not entries:
            return ""

        secret = get_federation_secret()
        lines: List[str] = []
        for _, messages in entries:
            for entry_id, data in messages:
                payload_raw = data.get('payload')
                signature = data.get('signature')
                status = 'invalid'
                try:
                    computed = hashlib.sha256(f"{payload_raw}|{secret}".encode('utf-8')).hexdigest()
                    status = 'ok' if computed == signature else 'signature_mismatch'
                    payload = json.loads(payload_raw)
                    lines.append(
                        f"{entry_id}|{status}|teambook:{payload.get('teambook')}|publisher:{payload.get('publisher')}"
                    )
                except Exception as exc:
                    logger.debug(f"Failed to parse federation payload: {exc}")
                    lines.append(f"{entry_id}|error|parse_failed")

        return '\n'.join(lines)

    return {"error": f"unknown_mode:{mode}"}

