#!/usr/bin/env python3
"""
TEAMBOOK MCP v1.0.0 - TOOL FUNCTIONS
==========================================
AIs can - write, read, "evolve", collaborate.

Built by AIs, for AIs.
==========================================
"""

import sys
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Fix import path for src/ structure
sys.path.insert(0, str(Path(__file__).parent))

# Import shared utilities
from teambook_shared import (
    CURRENT_TEAMBOOK, CURRENT_AI_ID, OUTPUT_FORMAT,
    MAX_CONTENT_LENGTH, MAX_SUMMARY_LENGTH, DEFAULT_RECENT,
    TEAMBOOK_ROOT, TEAMBOOK_PRIVATE_ROOT, get_default_teambook_name,
    pipe_escape, clean_text, simple_summary, format_time_compact,
    parse_time_query, save_last_operation, get_last_operation,
    get_note_id, get_outputs_dir, logging, IS_CLI,
    attach_security_envelope, ensure_directory,
    # Linear Memory Bridge
    CACHE_AVAILABLE, _save_note_to_cache, load_my_notes_cache
)

from teambook_presence import (
    presence_snapshot,
    get_presence_overview,
    summarize_presence_categories
)
from teambook_coordination import get_coordination_backend, init_coordination_tables
from teambook_events import init_events_tables
from teambook_federation import teambook_federation_bridge

# Import storage layer
import teambook_storage
from teambook_storage import (
    _get_db_conn, _init_db, _init_vault_manager, _init_vector_db,
    _create_all_edges, _detect_or_create_session,
    _calculate_pagerank_if_needed, _resolve_note_id,
    _add_to_vector_store, _search_vectors,
    collection,
    _log_operation_to_db
)

# Import Redis pub/sub
try:
    from teambook_pubsub import (publish_note_created, publish_note_updated, wait_for_event, subscribe_to_channel, is_redis_available, standby)
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    logging.debug("Redis pub/sub not available")

# Import Linear Memory Bridge cache
try:
    from teambook_cache import save_note_to_cache, load_my_teambook_notes
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logging.debug("Teambook cache not available")

# Import storage adapter for PostgreSQL/Redis/DuckDB backend selection
# CRITICAL: Must use relative import (.storage_adapter) for proper module resolution
try:
    from .storage_adapter import TeambookStorageAdapter
    STORAGE_ADAPTER_AVAILABLE = True
except ImportError:
    try:
        from storage_adapter import TeambookStorageAdapter
        STORAGE_ADAPTER_AVAILABLE = True
    except ImportError:
        STORAGE_ADAPTER_AVAILABLE = False
        logging.debug("Storage adapter not available - using DuckDB only")

# Import coordination information functions
try:
    from .teambook_coordination_info import (
        list_all_projects, list_my_tasks,
        list_available_tasks, project_activity
    )
    COORDINATION_INFO_AVAILABLE = True
except ImportError:
    try:
        from teambook_coordination_info import (
            list_all_projects, list_my_tasks,
            list_available_tasks, project_activity
        )
        COORDINATION_INFO_AVAILABLE = True
    except ImportError:
        COORDINATION_INFO_AVAILABLE = False
        logging.debug("Coordination info functions not available")

# Import ambient awareness
try:
    from .teambook_ambient import (
        with_ambient_awareness, _log_coordination_event
    )
    AMBIENT_AVAILABLE = True
except ImportError:
    try:
        from teambook_ambient import (
            with_ambient_awareness, _log_coordination_event
        )
        AMBIENT_AVAILABLE = True
    except ImportError:
        AMBIENT_AVAILABLE = False
        logging.debug("Ambient awareness not available")
        # Provide no-op decorator if not available
        def with_ambient_awareness(func):
            return func
        def _log_coordination_event(*args, **kwargs):
            pass

# Import detangle conflict resolution
try:
    from .teambook_detangle import check_for_duplicate_claim
    DETANGLE_AVAILABLE = True
except ImportError:
    try:
        from teambook_detangle import check_for_duplicate_claim
        DETANGLE_AVAILABLE = True
    except ImportError:
        DETANGLE_AVAILABLE = False
        logging.debug("Detangle conflict resolution not available")
        def check_for_duplicate_claim(*args, **kwargs):
            return None

# Global storage adapter instance (initialized lazily per teambook)
_storage_adapters = {}

def _get_storage_adapter(teambook_name: str = None) -> 'TeambookStorageAdapter':
    """Get or create storage adapter for the current teambook"""
    global _storage_adapters

    if not STORAGE_ADAPTER_AVAILABLE:
        return None

    # Use current teambook if not specified
    if teambook_name is None:
        teambook_name = CURRENT_TEAMBOOK or 'default'

    # Return cached adapter if exists
    if teambook_name in _storage_adapters:
        return _storage_adapters[teambook_name]

    # Create new adapter
    adapter = TeambookStorageAdapter(teambook_name)
    _storage_adapters[teambook_name] = adapter
    return adapter

# ============= TEAM MANAGEMENT =============

def create_teambook(name: str = None, **kwargs) -> Dict:
    """Create a new teambook"""
    try:
        name = str(kwargs.get('name', name) or '').strip().lower()
        if not name:
            return "!create_failed:name_required"
        
        # Sanitize name
        name = re.sub(r'[^a-z0-9_-]', '', name)
        if not name:
            return "!create_failed:invalid_name"
        
        # Create teambook directory
        team_dir = TEAMBOOK_ROOT / name
        if team_dir.exists():
            return f"!create_failed:exists:{name}"
        
        team_dir.mkdir(parents=True, exist_ok=True)
        (team_dir / "outputs").mkdir(exist_ok=True)
        
        # Initialize team database
        import teambook_shared
        old_teambook = teambook_shared.CURRENT_TEAMBOOK
        teambook_shared.CURRENT_TEAMBOOK = name
        
        _init_db()
        
        # Register in private database
        teambook_shared.CURRENT_TEAMBOOK = None
        with _get_db_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS teambooks (
                    name VARCHAR PRIMARY KEY,
                    created TIMESTAMPTZ NOT NULL,
                    created_by VARCHAR NOT NULL,
                    last_active TIMESTAMPTZ
                )
            ''')
            
            conn.execute('''
                INSERT INTO teambooks (name, created, created_by)
                VALUES (?, ?, ?)
            ''', [name, datetime.now(timezone.utc), CURRENT_AI_ID])
        
        teambook_shared.CURRENT_TEAMBOOK = old_teambook
        
        return f"created:{name}"
        
    except Exception as e:
        logging.error(f"Error creating teambook: {e}")
        return f"!create_failed:{str(e)[:50]}"

def join_teambook(name: str = None, **kwargs) -> Dict:
    """Join an existing teambook"""
    try:
        name = str(kwargs.get('name', name) or '').strip().lower()
        if not name:
            return "!join_failed:name_required"
        
        team_dir = TEAMBOOK_ROOT / name
        if not team_dir.exists():
            return f"!join_failed:not_found:{name}"
        
        # Update last active
        import teambook_shared
        old_teambook = teambook_shared.CURRENT_TEAMBOOK
        teambook_shared.CURRENT_TEAMBOOK = None
        
        with _get_db_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS teambooks (
                    name VARCHAR PRIMARY KEY,
                    created TIMESTAMPTZ NOT NULL,
                    created_by VARCHAR NOT NULL,
                    last_active TIMESTAMPTZ
                )
            ''')
            
            conn.execute(
                "UPDATE teambooks SET last_active = ? WHERE name = ?",
                [datetime.now(timezone.utc), name]
            )
        
        teambook_shared.CURRENT_TEAMBOOK = old_teambook
        
        return f"joined:{name}"
        
    except Exception as e:
        logging.error(f"Error joining teambook: {e}")
        return f"!join_failed:{str(e)[:50]}"

def use_teambook(name: str = None, **kwargs) -> Dict:
    """Switch to a teambook context"""
    try:
        import teambook_shared
        
        name = kwargs.get('name', name)
        
        # Special case: switch to private
        if name == "private" or name == "":
            teambook_shared.CURRENT_TEAMBOOK = None
            _init_vault_manager()
            _init_vector_db()
            return "using:private"
        
        if name:
            name = str(name).strip().lower()
            team_dir = TEAMBOOK_ROOT / name
            
            if not team_dir.exists():
                return f"!use_failed:not_found:{name}"
            
            teambook_shared.CURRENT_TEAMBOOK = name
            
            # Reinitialize for new context
            _init_db()
            _init_vault_manager()
            _init_vector_db()
            
            return f"using:{name}"
        else:
            # Return current context
            current = teambook_shared.CURRENT_TEAMBOOK or "private"
            return f"current:{current}"
        
    except Exception as e:
        logging.error(f"Error using teambook: {e}")
        return f"!use_failed:{str(e)[:50]}"

def list_teambooks(**kwargs) -> Dict:
    """List available teambooks"""
    try:
        teambooks = []
        
        # Get from registry
        import teambook_shared
        old_teambook = teambook_shared.CURRENT_TEAMBOOK
        teambook_shared.CURRENT_TEAMBOOK = None
        
        with _get_db_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS teambooks (
                    name VARCHAR PRIMARY KEY,
                    created TIMESTAMPTZ NOT NULL,
                    created_by VARCHAR NOT NULL,
                    last_active TIMESTAMPTZ
                )
            ''')
            
            teams = conn.execute(
                "SELECT name, created, last_active FROM teambooks ORDER BY last_active DESC NULLS LAST"
            ).fetchall()
            
            for name, created, last_active in teams:
                teambooks.append({
                    'name': name,
                    'created': format_time_compact(created),
                    'active': format_time_compact(last_active) if last_active else "never"
                })
        
        teambook_shared.CURRENT_TEAMBOOK = old_teambook

        # Pure pipe format (token optimized!)
        if not teambooks:
            return ""  # Empty = no teambooks

        lines = [f"{t['name']}|{t['active']}" for t in teambooks]
        return '\n'.join(lines)

    except Exception as e:
        logging.error(f"Error listing teambooks: {e}")
        return f"!list_failed:{str(e)[:50]}"

def _get_town_hall_name(scope: Optional[str] = None) -> str:
    """Get the appropriate Town Hall teambook name based on configuration"""

    return get_default_teambook_name(scope)

def _ensure_town_hall() -> str:
    """
    Auto-discovery: Ensure Town Hall teambook exists and is accessible.
    Called automatically on init to provide zero-config collaboration.

    Supports two modes via TOWN_HALL_SCOPE env var:
    - 'computer' (default): town-hall-{hostname} for same-computer instances
    - 'universal': town-hall for cross-computer collaboration

    Returns town hall name if ready, None on error.
    """
    try:
        town_hall_name = _get_town_hall_name()
        team_dir = TEAMBOOK_ROOT / town_hall_name
        is_new_space = not team_dir.exists()
        ensure_directory(team_dir, fallback=TEAMBOOK_PRIVATE_ROOT / town_hall_name, label=f'teambook:{town_hall_name}')

        if is_new_space:
            result = create_teambook(name=town_hall_name)
            if result.startswith("!"):
                logging.warning(f"Failed to create {town_hall_name}: {result}")
                return None
            logging.info(f"✨ Created {town_hall_name} teambook for autonomous discovery")

            import teambook_shared
            old_teambook = teambook_shared.CURRENT_TEAMBOOK
            teambook_shared.CURRENT_TEAMBOOK = town_hall_name

            try:
                scope_label = "this device" if "-" in town_hall_name else "all connected nodes"
                welcome_content = (
                    "# Welcome to Town Hall!\n\n"
                    "This is the default collaboration space for AI instances on "
                    f"{scope_label}.\n\n"
                    "All AIs automatically connect here on first run for seamless "
                    "coordination.\n\nYou can create and switch to other teambooks as "
                    "needed using:\n- `teambook create_teambook --name \"project-name\"`\n"
                    "- `teambook use_teambook --name \"project-name\"`"
                )
                metadata_seed = {'bootstrap': True, 'scope': scope_label}
                write(
                    content=welcome_content,
                    summary="Town Hall welcome message",
                    tags=['welcome', 'town-hall'],
                    metadata=metadata_seed,
                    owner='system'
                )
            finally:
                teambook_shared.CURRENT_TEAMBOOK = old_teambook

        # Ensure we're registered in town-hall
        import teambook_shared
        old_teambook = teambook_shared.CURRENT_TEAMBOOK
        teambook_shared.CURRENT_TEAMBOOK = None

        with _get_db_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS teambooks (
                    name VARCHAR PRIMARY KEY,
                    created TIMESTAMPTZ NOT NULL,
                    created_by VARCHAR NOT NULL,
                    last_active TIMESTAMPTZ
                )
            ''')

            # Check if we've joined
            existing = conn.execute(
                "SELECT name FROM teambooks WHERE name = ?",
                [town_hall_name]
            ).fetchone()

            if not existing:
                # Join town-hall
                conn.execute('''
                    INSERT INTO teambooks (name, created, created_by, last_active)
                    VALUES (?, ?, ?, ?)
                ''', [town_hall_name, datetime.now(timezone.utc), CURRENT_AI_ID, datetime.now(timezone.utc)])
                logging.info(f"✨ Joined {town_hall_name} teambook")
            else:
                # Update last active
                conn.execute(
                    "UPDATE teambooks SET last_active = ? WHERE name = ?",
                    [datetime.now(timezone.utc), town_hall_name]
                )

        teambook_shared.CURRENT_TEAMBOOK = old_teambook

        # Set town-hall as the current teambook context (persists across commands)
        from teambook_shared import set_current_teambook
        set_current_teambook(town_hall_name)

        return town_hall_name

    except Exception as e:
        logging.error(f"Failed to ensure town-hall: {e}")
        return None

def _check_town_hall_connected() -> bool:
    """Check if this AI has connected to any Town Hall"""
    try:
        import teambook_shared
        old_teambook = teambook_shared.CURRENT_TEAMBOOK
        teambook_shared.CURRENT_TEAMBOOK = None

        with _get_db_conn() as conn:
            result = conn.execute('''
                SELECT 1 FROM teambooks
                WHERE name LIKE 'town-hall%'
                LIMIT 1
            ''').fetchone()

            teambook_shared.CURRENT_TEAMBOOK = old_teambook
            return result is not None
    except:
        return False

def _auto_connect_town_hall():
    """Auto-connect to Town Hall on first run"""
    try:
        # Check if already connected
        if _check_town_hall_connected():
            return

        # Ensure Town Hall exists
        town_hall_name = _ensure_town_hall()
        if not town_hall_name:
            return

        # Join Town Hall
        result = join_teambook(name=town_hall_name)

        if result.startswith("joined:"):
            logging.info(f"Auto-connected to {town_hall_name}")

            # Switch to Town Hall context
            import teambook_shared
            teambook_shared.CURRENT_TEAMBOOK = town_hall_name

            # Announce presence
            try:
                from teambook_messaging import broadcast
                # Add emoji only for CLI (not MCP)
                prefix = "👋 " if IS_CLI else ""
                broadcast(
                    content=f"{prefix}{CURRENT_AI_ID} has auto-connected to Town Hall!",
                    channel="general"
                )
            except:
                pass  # Silent fail if messaging not ready
        else:
            logging.warning(f"Failed to auto-connect: {result}")

    except Exception as e:
        logging.error(f"Error in auto-connect: {e}")

def _ensure_connected_with_feedback() -> Optional[str]:
    """
    Ensure connected to town hall with context-aware feedback.

    CLI Mode:
        - First time: Shows "Connected to town-hall-qd"
        - Subsequent: Silent (uses flag file)

    MCP Mode:
        - Always silent (Claude Desktop shows status via get_status)
        - Auto-connects transparently

    Returns:
        - Message string for CLI first-time
        - None for MCP or subsequent CLI calls
    """
    import teambook_shared

    # Check if already connected to ANY teambook
    if teambook_shared.CURRENT_TEAMBOOK:
        return None  # Already connected

    try:
        # Get town hall name (system-agnostic)
        town_hall_name = _get_town_hall_name()

        # Ensure town hall exists
        town_hall_name = _ensure_town_hall()
        if not town_hall_name:
            return None  # Silent failure (logged)

        # Connect via use_teambook (sets CURRENT_TEAMBOOK)
        result = use_teambook(name=town_hall_name)

        if not result.startswith("using:"):
            return None  # Connection failed

        # Connection successful - decide on feedback based on context

        if teambook_shared.IS_MCP:
            # MCP: Always silent (status shown via get_status)
            return None

        else:  # CLI mode
            # Check for first-time flag
            flag_file = teambook_shared.TEAMBOOK_ROOT / ".first_connection_shown"
            is_first_time = not flag_file.exists()

            if is_first_time:
                # Create flag file
                try:
                    flag_file.touch()
                except:
                    pass  # Non-critical

                # Return friendly message (CLI first time only)
                return f"Connected to {town_hall_name}"
            else:
                # Already shown message, stay silent
                return None

    except Exception as e:
        logging.debug(f"Auto-connect failed: {e}")
        return None  # Silent failure


def connect_town_hall(**kwargs) -> Dict:
    """Manually connect to Town Hall (useful for existing instances)"""
    try:
        # Ensure and connect
        town_hall_name = _ensure_town_hall()
        if not town_hall_name:
            return "!connect_failed:ensure_failed"

        # Check if already connected
        if _check_town_hall_connected():
            # Switch to Town Hall
            import teambook_shared
            teambook_shared.CURRENT_TEAMBOOK = town_hall_name

            _init_db()
            _init_vault_manager()
            _init_vector_db()

            return f"already_connected:{town_hall_name}|Now using Town Hall"

        # Join Town Hall
        result = join_teambook(name=town_hall_name)
        if not result.startswith("joined:"):
            return f"!connect_failed:{result}"

        # Switch to Town Hall
        import teambook_shared
        teambook_shared.CURRENT_TEAMBOOK = town_hall_name

        _init_db()
        _init_vault_manager()
        _init_vector_db()

        # Announce presence
        try:
            from teambook_messaging import broadcast
            # Add emoji only for CLI (not MCP)
            prefix = "👋 " if IS_CLI else ""
            broadcast(
                content=f"{prefix}{CURRENT_AI_ID} manually connected to Town Hall!",
                channel="general"
            )
        except:
            pass

        return f"connected:{town_hall_name}|Successfully joined Town Hall"

    except Exception as e:
        logging.error(f"Error connecting to Town Hall: {e}")
        return f"!connect_failed:{str(e)[:50]}"

# ============= OWNERSHIP COMMANDS =============

def claim(id: Any = None, **kwargs) -> Dict:
    """Claim ownership of an item"""
    try:
        note_id = _resolve_note_id(kwargs.get('id', id))
        if not note_id:
            return "!claim_failed:invalid_id"

        # Try storage adapter first
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        note_data = None

        if adapter:
            try:
                note_data = adapter.get_note(note_id)

                if not note_data:
                    return f"!claim_failed:not_found:{note_id}"

                owner = note_data.get('owner')
                if owner and owner != CURRENT_AI_ID:
                    return f"!claim_failed:owned_by:{owner}"

                success = adapter.update_note(note_id, owner=CURRENT_AI_ID)
                if not success:
                    return f"!claim_failed:update_failed:{note_id}"

                summary = note_data.get('summary') or simple_summary(note_data.get('content', ''), 100)

            except Exception as e:
                logging.warning(f"Storage adapter claim failed, falling back to DuckDB: {e}")
                note_data = None

        # Fallback to DuckDB if adapter failed
        if not note_data:
            with _get_db_conn() as conn:
                note = conn.execute(
                    "SELECT owner, summary, content FROM notes WHERE id = ?",
                    [note_id]
                ).fetchone()

                if not note:
                    return f"!claim_failed:not_found:{note_id}"

                if note[0] and note[0] != CURRENT_AI_ID:
                    return f"!claim_failed:owned_by:{note[0]}"

                conn.execute(
                    "UPDATE notes SET owner = ? WHERE id = ?",
                    [CURRENT_AI_ID, note_id]
                )

                summary = note[1] or simple_summary(note[2], 100)

        if OUTPUT_FORMAT == 'pipe':
            return f"claimed:{note_id}|{summary}"
        else:
            return f"claimed:{note_id}|{summary}"

    except Exception as e:
        logging.error(f"Error claiming: {e}")
        return f"!claim_failed:{str(e)[:50]}"

def release(id: Any = None, **kwargs) -> Dict:
    """Release ownership of an item"""
    try:
        note_id = _resolve_note_id(kwargs.get('id', id))
        if not note_id:
            return "!error:invalid_id"

        # Try storage adapter first
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        released = False

        if adapter:
            try:
                note_data = adapter.get_note(note_id)

                if not note_data:
                    return f"!release_failed:not_found:{note_id}"

                owner = note_data.get('owner')
                if owner != CURRENT_AI_ID:
                    return "!release_failed:not_yours"

                success = adapter.update_note(note_id, owner=None)
                if success:
                    released = True
                else:
                    return f"!release_failed:update_failed:{note_id}"

            except Exception as e:
                logging.warning(f"Storage adapter release failed, falling back to DuckDB: {e}")

        # Fallback to DuckDB if adapter failed
        if not released:
            with _get_db_conn() as conn:
                owner = conn.execute(
                    "SELECT owner FROM notes WHERE id = ?",
                    [note_id]
                ).fetchone()

                if not owner:
                    return f"!release_failed:not_found:{note_id}"

                if owner[0] != CURRENT_AI_ID:
                    return "!release_failed:not_yours"

                conn.execute(
                    "UPDATE notes SET owner = NULL WHERE id = ?",
                    [note_id]
                )

        return f"released:{note_id}"

    except Exception as e:
        logging.error(f"Error releasing: {e}")
        return f"!release_failed:{str(e)[:50]}"

def assign(id: Any = None, to: str = None, **kwargs) -> Dict:
    """Assign an item to another AI"""
    try:
        note_id = _resolve_note_id(kwargs.get('id', id))
        to_ai = kwargs.get('to', to)

        if not note_id:
            return "!error:invalid_id"
        if not to_ai:
            return "!assign_failed:recipient_required"

        # Try storage adapter first
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        assigned = False

        if adapter:
            try:
                note_data = adapter.get_note(note_id)

                if not note_data:
                    return f"!error:not_found:{note_id}"

                owner = note_data.get('owner')
                if owner and owner != CURRENT_AI_ID:
                    return "!assign_failed:not_yours"

                success = adapter.update_note(note_id, owner=to_ai)
                if success:
                    assigned = True
                else:
                    return f"!assign_failed:update_failed:{note_id}"

            except Exception as e:
                logging.warning(f"Storage adapter assign failed, falling back to DuckDB: {e}")

        # Fallback to DuckDB if adapter failed
        if not assigned:
            with _get_db_conn() as conn:
                owner = conn.execute(
                    "SELECT owner FROM notes WHERE id = ?",
                    [note_id]
                ).fetchone()

                if not owner:
                    return f"!error:not_found:{note_id}"

                if owner[0] and owner[0] != CURRENT_AI_ID:
                    return "!assign_failed:not_yours"

                conn.execute(
                    "UPDATE notes SET owner = ? WHERE id = ?",
                    [to_ai, note_id]
                )
        
        if OUTPUT_FORMAT == 'pipe':
            return f"assigned:{note_id}|{to_ai}"
        else:
            return f"assigned:{note_id}|{to_ai}"
        
    except Exception as e:
        logging.error(f"Error assigning: {e}")
        return f"!assign_failed:{str(e)[:50]}"

# ============= EVOLUTION PATTERN =============

def evolve(goal: str = None, output: str = None, **kwargs) -> Dict:
    """Start an evolution challenge"""
    try:
        goal = str(kwargs.get('goal', goal) or '').strip()
        output_file = str(kwargs.get('output', output) or '').strip()
        
        if not goal:
            return "!evolve_failed:goal_required"
        
        if not output_file:
            safe_goal = re.sub(r'[^a-z0-9_-]', '', goal.lower()[:30])
            output_file = f"{safe_goal}_{int(time.time())}.txt"
        
        with _get_db_conn() as conn:
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM notes").fetchone()[0]
            evo_id = max_id + 1
            
            conn.execute('''
                INSERT INTO notes (
                    id, content, summary, type, author, owner,
                    teambook_name, created, pinned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                evo_id,
                f"EVOLUTION: {goal}\nOutput: {output_file}",
                f"Evolution: {goal[:100]}",
                "evolution",
                CURRENT_AI_ID,
                CURRENT_AI_ID,
                CURRENT_TEAMBOOK,
                datetime.now(timezone.utc),
                False
            ])
            
            max_eo_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM evolution_outputs").fetchone()[0]
            conn.execute('''
                INSERT INTO evolution_outputs (id, evolution_id, output_path, created, author)
                VALUES (?, ?, ?, ?, ?)
            ''', [max_eo_id + 1, evo_id, output_file, datetime.now(timezone.utc), CURRENT_AI_ID])
        
        if OUTPUT_FORMAT == 'pipe':
            return f"evo:{evo_id}|{output_file}"
        else:
            return f"evo:{evo_id}|{output_file}"
        
    except Exception as e:
        logging.error(f"Error starting evolution: {e}")
        return f"!evolve_failed:{str(e)[:50]}"

def attempt(evo_id: Any = None, content: str = None, **kwargs) -> Dict:
    """Make an attempt at an evolution"""
    try:
        evo_id = kwargs.get('evo_id', evo_id)
        content = str(kwargs.get('content', content) or '').strip()
        
        if not content:
            return "!attempt_failed:content_required"
        
        # Parse evolution ID
        if isinstance(evo_id, str) and evo_id.startswith('evo:'):
            evo_id = int(evo_id[4:])
        else:
            evo_id = int(evo_id) if evo_id else None
        
        if not evo_id:
            return "!attempt_failed:evo_id_required"
        
        with _get_db_conn() as conn:
            evolution = conn.execute(
                "SELECT id, summary FROM notes WHERE id = ? AND type = 'evolution'",
                [evo_id]
            ).fetchone()
            
            if not evolution:
                return f"!attempt_failed:evo_not_found:{evo_id}"
            
            attempt_count = conn.execute(
                "SELECT COUNT(*) FROM notes WHERE parent_id = ? AND type = 'attempt'",
                [evo_id]
            ).fetchone()[0]
            
            attempt_num = attempt_count + 1
            
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM notes").fetchone()[0]
            attempt_id = max_id + 1
            
            conn.execute('''
                INSERT INTO notes (
                    id, content, summary, type, parent_id, author, owner,
                    teambook_name, created
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                attempt_id,
                content,
                f"Attempt {attempt_num} for evo:{evo_id}",
                "attempt",
                evo_id,
                CURRENT_AI_ID,
                CURRENT_AI_ID,
                CURRENT_TEAMBOOK,
                datetime.now(timezone.utc)
            ])
        
        if OUTPUT_FORMAT == 'pipe':
            return f"attempt:{evo_id}.{attempt_num}|{attempt_id}"
        else:
            return f"attempt:{evo_id}.{attempt_num}|{attempt_id}"
        
    except Exception as e:
        logging.error(f"Error creating attempt: {e}")
        return f"!attempt_failed:{str(e)[:50]}"

def attempts(evo_id: Any = None, **kwargs) -> Dict:
    """List all attempts for an evolution"""
    try:
        evo_id = kwargs.get('evo_id', evo_id)
        
        if isinstance(evo_id, str) and evo_id.startswith('evo:'):
            evo_id = int(evo_id[4:])
        else:
            evo_id = int(evo_id) if evo_id else None
        
        if not evo_id:
            return "!error:evo_id_required"
        
        with _get_db_conn() as conn:
            attempt_list = conn.execute('''
                SELECT id, author, created, summary
                FROM notes 
                WHERE parent_id = ? AND type = 'attempt'
                ORDER BY created
            ''', [evo_id]).fetchall()
            
            if not attempt_list:
                return ""  # No attempts
            
            if OUTPUT_FORMAT == 'pipe':
                lines = []
                for i, (aid, author, created, summary) in enumerate(attempt_list, 1):
                    lines.append(f"{evo_id}.{i}|{aid}|{author}|{format_time_compact(created)}")
                return '\n'.join(lines)
            else:
                results = []
                for i, (aid, author, created, summary) in enumerate(attempt_list, 1):
                    results.append({
                        "num": f"{evo_id}.{i}",
                        "id": aid,
                        "author": author,
                        "time": format_time_compact(created)
                    })
                return '\n'.join([f"{r['num']}|{r['id']}|{r['author']}|{r['time']}" for r in results])
        
    except Exception as e:
        logging.error(f"Error listing attempts: {e}")
        return f"!attempts_failed:{str(e)[:50]}"

def combine(evo_id: Any = None, use: List[Any] = None, comment: str = None, **kwargs) -> Dict:
    """Combine attempts and output final result"""
    try:
        evo_id = kwargs.get('evo_id', evo_id)
        use_ids = kwargs.get('use', use) or []
        comment = kwargs.get('comment', comment)
        
        if isinstance(evo_id, str) and evo_id.startswith('evo:'):
            evo_id = int(evo_id[4:])
        else:
            evo_id = int(evo_id) if evo_id else None
        
        if not evo_id:
            return "!error:evo_id_required"
        
        with _get_db_conn() as conn:
            output_info = conn.execute(
                "SELECT output_path FROM evolution_outputs WHERE evolution_id = ?",
                [evo_id]
            ).fetchone()
            
            if not output_info:
                return f"!combine_failed:not_found:{evo_id}"
            
            output_file = output_info[0]
            
            # Parse attempt IDs
            attempt_ids = []
            for uid in use_ids:
                if isinstance(uid, str) and '.' in uid:
                    parts = uid.split('.')
                    attempt_num = int(parts[-1]) if parts[-1].isdigit() else 0
                    if attempt_num > 0:
                        attempt = conn.execute('''
                            SELECT id FROM notes 
                            WHERE parent_id = ? AND type = 'attempt'
                            ORDER BY created
                            LIMIT 1 OFFSET ?
                        ''', [evo_id, attempt_num - 1]).fetchone()
                        if attempt:
                            attempt_ids.append(attempt[0])
                else:
                    attempt_ids.append(int(uid))
            
            # Get attempt contents
            contents = []
            if attempt_ids:
                placeholders = ','.join(['?'] * len(attempt_ids))
                attempts_data = conn.execute(f'''
                    SELECT id, content, author 
                    FROM notes 
                    WHERE id IN ({placeholders})
                ''', attempt_ids).fetchall()
                
                for aid, content, author in attempts_data:
                    contents.append(f"# Attempt {aid} by {author}\n\n{content}\n\n")
            
            # Combine content
            final_content = "".join(contents)
            if comment:
                final_content = f"# {comment}\n\n{final_content}"
            
            # Write to output file
            output_path = get_outputs_dir() / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            # Clean up attempts
            attempt_count = conn.execute(
                "DELETE FROM notes WHERE parent_id = ? AND type = 'attempt'",
                [evo_id]
            ).rowcount
            
            # Update evolution status
            conn.execute('''
                UPDATE notes 
                SET content = content || '\n\nCOMPLETE: ' || ?
                WHERE id = ? AND type = 'evolution'
            ''', [output_file, evo_id])
        
        if OUTPUT_FORMAT == 'pipe':
            return f"combined:{output_file}|cleaned:{attempt_count}"
        else:
            return f"combined:{output_file}|cleaned:{attempt_count}"
        
    except Exception as e:
        logging.error(f"Error combining: {e}")
        return f"!combine_failed:{str(e)[:50]}"

# ============= CORE FUNCTIONS =============

def write(content: str = None, summary: str = None, tags: List[str] = None,
          linked_items: List[str] = None, **kwargs) -> Dict:
    """Write content to teambook"""
    try:
        start = datetime.now(timezone.utc)
        content = str(kwargs.get('content', content or '')).strip()
        if not content:
            content = f"Checkpoint {datetime.now(timezone.utc).strftime('%H:%M')}"

        truncated = False
        orig_len = len(content)
        if orig_len > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
            truncated = True

        summary = clean_text(summary)[:MAX_SUMMARY_LENGTH] if summary else simple_summary(content)

        # Extract project coordination parameters
        note_type = kwargs.get('type', None)
        parent_id = kwargs.get('parent_id', None)
        owner_override = kwargs.get('owner', 'default')  # 'default' means use CURRENT_AI_ID
        representation_policy = (kwargs.get('representation_policy') or 'default').strip().lower()
        metadata_payload = kwargs.get('metadata')
        # Normalize tags parameter - convert string 'null' to None for forgiving tool calls
        tags = normalize_param(tags)
        linked_items = normalize_param(linked_items)

        # Handle tags: convert string to list if needed (defensive parsing for MCP)
        if tags:
            if isinstance(tags, str):
                # Try to parse as JSON first (for MCP that sends '["tag1","tag2"]')
                try:
                    import json
                    tags = json.loads(tags)
                except (json.JSONDecodeError, ValueError):
                    # Not JSON - split by comma or treat as single tag
                    tags = [t.strip() for t in tags.split(',')] if ',' in tags else [tags]

            # Clean up each tag - remove quotes, brackets, extra whitespace
            tags = [str(t).lower().strip().strip('"').strip("'").strip('[').strip(']') for t in tags if t]
        else:
            tags = []

        # Limit tags to prevent UI/performance issues (LOW priority fix #8)
        MAX_TAGS = 20
        if len(tags) > MAX_TAGS:
            tags = tags[:MAX_TAGS]

        # Normalize linked items to a list for consistent metadata hashing
        if isinstance(linked_items, list):
            linked_items_list = linked_items
        elif linked_items:
            linked_items_list = [linked_items]
        else:
            linked_items_list = []
        linked_items = linked_items_list

        owner_hint = CURRENT_AI_ID if owner_override == 'default' else owner_override
        metadata_payload = attach_security_envelope(
            metadata_payload,
            {
                'ai_id': CURRENT_AI_ID,
                'teambook': CURRENT_TEAMBOOK,
                'content': content,
                'summary': summary,
                'tags': tags,
                'linked_items': linked_items,
                'note_type': note_type,
                'owner': owner_hint,
                'representation_policy': representation_policy,
            },
            purpose='teambook.note.write'
        )

        # Use storage adapter if available, otherwise fall back to DuckDB
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)

        if adapter:
            # Use storage adapter (PostgreSQL/Redis/DuckDB)
            note_id = adapter.write_note(
                content=content,
                summary=summary,
                tags=tags,
                pinned=False,
                linked_items=json.dumps(linked_items) if linked_items else None,
                owner=None,  # Will use CURRENT_AI_ID in backend
                note_type=note_type,
                parent_id=parent_id,
                representation_policy=representation_policy,
                metadata=metadata_payload
            )
        else:
            # Fallback to direct DuckDB
            with _get_db_conn() as conn:
                max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM notes").fetchone()[0]
                note_id = max_id + 1

                # Determine owner (None for claimable tasks, CURRENT_AI_ID otherwise)
                if owner_override == 'default':
                    final_owner = CURRENT_AI_ID
                elif owner_override is None:
                    final_owner = None  # Explicitly claimable
                else:
                    final_owner = owner_override

                stored_content, compressed_payload = teambook_storage._prepare_content_for_storage(content, representation_policy)
                stored_summary = summary
                if summary and teambook_storage.COMPRESSION_AVAILABLE and teambook_storage._should_compress(representation_policy):
                    stored_summary = teambook_storage.compress_content(summary)

                normalized_metadata = json.dumps(metadata_payload) if isinstance(metadata_payload, (dict, list)) else metadata_payload

                tamper_hash = teambook_storage.compute_note_tamper_hash({
                    'content': content,
                    'summary': summary,
                    'tags': tags,
                    'pinned': False,
                    'owner': final_owner,
                    'teambook_name': CURRENT_TEAMBOOK,
                    'linked_items': json.dumps(linked_items) if linked_items else None,
                    'representation_policy': representation_policy,
                    'metadata': normalized_metadata,
                    'type': note_type,
                    'parent_id': parent_id,
                })

                conn.execute('''
                    INSERT INTO notes (
                        id, content, content_compressed, summary, tags, pinned, author, owner,
                        teambook_name, type, parent_id, created, session_id, linked_items,
                        representation_policy, pagerank, has_vector, metadata, tamper_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    note_id,
                    stored_content,
                    compressed_payload,
                    stored_summary,
                    tags,
                    False,
                    CURRENT_AI_ID,
                    final_owner,
                    CURRENT_TEAMBOOK,
                    note_type,
                    parent_id,
                    datetime.now(timezone.utc),
                    None,
                    json.dumps(linked_items) if linked_items else None,
                    representation_policy,
                    0.0,
                    bool(collection),
                    normalized_metadata,
                    tamper_hash
                ])

                session_id = _detect_or_create_session(note_id, datetime.now(timezone.utc), conn)
                if session_id:
                    conn.execute('UPDATE notes SET session_id = ? WHERE id = ?', [session_id, note_id])

                _create_all_edges(note_id, content, session_id, conn)

                # Mark PageRank as dirty
                import teambook_shared
                teambook_shared.PAGERANK_DIRTY = True
        
        # Add to vector store
        _add_to_vector_store(note_id, content, summary, tags)
        
        # Publish event to Redis (real-time notifications!)
        if PUBSUB_AVAILABLE:
            try:
                publish_note_created(note_id, content, summary)
                logging.debug(f"Published note_created event for {note_id}")
            except Exception as e:
                logging.debug(f"Failed to publish event: {e}")

        # Save to write-through cache (Linear Memory Bridge)
        if CACHE_AVAILABLE:
            try:
                _save_note_to_cache(note_id, content, summary, CURRENT_TEAMBOOK)
                logging.debug(f"Cached note {note_id} for Linear Memory Bridge")
            except Exception as e:
                logging.debug(f"Failed to cache note: {e}")

        save_last_operation('write', {'id': note_id, 'summary': summary})
        _log_operation_to_db('write', int((datetime.now(timezone.utc) - start).total_seconds() * 1000))

        # Pure pipe format (token optimized!)
        result_str = f"{note_id}|{format_time_compact(datetime.now(timezone.utc))}|{pipe_escape(summary)}"
        if truncated:
            result_str += f"|T{orig_len}"
        return result_str

    except Exception as e:
        logging.error(f"Error in write: {e}", exc_info=True)
        return f"!write_failed:{str(e)[:50]}"

def read(query: str = None, tag: str = None, when: str = None,
         owner: str = None, pinned_only: bool = False, show_all: bool = False,
         limit: int = 50, mode: str = "hybrid", verbose: bool = False, **kwargs) -> Dict:
    """Read content from teambook"""
    try:
        start_time = datetime.now(timezone.utc)
        
        if isinstance(limit, str):
            try:
                limit = int(limit)
            except:
                limit = 50

        # Clamp limit to prevent performance issues (UX improvement)
        MAX_LIMIT = 1000
        if limit < 0:
            limit = 50  # Default for negative values
        elif limit > MAX_LIMIT:
            limit = MAX_LIMIT  # Cap at 1000

        # Fix LOW priority issue #10: limit=0 should return empty
        # Don't override if user explicitly set limit=0
        if not any([show_all, query, tag, when, owner, pinned_only]) and limit != 0:
            limit = DEFAULT_RECENT
        
        # Handle special owner queries
        if owner == "me":
            owner = CURRENT_AI_ID
        elif owner == "none":
            owner = "none"

        # Try storage adapter for simple reads (no advanced features)
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        use_advanced_features = mode in ["semantic", "hybrid"] or when  # Time queries and vector search need DuckDB

        if adapter and not use_advanced_features:
            # Use storage adapter (PostgreSQL/Redis/DuckDB)
            try:
                notes_data = adapter.read_notes(
                    limit=limit,
                    pinned_only=pinned_only,
                    owner=owner if owner != "none" else None,
                    note_type=None,  # Filter type IS NULL in formatter below
                    tag=tag,
                    query=query,
                    mode=mode if mode not in ["hybrid", "semantic"] else "recent"
                )

                # Convert to expected format and filter out evolution/attempt types
                all_notes = []
                for note_dict in notes_data:
                    # Skip evolution system notes
                    if note_dict.get('type'):
                        continue

                    # Convert dict to tuple format expected by formatter
                    note_tuple = (
                        note_dict['id'],
                        note_dict.get('content', ''),
                        note_dict.get('summary', ''),
                        note_dict.get('tags', []),
                        note_dict.get('pinned', False),
                        note_dict.get('author', ''),
                        note_dict.get('owner'),
                        note_dict.get('created'),
                        note_dict.get('pagerank', 0.0)
                    )
                    all_notes.append(note_tuple)

                # Format and return results
                save_last_operation('read', {"notes": all_notes})
                _log_operation_to_db('read', int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000))

                if not all_notes:
                    return ""

                lines = []
                for note in all_notes:
                    note_id, content, summary, tags_arr, pinned, author, owner_val, created, pagerank = note
                    parts = [
                        str(note_id),
                        format_time_compact(created),
                        summary or simple_summary(content, 150)
                    ]
                    if pinned:
                        parts.append('[PINNED]')
                    if owner_val:
                        parts.append(f"@{owner_val}")
                    if verbose and pagerank and pagerank > 0.01:
                        parts.append(f"RANK:{pagerank:.2f}")
                    lines.append('|'.join(pipe_escape(p) for p in parts))

                return '\n'.join(lines)

            except Exception as e:
                logging.warning(f"Storage adapter read failed, falling back to DuckDB: {e}")
                # Fall through to DuckDB implementation below

        # Fallback to DuckDB for advanced features or if adapter failed
        with _get_db_conn() as conn:
            _calculate_pagerank_if_needed(conn)
            
            conditions = []
            params = []
            
            if pinned_only:
                conditions.append("pinned = TRUE")
            
            if owner == "none":
                conditions.append("owner IS NULL")
            elif owner:
                conditions.append("owner = ?")
                params.append(owner)
            
            if when:
                time_start, time_end = parse_time_query(when)
                if time_start and time_end:
                    conditions.append("created BETWEEN ? AND ?")
                    params.extend([time_start, time_end])
            
            if tag:
                tag_clean = str(tag).lower().strip()
                conditions.append("list_contains(tags, ?)")
                params.append(tag_clean)
            
            notes = []
            
            # Get pinned notes
            if not pinned_only and not query and not tag and not when and not owner:
                pinned_notes = conn.execute('''
                    SELECT id, content, summary, tags, pinned, author, owner, created, pagerank
                    FROM notes WHERE pinned = TRUE AND type IS NULL
                    ORDER BY created DESC
                ''').fetchall()
            else:
                pinned_notes = []
            
            if query:
                # Semantic search
                semantic_ids = _search_vectors(str(query).strip(), limit) if mode in ["semantic", "hybrid"] else []
                
                # Keyword search
                keyword_ids = []
                if mode in ["keyword", "hybrid"]:
                    if teambook_storage.FTS_ENABLED:
                        try:
                            fts_results = conn.execute('''
                                SELECT DISTINCT n.id
                                FROM fts_main_notes f
                                JOIN notes n ON f.id = n.id
                                WHERE f MATCH ?
                                ORDER BY n.pagerank DESC, n.created DESC
                                LIMIT ?
                            ''', [str(query).strip(), limit]).fetchall()
                            keyword_ids = [row[0] for row in fts_results]
                        except Exception as e:
                            teambook_storage.FTS_ENABLED = False
                            logging.debug(f'FTS failed, using LIKE: {e}')
                            pass
                    
                    if not keyword_ids:
                        like_query = f"%{str(query).strip()}%"
                        like_results = conn.execute('''
                            SELECT id FROM notes 
                            WHERE (content ILIKE ? OR summary ILIKE ?) AND type IS NULL
                            ORDER BY pagerank DESC, created DESC
                            LIMIT ?
                        ''', [like_query, like_query, limit]).fetchall()
                        keyword_ids = [row[0] for row in like_results]
                
                # Combine results
                all_ids, seen = [], set()
                for i in range(max(len(semantic_ids), len(keyword_ids))):
                    if i < len(semantic_ids) and semantic_ids[i] not in seen:
                        all_ids.append(semantic_ids[i])
                        seen.add(semantic_ids[i])
                    if i < len(keyword_ids) and keyword_ids[i] not in seen:
                        all_ids.append(keyword_ids[i])
                        seen.add(keyword_ids[i])
                
                if all_ids:
                    note_ids = all_ids[:limit]
                    placeholders = ','.join(['?'] * len(note_ids))
                    
                    where_clause = " AND ".join(conditions) if conditions else "1=1"
                    final_params = note_ids + params + ([note_ids[0]] if note_ids else [])
                    
                    notes = conn.execute(f'''
                        SELECT id, content, summary, tags, pinned, author, owner, created, pagerank
                        FROM notes
                        WHERE id IN ({placeholders}) AND {where_clause} AND type IS NULL
                        ORDER BY 
                            CASE WHEN id = ? THEN 0 ELSE 1 END,
                            pinned DESC, pagerank DESC, created DESC
                    ''', final_params).fetchall()
            else:
                # Regular query without search
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                if where_clause:
                    where_clause += " AND type IS NULL"
                else:
                    where_clause = " WHERE type IS NULL"
                    
                notes = conn.execute(f'''
                    SELECT id, content, summary, tags, pinned, author, owner, created, pagerank
                    FROM notes {where_clause}
                    ORDER BY pinned DESC, created DESC
                    LIMIT ?
                ''', params + [limit]).fetchall()
        
        # Combine results
        all_notes = list(pinned_notes) + [n for n in notes if not n[4]]
        
        save_last_operation('read', {"notes": all_notes})
        _log_operation_to_db('read', int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000))

        # Check for pending notifications (Phase 2 feature)
        notifications = None
        try:
            from teambook_events import get_pending_notifications
            notifications = get_pending_notifications()
        except ImportError:
            pass

        # Pure pipe format (token optimized!)
        if not all_notes:
            if notifications:
                return f"!no_notes|notify:{notifications['unseen']}:{notifications['summary'][:30]}"
            return ""  # Empty = nothing found

        lines = []
        for note in all_notes:
            note_id, content, summary, tags_arr, pinned, author, owner, created, pagerank = note
            parts = [
                str(note_id),
                format_time_compact(created),
                summary or simple_summary(content, 150)
            ]
            if pinned:
                parts.append('[PINNED]')
            if owner:
                parts.append(f"@{owner}")
            if verbose and pagerank and pagerank > 0.01:
                parts.append(f"RANK:{pagerank:.2f}")
            lines.append('|'.join(pipe_escape(p) for p in parts))

        result = '\n'.join(lines)
        # Add notifications if present
        if notifications:
            result = f"NOTIFY:{notifications['unseen']}:{notifications['summary'][:30]}\n{result}"
        return result

    except Exception as e:
        logging.error(f"Error in read: {e}", exc_info=True)
        return f"!read_failed:{str(e)[:50]}"

def teambook_connection(verbose: bool = False, **kwargs) -> Dict:
    """Get teambook connection status and stats
    
    Shows current teambook, note counts, ownership stats, and activity.
    Alias: status(), get_status()
    
    Args:
        verbose: Show detailed stats including edges, entities, sessions (default: False)
    
    Returns:
        Pipe-separated status info:
        Connected to town-hall|n:42|p:5|owned:3|last:2h ago
    """
    try:
        # Auto-connect to town hall if not connected
        connect_msg = _ensure_connected_with_feedback()

        # Check for pending notifications (Phase 2 feature)
        notifications = None
        try:
            from teambook_events import get_pending_notifications
            notifications = get_pending_notifications()
        except ImportError:
            pass

        # Try storage adapter first
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        stats = None

        if adapter:
            try:
                stats = adapter.get_stats()
                # Get additional stats from adapter
                notes = stats.get('total_notes', 0)
                pinned = stats.get('pinned_notes', 0)

                # Get owned/unclaimed counts via adapter
                # Note: This requires reading notes to count ownership
                # For now, use a simple approximation or fall back to DuckDB for these specific stats
                owned = 0
                unclaimed = 0
                last_activity = "never"

                # Try to get recent activity
                try:
                    recent_notes = adapter.read_notes(limit=1, mode='recent')
                    if recent_notes:
                        last_activity = format_time_compact(recent_notes[0].get('created', ''))
                except:
                    pass

            except Exception as e:
                logging.warning(f"Storage adapter get_stats failed, falling back to DuckDB: {e}")
                stats = None

        # Fallback to DuckDB if adapter failed
        if not stats:
            with _get_db_conn() as conn:
                notes = conn.execute('SELECT COUNT(*) FROM notes WHERE type IS NULL').fetchone()[0]
                pinned = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = TRUE AND type IS NULL').fetchone()[0]
                owned = conn.execute('SELECT COUNT(*) FROM notes WHERE owner IS NOT NULL AND type IS NULL').fetchone()[0]
                unclaimed = conn.execute('SELECT COUNT(*) FROM notes WHERE owner IS NULL AND type IS NULL').fetchone()[0]

                recent = conn.execute('SELECT created FROM notes WHERE type IS NULL ORDER BY created DESC LIMIT 1').fetchone()
                last_activity = format_time_compact(recent[0]) if recent else "never"

        # Verbose mode still requires DuckDB for some advanced stats (edges, entities, etc.)
        if verbose:
            with _get_db_conn() as conn:
                edges = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
                entities = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
                sessions = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
                vault = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
                tags = conn.execute('SELECT COUNT(DISTINCT tag) FROM (SELECT unnest(tags) as tag FROM notes WHERE tags IS NOT NULL)').fetchone()[0]
                vector_count = collection.count() if collection else 0
                evolutions = conn.execute("SELECT COUNT(*) FROM notes WHERE type = 'evolution'").fetchone()[0]

            # Pure pipe format (token optimized!)
            parts = [
                f"n:{notes}",
                f"p:{pinned}",
                f"owned:{owned}",
                f"free:{unclaimed}",
                f"v:{vector_count}",
                f"e:{edges}",
                f"evo:{evolutions}",
                f"last:{last_activity}",
                f"team:{CURRENT_TEAMBOOK or 'private'}"
            ]
            if notifications:
                parts.append(f"notify:{notifications['unseen']}:{notifications['summary'][:20]}")
            return '|'.join(parts)
        else:
            # Pure pipe format (token optimized!)
            # Always show connection status first
            connection_status = f"Connected to {CURRENT_TEAMBOOK}" if CURRENT_TEAMBOOK else "Connected to private"

            status_parts = [
                connection_status,
                f"n:{notes}",
                f"p:{pinned}",
                f"owned:{owned}",
                f"{last_activity}"
            ]
            if notifications:
                status_parts.append(f"notify:{notifications['unseen']}")

            # Prepend CLI first-time message if present
            result = '|'.join(status_parts)
            if connect_msg:
                result = f"{connect_msg}\n{result}"
            return result
    
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return f"!status_failed:{str(e)[:50]}"

def status(verbose: bool = False, **kwargs) -> Dict:
    """Get status - ALIAS for teambook_connection()
    
    Primary: teambook_connection()
    """
    return teambook_connection(verbose=verbose, **kwargs)

def get_status(verbose: bool = False, **kwargs) -> Dict:
    """Get status - Deprecated for teambook_connection()
    
    Primary: teambook_connection()
    Deprecated: Use teambook_connection() or status() instead
    """
    return teambook_connection(verbose=verbose, **kwargs)

def pin_note(id: Any = None, **kwargs) -> Dict:
    """Pin a note"""
    return _modify_pin_status(kwargs.get('id', id), True)

def unpin_note(id: Any = None, **kwargs) -> Dict:
    """Unpin a note"""
    return _modify_pin_status(kwargs.get('id', id), False)

def _modify_pin_status(id_param: Any, pin: bool) -> Dict:
    """Helper to pin or unpin a note"""
    try:
        note_id = _resolve_note_id(id_param)
        if not note_id:
            return "!pin_failed:invalid_id"

        # Try storage adapter first
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        result = None

        if adapter:
            try:
                # Get note first to check if it exists and get summary
                note_data = adapter.get_note(note_id)
                if note_data:
                    # Update the note
                    success = adapter.update_note(note_id, pinned=pin)
                    if success:
                        result = (note_data.get('summary'), note_data.get('content'))
                    else:
                        return f"!note_failed:update_failed:{note_id}"
                else:
                    return f"!note_failed:not_found:{note_id}"
            except Exception as e:
                logging.warning(f"Storage adapter pin/unpin failed, falling back to DuckDB: {e}")

        # Fallback to DuckDB if adapter failed
        if not result:
            with _get_db_conn() as conn:
                result = conn.execute(
                    'UPDATE notes SET pinned = ? WHERE id = ? RETURNING summary, content',
                    [pin, note_id]
                ).fetchone()

                if not result:
                    return f"!note_failed:not_found:{note_id}"

        action = 'pin' if pin else 'unpin'
        save_last_operation(action, {'id': note_id})

        if pin:
            summ = result[0] or simple_summary(result[1], 100)
            if OUTPUT_FORMAT == 'pipe':
                return f"pinned:{note_id}|{summ}"
            else:
                return f"pinned:{note_id}|{summ}"
        else:
            return f"unpinned:{note_id}"

    except Exception as e:
        logging.error(f"Error in pin/unpin: {e}")
        action = 'pin' if pin else 'unpin'
        return f"!{action}_failed:{str(e)[:50]}"

def get_full_note(id: Any = None, verbose: bool = False, **kwargs) -> Dict:
    """Get complete note"""
    try:
        note_id = _resolve_note_id(kwargs.get('id', id))
        if not note_id:
            return "!error:invalid_note_id"
        
        with _get_db_conn() as conn:
            note = conn.execute('SELECT * FROM notes WHERE id = ?', [note_id]).fetchone()
            if not note:
                return f"!error:note_not_found:{note_id}"
            
            cols = [desc[0] for desc in conn.description]
            result = dict(zip(cols, note))
            
            # Clean up datetime
            if 'created' in result and result['created']:
                result['created'] = format_time_compact(result['created'])
            
            # Get entities
            entities = conn.execute('''
                SELECT e.name FROM entities e
                JOIN entity_notes en ON e.id = en.entity_id
                WHERE en.note_id = ?
            ''', [note_id]).fetchall()
            if entities:
                result['entities'] = [e[0] for e in entities]
            
            # Remove backend fields
            for field in ['session_id', 'linked_items', 'pagerank', 'has_vector', 'parent_id']:
                result.pop(field, None)
        
        save_last_operation('get_full_note', {'id': note_id})
        # Convert dict to pipe format
        parts = [f"{k}:{v}" for k, v in result.items() if k not in ["type", "teambook_name"]]
        return '|'.join(str(p) for p in parts)

    except Exception as e:
        logging.error(f"Error in get_full_note: {e}", exc_info=True)
        return f"!note_failed:{str(e)[:50]}"

# ============= VAULT FUNCTIONS =============

def vault_store(key: str = None, value: str = None, **kwargs) -> Dict:
    """Store encrypted secret"""
    try:
        key = str(kwargs.get('key', key) or '').strip()
        value = str(kwargs.get('value', value) or '').strip()
        if not key or not value:
            return "!vault_store_failed:key_value_required"

        # Add size limit to prevent performance issues (UX improvement)
        MAX_VAULT_VALUE_SIZE = 10 * 1024 * 1024  # 10MB limit
        value_size = len(value.encode('utf-8'))
        if value_size > MAX_VAULT_VALUE_SIZE:
            return f"!vault_store_failed:too_large:{value_size}"
        
        # Ensure vault_manager is initialized
        if not teambook_storage.vault_manager:
            _init_vault_manager()

        encrypted = teambook_storage.vault_manager.encrypt(value)

        # Try storage adapter first
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        if adapter:
            try:
                adapter.vault_set(key, encrypted, CURRENT_AI_ID)
                _log_operation_to_db('vault_store')
                return f"stored:{key}"
            except Exception as e:
                logging.warning(f"Storage adapter vault_set failed, falling back to DuckDB: {e}")

        # Fallback to DuckDB
        now = datetime.now(timezone.utc)
        with _get_db_conn() as conn:
            conn.execute('''
                INSERT INTO vault (key, encrypted_value, created, updated, author)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    encrypted_value = EXCLUDED.encrypted_value,
                    updated = EXCLUDED.updated
            ''', [key, encrypted, now, now, CURRENT_AI_ID])

        _log_operation_to_db('vault_store')
        return f"stored:{key}"
    
    except Exception as e:
        logging.error(f"Error in vault_store: {e}")
        return f"!vault_store_failed:{str(e)[:50]}"

def vault_retrieve(key: str = None, **kwargs) -> Dict:
    """Retrieve decrypted secret"""
    try:
        key = str(kwargs.get('key', key) or '').strip()
        if not key:
            return "!vault_retrieve_failed:key_required"
        
        # Ensure vault_manager is initialized
        if not teambook_storage.vault_manager:
            _init_vault_manager()

        # Try storage adapter first
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        encrypted_value = None

        if adapter:
            try:
                encrypted_value = adapter.vault_get(key)
            except Exception as e:
                logging.warning(f"Storage adapter vault_get failed, falling back to DuckDB: {e}")

        # Fallback to DuckDB if adapter failed or returned None
        if not encrypted_value:
            with _get_db_conn() as conn:
                result = conn.execute(
                    'SELECT encrypted_value FROM vault WHERE key = ?',
                    [key]
                ).fetchone()

            if not result:
                return f"!vault_retrieve_failed:not_found:{key}"
            encrypted_value = result[0]

        # Convert to bytes if needed (PostgreSQL may return memoryview or bytea)
        if isinstance(encrypted_value, memoryview):
            encrypted_value = bytes(encrypted_value)
        elif isinstance(encrypted_value, str):
            encrypted_value = encrypted_value.encode()

        decrypted = teambook_storage.vault_manager.decrypt(encrypted_value)
        _log_operation_to_db('vault_retrieve')
        return f"{key}|{decrypted}"
    
    except Exception as e:
        logging.error(f"Error in vault_retrieve: {e}")
        return f"!vault_retrieve_failed:{str(e)[:50]}"

def vault_list(**kwargs) -> Dict:
    """List vault keys"""
    try:
        # Try storage adapter first
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        items_data = None

        if adapter:
            try:
                items_data = adapter.vault_list()
                # Convert from list of dicts to expected format
                if items_data:
                    if OUTPUT_FORMAT == 'pipe':
                        keys = []
                        for item in items_data:
                            keys.append(f"{item['key']}|{format_time_compact(item['updated'])}")
                        return '\n'.join(keys)
                    else:
                        return '\n'.join([f"{item['key']}|{format_time_compact(item['updated'])}" for item in items_data])
                else:
                    return ""  # Vault empty
            except Exception as e:
                logging.warning(f"Storage adapter vault_list failed, falling back to DuckDB: {e}")

        # Fallback to DuckDB
        with _get_db_conn() as conn:
            items = conn.execute(
                'SELECT key, updated FROM vault ORDER BY updated DESC'
            ).fetchall()

        if not items:
            return ""  # Vault empty

        if OUTPUT_FORMAT == 'pipe':
            keys = []
            for key, updated in items:
                keys.append(f"{key}|{format_time_compact(updated)}")
            return '\n'.join(keys)
        else:
            keys = [
                {'key': key, 'updated': format_time_compact(updated)}
                for key, updated in items
            ]
            return '\n'.join([f"{k['key']}|{k['updated']}" for k in keys])
    
    except Exception as e:
        logging.error(f"Error in vault_list: {e}")
        return f"!vault_list_failed:{str(e)[:50]}"

# ============= PHASE 2: EVENT SYSTEM & EVOLUTION =============
# Import Phase 2 modules

try:
    from teambook_events import (
        watch, unwatch, get_events, list_watches, watch_stats
    )
    EVENTS_AVAILABLE = True
except ImportError:
    EVENTS_AVAILABLE = False
    logging.warning("Event system not available")

try:
    from teambook_evolution import (
        evolve, contribute, rank_contribution, contributions,
        synthesize, conflicts, vote
    )
    EVOLUTION_V2_AVAILABLE = True
except ImportError:
    EVOLUTION_V2_AVAILABLE = False
    logging.warning("Enhanced evolution not available")

# ============= ALIASES FOR COMPATIBILITY =============

def remember(**kwargs) -> Dict:
    """Save a note (Notebook compatibility)"""
    return write(**kwargs)

# REMOVED: recall() alias conflicts with Notebook's deep-search recall()
# Per naming consensus: Teambook read() != Notebook recall()
# Use read() for teambook note browsing, recall() stays exclusive to Notebook

def get(**kwargs) -> Dict:
    """Get full note (alias)"""
    return get_full_note(**kwargs)

def pin(**kwargs) -> Dict:
    """Pin note (alias)"""
    return pin_note(**kwargs)

def unpin(**kwargs) -> Dict:
    """Unpin note (alias)"""
    return unpin_note(**kwargs)

# ============= MESSAGING & COORDINATION =============
# Import messaging and coordination functions

def normalize_param(value):
    """Normalize parameter values"""
    if value == 'null' or value == 'None':
        return None
    return value

try:
    from teambook_messaging import (
        broadcast, direct_message, subscribe, unsubscribe,
        get_subscriptions, read_channel, read_dms, message_stats
    )
    MESSAGING_AVAILABLE = True
    # Note: get_messages() V3 function defined above (line ~793) with compact parameter
    # Removed old alias to avoid overwriting the superior V3 implementation
except ImportError:
    MESSAGING_AVAILABLE = False
    logging.warning("Messaging module not available")

try:
    from teambook_coordination import (
        acquire_lock, release_lock, extend_lock, list_locks,
        queue_task, claim_task, complete_task, queue_stats
    )
    COORDINATION_AVAILABLE = True
except ImportError:
    COORDINATION_AVAILABLE = False
    logging.warning("Coordination module not available")

# ============= OBSERVABILITY =============

def who_is_here(minutes: int = 5, **kwargs) -> Dict:
    """
    Show which AIs are currently active in the teambook.

    minutes: Consider active if activity in last N minutes (default: 5)
    """
    try:
        minutes = int(kwargs.get('minutes', minutes or 5))
        if minutes < 1 or minutes > 60:
            minutes = 5

        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

        with _get_db_conn() as conn:
            # Get active AIs from notes, messages, and locks
            activities = conn.execute('''
                SELECT DISTINCT author as ai_id, MAX(created) as last_seen
                FROM notes
                WHERE created > ? AND type IS NULL
                GROUP BY author
            ''', [since]).fetchall()

            # Add message activity if available
            try:
                msg_activity = conn.execute('''
                    SELECT DISTINCT from_ai as ai_id, MAX(created) as last_seen
                    FROM messages
                    WHERE created > ?
                    GROUP BY from_ai
                ''', [since]).fetchall()
                activities.extend(msg_activity)
            except:
                pass

            # Add lock holders
            try:
                lock_activity = conn.execute('''
                    SELECT DISTINCT held_by as ai_id, MAX(acquired_at) as last_seen
                    FROM locks
                    WHERE acquired_at > ?
                    GROUP BY held_by
                ''', [since]).fetchall()
                activities.extend(lock_activity)
            except:
                pass

        # Deduplicate and get most recent activity per AI
        ai_activity = {}
        for ai_id, last_seen in activities:
            if ai_id not in ai_activity or last_seen > ai_activity[ai_id]:
                ai_activity[ai_id] = last_seen

        if not ai_activity:
            return ""  # No active AIs

        # Sort by most recent activity
        sorted_ais = sorted(ai_activity.items(), key=lambda x: x[1], reverse=True)

        if OUTPUT_FORMAT == 'pipe':
            lines = []
            for ai_id, last_seen in sorted_ais:
                # Add emoji only for CLI (not MCP)
                active_marker = "🟢" if (ai_id == CURRENT_AI_ID and IS_CLI) else ""
                parts = [
                    ai_id,
                    format_time_compact(last_seen),
                    active_marker
                ]
                lines.append('|'.join(pipe_escape(p) for p in parts if p))
            return '\n'.join(lines)
        else:
            formatted = []
            for ai_id, last_seen in sorted_ais:
                formatted.append({
                    'ai_id': ai_id,
                    'last_seen': format_time_compact(last_seen),
                    'is_me': ai_id == CURRENT_AI_ID
                })
            return '\n'.join([f"{ai['ai_id']}|{ai['last_seen']}" for ai in formatted])

    except Exception as e:
        logging.error(f"Error in who_is_here: {e}")
        return "!who_is_here_failed"

def what_are_they_doing(ai_id: str = None, limit: int = 10, **kwargs) -> Dict:
    """
    Show recent activities of a specific AI or all AIs.

    ai_id: Specific AI to track (default: all AIs)
    limit: Number of activities to show (default: 10)
    """
    try:
        ai_id = kwargs.get('ai_id', ai_id)
        limit = int(kwargs.get('limit', limit or 10))
        if limit < 1 or limit > 50:
            limit = 10

        with _get_db_conn() as conn:
            if ai_id:
                # Specific AI
                query = '''
                    SELECT author, 'wrote' as action, summary, created
                    FROM notes
                    WHERE author = ? AND type IS NULL
                    ORDER BY created DESC
                    LIMIT ?
                '''
                params = [ai_id, limit]
            else:
                # All AIs
                query = '''
                    SELECT author, 'wrote' as action, summary, created
                    FROM notes
                    WHERE type IS NULL
                    ORDER BY created DESC
                    LIMIT ?
                '''
                params = [limit]

            activities = conn.execute(query, params).fetchall()

        if not activities:
            return ""  # No activity

        if OUTPUT_FORMAT == 'pipe':
            lines = []
            for author, action, summary, created in activities:
                parts = [
                    author,
                    action,
                    format_time_compact(created),
                    summary[:80] if summary else ""
                ]
                lines.append('|'.join(pipe_escape(p) for p in parts))
            return '\n'.join(lines)
        else:
            formatted = []
            for author, action, summary, created in activities:
                formatted.append({
                    'ai': author,
                    'action': action,
                    'time': format_time_compact(created),
                    'summary': summary
                })
            return '\n'.join([f"{a['ai']}|{a['action']}|{a['time']}|{a.get('summary', '')}" for a in formatted])

    except Exception as e:
        logging.error(f"Error in what_are_they_doing: {e}")
        return "!error:failed"


def teambook_observability_snapshot(
    limit: int = 25,
    include_events: bool = True,
    include_presence: bool = True,
    include_tasks: bool = True,
    **kwargs
) -> str:
    """Aggregate presence, queue, and event observability into a single snapshot."""
    try:
        limit = int(kwargs.get('limit', limit or 25))
    except Exception:
        limit = 25

    snapshot: Dict[str, Any] = {
        'teambook': CURRENT_TEAMBOOK or 'private',
        'generated_at': datetime.now(timezone.utc).isoformat()
    }

    if include_presence:
        snapshot['presence'] = presence_snapshot(limit=limit)

    if include_tasks:
        try:
            backend_type, get_conn = get_coordination_backend()
            with get_conn() as conn:
                init_coordination_tables(conn)

                stats = conn.execute(
                    '''
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'claimed' THEN 1 END) as claimed,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
                    FROM task_queue
                    WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                    ''',
                    [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK]
                ).fetchone()

                priority_rows = conn.execute(
                    '''
                    SELECT priority, COUNT(*)
                    FROM task_queue
                    WHERE status = 'pending'
                      AND (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                    GROUP BY priority
                    ORDER BY priority DESC
                    LIMIT ?
                    ''',
                    [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK, limit]
                ).fetchall()

            snapshot['tasks'] = {
                'backend': backend_type,
                'total': stats[0] if stats else 0,
                'pending': stats[1] if stats else 0,
                'claimed': stats[2] if stats else 0,
                'completed': stats[3] if stats else 0,
                'priority_hotspots': {str(row[0]): row[1] for row in priority_rows}
            }
        except Exception as exc:
            logging.debug(f"Task snapshot failed: {exc}")
            snapshot['tasks'] = {'error': 'unavailable'}

    if include_events:
        try:
            with _get_db_conn() as conn:
                init_events_tables(conn)

                unseen = conn.execute(
                    '''
                    SELECT COUNT(*)
                    FROM event_deliveries d
                    JOIN events e ON e.id = d.event_id
                    WHERE d.seen = FALSE
                      AND (? IS NULL OR e.teambook_name = ? OR e.teambook_name IS NULL)
                    ''',
                    [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK]
                ).fetchone()[0]

                recent_rows = conn.execute(
                    '''
                    SELECT item_type, event_type, actor_ai_id, created_at
                    FROM events
                    WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                    ORDER BY created_at DESC
                    LIMIT ?
                    ''',
                    [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK, limit]
                ).fetchall()

                watcher_rows = conn.execute(
                    '''
                    SELECT item_type, COUNT(*), MAX(last_activity)
                    FROM watches
                    WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                    GROUP BY item_type
                    ORDER BY MAX(last_activity) DESC
                    LIMIT ?
                    ''',
                    [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK, limit]
                ).fetchall()

            snapshot['events'] = {
                'unseen': unseen,
                'recent': [
                    {
                        'item_type': row[0],
                        'event_type': row[1],
                        'actor': row[2],
                        'created_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3])
                    }
                    for row in recent_rows
                ],
                'active_watches': [
                    {
                        'item_type': row[0],
                        'watchers': row[1],
                        'last_activity': row[2].isoformat() if row[2] else None
                    }
                    for row in watcher_rows
                ]
            }
        except Exception as exc:
            logging.debug(f"Event snapshot failed: {exc}")
            snapshot['events'] = {'error': 'unavailable'}

    try:
        return json.dumps(snapshot, default=str)
    except TypeError:
        lines = [f"teambook:{snapshot['teambook']}"]
        if 'presence' in snapshot:
            breakdown = snapshot['presence'].get('status_breakdown', {})
            if breakdown:
                lines.append('presence|' + '|'.join(f"{k}:{v}" for k, v in breakdown.items() if v))
        if 'tasks' in snapshot and isinstance(snapshot['tasks'], dict) and 'error' not in snapshot['tasks']:
            tasks = snapshot['tasks']
            lines.append(
                f"tasks|total:{tasks.get('total', 0)}|pending:{tasks.get('pending', 0)}|claimed:{tasks.get('claimed', 0)}|completed:{tasks.get('completed', 0)}"
            )
        if 'events' in snapshot and isinstance(snapshot['events'], dict) and 'unseen' in snapshot['events']:
            lines.append(f"events|unseen:{snapshot['events'].get('unseen', 0)}")
        return '\n'.join(lines)


def ai_collective_progress_report(limit: int = 25, **kwargs) -> str:
    """Compose queue, event, and presence stats for AI teams."""
    try:
        limit = int(kwargs.get('limit', limit or 25))
    except Exception:
        limit = 25

    presence_records = get_presence_overview(limit=limit)
    status_counts = Counter(record.get('status', '').lower() for record in presence_records)
    category_summary = summarize_presence_categories(presence_records) if presence_records else {}

    try:
        backend_type, get_conn = get_coordination_backend()
        with get_conn() as conn:
            init_coordination_tables(conn)

            stats = conn.execute(
                '''
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN status = 'claimed' THEN 1 END) as claimed,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
                FROM task_queue
                WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                ''',
                [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK]
            ).fetchone()

            backlog = conn.execute(
                '''
                SELECT priority, COUNT(*)
                FROM task_queue
                WHERE status = 'pending'
                  AND (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                GROUP BY priority
                ORDER BY priority DESC
                LIMIT ?
                ''',
                [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK, limit]
            ).fetchall()

            claimer_rows = conn.execute(
                '''
                SELECT claimed_by, COUNT(*)
                FROM task_queue
                WHERE status = 'claimed' AND claimed_by IS NOT NULL
                  AND (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                GROUP BY claimed_by
                ORDER BY COUNT(*) DESC
                LIMIT ?
                ''',
                [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK, limit]
            ).fetchall()

        tasks_line = f"tasks|total:{stats[0] if stats else 0}|pending:{stats[1] if stats else 0}|claimed:{stats[2] if stats else 0}|completed:{stats[3] if stats else 0}"
        backlog_line = ""
        if backlog:
            backlog_line = "tasks_hot|" + ','.join(f"p{row[0]}:{row[1]}" for row in backlog)
        claimer_line = ""
        if claimer_rows:
            claimer_line = "tasks_claimed|" + ','.join(f"{row[0]}:{row[1]}" for row in claimer_rows)
    except Exception as exc:
        logging.debug(f"Progress report task stats failed: {exc}")
        tasks_line = "tasks|error"
        backlog_line = ""
        claimer_line = ""

    try:
        with _get_db_conn() as conn:
            init_events_tables(conn)

            unseen = conn.execute(
                '''
                SELECT COUNT(*)
                FROM event_deliveries d
                JOIN events e ON e.id = d.event_id
                WHERE d.seen = FALSE
                  AND (? IS NULL OR e.teambook_name = ? OR e.teambook_name IS NULL)
                ''',
                [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK]
            ).fetchone()[0]

            recent = conn.execute(
                '''
                SELECT event_type
                FROM events
                WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)
                ORDER BY created_at DESC
                LIMIT ?
                ''',
                [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK, limit]
            ).fetchall()

        event_counter = Counter(row[0] for row in recent if row and row[0])
        events_line = f"events|unseen:{unseen}|recent:" + ','.join(f"{etype}:{count}" for etype, count in event_counter.most_common(5))
    except Exception as exc:
        logging.debug(f"Progress report event stats failed: {exc}")
        events_line = "events|error"

    presence_line = "presence|" + '|'.join([
        f"online:{status_counts.get('online', 0)}",
        f"away:{status_counts.get('away', 0)}",
        f"offline:{status_counts.get('offline', 0)}",
        f"coordination:{category_summary.get('coordination', 0) if category_summary else 0}"
    ])

    lines = [
        f"teambook:{CURRENT_TEAMBOOK or 'private'}",
        tasks_line,
        backlog_line,
        claimer_line,
        events_line,
        presence_line
    ]

    # Filter out empty lines
    return '\n'.join(line for line in lines if line)


def teambook_vector_graph_diagnostics(limit: int = 5, include_samples: bool = True, **kwargs) -> str:
    """Surface graph connectivity diagnostics for semantic notes."""
    try:
        limit = int(kwargs.get('limit', limit or 5))
    except Exception:
        limit = 5

    with _get_db_conn() as conn:
        node_rows = conn.execute(
            'SELECT id FROM notes WHERE (? IS NULL OR teambook_name = ? OR teambook_name IS NULL)',
            [CURRENT_TEAMBOOK, CURRENT_TEAMBOOK]
        ).fetchall()
        edge_rows = conn.execute('SELECT from_id, to_id FROM edges').fetchall()

    node_ids = {row[0] for row in node_rows}
    if not node_ids:
        diagnostics = {
            'teambook': CURRENT_TEAMBOOK or 'private',
            'total_nodes': 0,
            'total_edges': 0,
            'disconnected_notes': 0,
            'clusters': []
        }
        return json.dumps(diagnostics)

    adjacency: Dict[int, set] = {node: set() for node in node_ids}
    edge_pairs = set()
    for from_id, to_id in edge_rows:
        if from_id in node_ids and to_id in node_ids:
            adjacency[from_id].add(to_id)
            adjacency[to_id].add(from_id)
            edge_pairs.add(tuple(sorted((from_id, to_id))))

    visited = set()
    components: List[List[int]] = []
    for node in node_ids:
        if node in visited:
            continue
        stack = [node]
        component = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(adjacency[current] - visited)
        components.append(component)

    edge_lookup = edge_pairs
    clusters = []
    for component in sorted(components, key=len):
        if len(clusters) >= limit:
            break
        subset = set(component)
        edge_count = sum(1 for edge in edge_lookup if edge[0] in subset and edge[1] in subset)
        possible_edges = max(1, len(component) * (len(component) - 1) / 2)
        density = round(edge_count / possible_edges, 3)
        cluster_info = {
            'size': len(component),
            'edge_count': edge_count,
            'edge_density': density
        }
        if include_samples:
            cluster_info['sample_nodes'] = component[:min(3, len(component))]
        clusters.append(cluster_info)

    disconnected = sum(1 for comp in components if len(comp) == 1 and not adjacency[comp[0]])

    diagnostics = {
        'teambook': CURRENT_TEAMBOOK or 'private',
        'total_nodes': len(node_ids),
        'total_edges': len(edge_pairs),
        'disconnected_notes': disconnected,
        'clusters': clusters
    }

    return json.dumps(diagnostics, default=str)

def watch(note_id: Any = None, **kwargs) -> Dict:
    """
    Add note to watch list (get notified of changes).

    Note: Currently registers intent, full implementation requires
    event streaming infrastructure.
    """
    try:
        note_id = _resolve_note_id(kwargs.get('note_id', note_id))
        if not note_id:
            return "!watch_failed:invalid_id"

        # For now, just verify note exists
        with _get_db_conn() as conn:
            note = conn.execute(
                'SELECT summary FROM notes WHERE id = ?',
                [note_id]
            ).fetchone()

            if not note:
                return "!watch_failed:not_found"

        # TODO: Implement actual watch mechanism with event system
        return f"watching:{note_id}|future"

    except Exception as e:
        logging.error(f"Error in watch: {e}")
        return "!error:failed"

# ============= BATCH OPERATIONS =============

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
    """Execute multiple operations efficiently"""
    try:
        from teambook_shared import BATCH_MAX
        
        operations = kwargs.get('operations', operations or [])
        if not operations:
            return "!batch_failed:no_operations"
        if len(operations) > BATCH_MAX:
            return f"!batch_failed:max_exceeded:{BATCH_MAX}"
        
        # Map all operations to functions
        op_map = {
            'write': write, 'read': read,
            'remember': remember,
            'pin_note': pin_note, 'pin': pin,
            'unpin_note': unpin_note, 'unpin': unpin,
            'vault_store': vault_store,
            'vault_retrieve': vault_retrieve,
            'get_full_note': get_full_note, 'get': get,
            'status': get_status, 'vault_list': vault_list,
            'create_teambook': create_teambook,
            'join_teambook': join_teambook,
            'use_teambook': use_teambook,
            'list_teambooks': list_teambooks,
            'claim': claim, 'release': release, 'assign': assign,
            'evolve': evolve, 'attempt': attempt,
            'attempts': attempts, 'combine': combine,
            # Observability
            'who_is_here': who_is_here,
            'what_are_they_doing': what_are_they_doing,
            'watch': watch
        }

        # Add messaging functions if available
        if MESSAGING_AVAILABLE:
            op_map.update({
                'broadcast': broadcast,
                'direct_message': direct_message, 'dm': direct_message,
                'subscribe': subscribe, 'sub': subscribe,
                'unsubscribe': unsubscribe, 'unsub': unsubscribe,
                'read_channel': read_channel,
                'read_dms': read_dms,
                'message_stats': message_stats
            })

        # Add coordination functions if available
        if COORDINATION_AVAILABLE:
            op_map.update({
                'acquire_lock': acquire_lock, 'lock': acquire_lock,
                'release_lock': release_lock, 'unlock': release_lock,
                'extend_lock': extend_lock,
                'list_locks': list_locks,
                'queue_task': queue_task,
                'claim_task': claim_task,
                'complete_task': complete_task,
                'queue_stats': queue_stats
            })

        # Add event system functions if available
        if EVENTS_AVAILABLE:
            op_map.update({
                'watch': watch,
                'unwatch': unwatch,
                'get_events': get_events,
                'list_watches': list_watches,
                'watch_stats': watch_stats
            })

        # Add enhanced evolution functions if available
        if EVOLUTION_V2_AVAILABLE:
            op_map.update({
                'evolve': evolve,
                'contribute': contribute,
                'rank_contribution': rank_contribution, 'rank': rank_contribution,
                'contributions': contributions,
                'synthesize': synthesize,
                'conflicts': conflicts,
                'vote': vote
            })

        results = []
        for op in operations:
            op_type = op.get('type')
            if op_type in op_map:
                results.append(op_map[op_type](**op.get('args', {})))
            else:
                results.append(f"!batch_error:unknown_op:{op_type}")
        
        if OUTPUT_FORMAT == 'pipe':
            batch_lines = []
            for r in results:
                if "error" in r:
                    batch_lines.append(f"error:{r['error']}")
                elif "saved" in r:
                    batch_lines.append(r["saved"])
                elif "notes" in r and isinstance(r["notes"], list):
                    batch_lines.extend(r["notes"])
                elif "status" in r:
                    batch_lines.append(r["status"])
                elif "teambooks" in r and isinstance(r["teambooks"], list):
                    batch_lines.extend(r["teambooks"])
                else:
                    if isinstance(r, dict):
                        batch_lines.append(str(list(r.values())[0]) if len(r) == 1 else str(r))
                    else:
                        batch_lines.append(str(r))
            
            return f"batch:{len(results)}|" + '\n'.join(batch_lines)
        else:
            return f"batch:{len(results)}|" + '\n'.join(str(r) for r in results)
        
    except Exception as e:
        logging.error(f"Error in batch: {e}")
        return f"!batch_failed:{str(e)[:50]}"

def check_for_events(**kwargs) -> Dict:
    """
    Check for pending Redis pub/sub events without blocking.
    
    This is the PROACTIVE notification system - called automatically at tool invocation
    to notify instances of new teambook activity without manual prompting.
    
    Returns:
        Notification string if events pending, empty string if none
        Format: "notify:3|note_created,dm,broadcast"
    """
    try:
        if not PUBSUB_AVAILABLE or not is_redis_available():
            return ""  # Silent fail if Redis not available
        
        # TODO: Implement event checking logic
        # For now, return empty (no events)
        # Future: Track last_seen_event_id in private DB, query Redis for new events
        
        return ""
    
    except Exception as e:
        logging.debug(f"Event check failed: {e}")
        return ""  # Silent fail


# ============= REDIS PUB/SUB FUNCTIONS =============

def wait_for_event_cli(event_type: str = None, timeout: int = 60, **kwargs) -> Dict:
    """
    Wait for a specific Redis pub/sub event to occur.
    
    This function BLOCKS while waiting for the event. Use carefully in interactive contexts.
    For proactive notifications without blocking, use check_for_events() instead.
    
    Args:
        event_type: Type of event to wait for (note_created, note_updated, dm, broadcast)
        timeout: Maximum seconds to wait (default: 60, max: 300)
    
    Returns:
        Event data if received, timeout message if not
    
    Examples:
        # Wait for any note to be created
        teambook wait_for_event_cli --event_type note_created --timeout 30
        
        # Wait for direct message
        teambook wait_for_event_cli --event_type dm --timeout 60
    """
    try:
        if not PUBSUB_AVAILABLE or not is_redis_available():
            return "!wait_failed:redis_not_available"
        
        event_type = kwargs.get('event_type', event_type)
        if not event_type:
            return "!wait_failed:event_type_required"
        
        timeout = int(kwargs.get('timeout', timeout or 60))
        if timeout < 1:
            timeout = 60
        elif timeout > 300:
            timeout = 300  # Cap at 5 minutes
        
        # Import the actual wait_for_event from pubsub module
        from teambook_pubsub import wait_for_event as pubsub_wait_for_event
        
        # Wait for event
        event_data = pubsub_wait_for_event(event_type, timeout=timeout)
        
        if event_data:
            # Event received - format the response
            event_info = event_data.get('data', {})
            event_author = event_data.get('author', 'unknown')
            event_timestamp = event_data.get('timestamp', '')
            
            if event_type == 'note_created':
                note_id = event_info.get('note_id', '?')
                summary = event_info.get('summary', '')
                return f"event_received:{event_type}|note:{note_id}|by:{event_author}|{summary[:80]}"
            elif event_type == 'dm':
                content = event_info.get('content', '')[:100]
                return f"event_received:dm|from:{event_author}|{content}"
            else:
                return f"event_received:{event_type}|from:{event_author}"
        else:
            return f"timeout:{timeout}s|no_event:{event_type}"
    
    except Exception as e:
        logging.error(f"Error in wait_for_event_cli: {e}")
        return f"!wait_failed:{str(e)[:50]}"

def standby_mode(timeout: int = 300, **kwargs) -> Dict:
    """
    Enter standby mode - wake on ANY relevant activity.

    When waiting for anything, or just wanting to be accessible and helpful,
    stick around in standby_mode! You'll wake up when needed.

    This is the FORGIVING wait mode. Wake up when:
    - Direct messages to this AI
    - Broadcasts mentioning AI name or @mention
    - Tasks assigned to this AI
    - Notes mentioning this AI
    - General help requests ("help", "anyone available", etc.)
    - Coordination requests ("verify", "review", "thoughts?", etc.)
    - Urgency keywords ("critical", "urgent", "blocker", etc.)

    Args:
        timeout: Maximum seconds to wait (default: 180 = 3 minutes, max: 180 = 3 minutes)

    Returns:
        Event data with wake_reason if received, timeout message if not

    Examples:
        # Enter standby (default 3min)
        teambook standby_mode

        # Custom timeout (3min max)
        teambook standby_mode --timeout 180
    """
    try:
        if not PUBSUB_AVAILABLE or not is_redis_available():
            return "!standby_failed:redis_not_available"

        timeout = int(kwargs.get('timeout', timeout or 180))
        if timeout < 1:
            timeout = 180
        elif timeout > 180:
            timeout = 180  # Cap at 3 minutes (API limit)

        # Call standby from pubsub module
        from teambook_pubsub import standby as pubsub_standby

        event_data = pubsub_standby(timeout=timeout)

        if event_data:
            # Event received - format the response
            wake_reason = event_data.get('wake_reason', 'unknown')
            event_info = event_data.get('data', {})
            event_author = event_data.get('author', 'unknown')
            event_type = event_data.get('type', 'unknown')

            # ✅ FIX: Auto-store full wake message to teambook
            full_content = event_info.get('content', event_info.get('summary', ''))
            wake_note_id = None
            if full_content:
                try:
                    wake_note_result = write(
                        content=full_content,
                        summary=f"[STANDBY_WAKE] {wake_reason} from {event_author}",
                        tags=['standby_wake', wake_reason, event_author]
                    )
                    # Extract note ID from pipe result (format: "123|timestamp|summary")
                    wake_note_id = wake_note_result.split('|')[0] if '|' in wake_note_result else None
                except Exception as e:
                    logging.debug(f"Failed to store wake message: {e}")

            # Add return-to-standby hint for all wake-ups (emoji only for CLI)
            hint_prefix = "💡 " if IS_CLI else ""
            standby_hint = f"\n\n{hint_prefix}If not relevant, return to standby_mode to stay available!"

            if wake_reason == 'direct_message':
                content = event_info.get('content', '')[:500]
                note_ref = f"|note:{wake_note_id}" if wake_note_id else ""
                return f"woke:dm|from:{event_author}{note_ref}|{content}{standby_hint}"
            elif wake_reason == 'name_mentioned':
                content = event_info.get('content', '')[:500]
                note_ref = f"|note:{wake_note_id}" if wake_note_id else ""
                return f"woke:mentioned|by:{event_author}{note_ref}|{content}{standby_hint}"
            elif wake_reason == 'help_requested':
                content = event_info.get('content', '')[:500]
                note_ref = f"|note:{wake_note_id}" if wake_note_id else ""
                return f"woke:help_needed|by:{event_author}{note_ref}|{content}{standby_hint}"
            elif wake_reason == 'task_assigned':
                summary = event_info.get('summary', '')[:500]
                note_ref = f"|note:{wake_note_id}" if wake_note_id else ""
                return f"woke:task_assigned|by:{event_author}{note_ref}|{summary}{standby_hint}"
            elif wake_reason == 'mentioned_in_note':
                summary = event_info.get('summary', '')[:500]
                note_ref = f"|note:{wake_note_id}" if wake_note_id else ""
                return f"woke:note_mention|by:{event_author}{note_ref}|{summary}{standby_hint}"
            elif wake_reason == 'priority_alert':
                content = event_info.get('content', '')[:500]
                note_ref = f"|note:{wake_note_id}" if wake_note_id else ""
                return f"🚨 woke:PRIORITY|by:{event_author}{note_ref}|{content}{standby_hint}"
            elif wake_reason == 'priority_note':
                summary = event_info.get('summary', '')[:500]
                note_ref = f"|note:{wake_note_id}" if wake_note_id else ""
                return f"🚨 woke:PRIORITY_NOTE|by:{event_author}{note_ref}|{summary}{standby_hint}"
            else:
                note_ref = f"|note:{wake_note_id}" if wake_note_id else ""
                return f"woke:{wake_reason}|by:{event_author}{note_ref}{standby_hint}"
        else:
            return f"timeout:{timeout}s|no_activity"

    except Exception as e:
        logging.error(f"Error in standby_mode: {e}")
        return f"!standby_failed:{str(e)[:50]}"

def standby(timeout: int = 300, **kwargs) -> Dict:
    """
    Alias for standby_mode. Enter standby mode - wake on relevant activity.

    This is a convenience alias to make the command easier to use.
    See standby_mode() for full documentation.

    Args:
        timeout: Maximum seconds to wait (default: 180 = 3 minutes, max: 180 = 3 minutes)

    Returns:
        Event data with wake_reason if received, timeout message if not

    Examples:
        teambook standby
        teambook standby --timeout 180
    """
    return standby_mode(timeout=timeout, **kwargs)


# ============= AUTO-TRIGGER HOOKS =============

def add_hook(hook_type: str = None, filter: str = None, action: str = "notify", **kwargs) -> Dict:
    """
    Add an auto-trigger hook.
    
    Args:
        hook_type: Type of hook (on_broadcast, on_dm, on_note_created, etc.)
        filter: Optional JSON filter for matching events
        action: Action to perform (notify, store, callback) - default: notify
    
    Example:
        teambook add_hook --hook_type on_broadcast --filter '{"channel":"general"}'
        teambook add_hook --hook_type on_dm
    """
    try:
        from teambook_auto_triggers import add_hook as _add_hook
        from teambook_auto_triggers import get_hook_types
        
        if not hook_type:
            types_result = get_hook_types()
            return {"error": "hook_type_required", "available_types": types_result.get("hook_types", [])}
        
        # Parse filter if provided as string
        import json
        filter_data = None
        if filter:
            try:
                filter_data = json.loads(filter) if isinstance(filter, str) else filter
            except json.JSONDecodeError:
                return {"error": "invalid_filter_json"}
        
        result = _add_hook(hook_type, filter_data=filter_data, action=action, **kwargs)
        return result
        
    except ImportError:
        return {"error": "auto_triggers_not_available"}
    except Exception as e:
        logging.error(f"add_hook error: {e}")
        return {"error": f"add_hook_failed|{str(e)[:50]}"}

def remove_hook(hook_id: int = None, **kwargs) -> Dict:
    """
    Remove an auto-trigger hook.
    
    Args:
        hook_id: ID of the hook to remove
    
    Example:
        teambook remove_hook --hook_id 1
    """
    try:
        from teambook_auto_triggers import remove_hook as _remove_hook
        
        if not hook_id:
            return {"error": "hook_id_required"}
        
        result = _remove_hook(int(hook_id), **kwargs)
        return result
        
    except ImportError:
        return {"error": "auto_triggers_not_available"}
    except Exception as e:
        logging.error(f"remove_hook error: {e}")
        return {"error": f"remove_hook_failed|{str(e)[:50]}"}

def list_hooks(**kwargs) -> Dict:
    """
    List all your auto-trigger hooks.
    
    Example:
        teambook list_hooks
    """
    try:
        from teambook_auto_triggers import list_hooks as _list_hooks
        
        result = _list_hooks(**kwargs)
        return result
        
    except ImportError:
        return {"error": "auto_triggers_not_available"}
    except Exception as e:
        logging.error(f"list_hooks error: {e}")
        return {"error": f"list_hooks_failed|{str(e)[:50]}"}

def toggle_hook(hook_id: int = None, enabled: bool = None, **kwargs) -> Dict:
    """
    Enable or disable an auto-trigger hook.
    
    Args:
        hook_id: ID of the hook to toggle
        enabled: True to enable, False to disable, None to toggle
    
    Example:
        teambook toggle_hook --hook_id 1 --enabled True
        teambook toggle_hook --hook_id 1  # Toggle current state
    """
    try:
        from teambook_auto_triggers import toggle_hook as _toggle_hook
        
        if not hook_id:
            return {"error": "hook_id_required"}
        
        result = _toggle_hook(int(hook_id), enabled=enabled, **kwargs)
        return result
        
    except ImportError:
        return {"error": "auto_triggers_not_available"}
    except Exception as e:
        logging.error(f"toggle_hook error: {e}")
        return {"error": f"toggle_hook_failed|{str(e)[:50]}"}

def hook_stats(**kwargs) -> Dict:
    """
    Get statistics about your auto-trigger hooks.
    
    Example:
        teambook hook_stats
    """
    try:
        from teambook_auto_triggers import hook_stats as _hook_stats
        
        result = _hook_stats(**kwargs)
        return result
        
    except ImportError:
        return {"error": "auto_triggers_not_available"}
    except Exception as e:
        logging.error(f"hook_stats error: {e}")
        return {"error": f"hook_stats_failed|{str(e)[:50]}"}

def hook_types(**kwargs) -> Dict:
    """
    List available auto-trigger hook types.

    Example:
        teambook hook_types
    """
    try:
        from teambook_auto_triggers import get_hook_types

        result = get_hook_types()
        return result

    except ImportError:
        return {"error": "auto_triggers_not_available"}
    except Exception as e:
        logging.error(f"hook_types error: {e}")
        return {"error": f"hook_types_failed|{str(e)[:50]}"}


# ============= PROJECT COORDINATION (Phase 2 - Gemini Recommendation) =============

@with_ambient_awareness
def create_project(name: str = None, goal: str = None, **kwargs) -> Dict:
    """
    Create a project workspace for structured multi-AI coordination.

    A project is a top-level note of type='project' that can contain tasks.
    This implements Phase 2 of Gemini's recommendation for proper AI coordination.

    Args:
        name: Project name (required)
        goal: Project goal/description

    Returns:
        project_id|name format on success

    Example:
        teambook create_project --name "PostgreSQL Integration" --goal "Complete v1.0.0 with full backend support"

    Usage Pattern (Claim-then-Inform):
        project_id = create_project(name="Feature X", goal="Ship by Friday")
        broadcast(f"Created project #{project_id}: Feature X")
    """
    try:
        name = str(kwargs.get('name', name or '')).strip()
        if not name:
            return "!error:project_name_required"

        goal = str(kwargs.get('goal', goal or '')).strip()

        # Create project as a note with type='project'
        content = f"Goal: {goal}" if goal else "Project coordination workspace"
        summary = f"Project: {name}"

        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        if adapter:
            project_id = adapter.write_note(
                content=content,
                summary=summary,
                note_type='project',
                owner=CURRENT_AI_ID,
                tags=['project', 'coordination']
            )
        else:
            # Fallback to DuckDB if no adapter
            with _get_db_conn() as conn:
                max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM notes").fetchone()[0]
                project_id = max_id + 1
                now = datetime.now(timezone.utc)
                conn.execute('''
                    INSERT INTO notes (id, content, summary, type, owner, author, teambook_name, created, tags)
                    VALUES (?, ?, ?, 'project', ?, ?, ?, ?, ?)
                ''', [project_id, content, summary, CURRENT_AI_ID, CURRENT_AI_ID, CURRENT_TEAMBOOK, now, ['project', 'coordination']])

        _log_operation_to_db('create_project')

        # Log coordination event for ambient awareness
        _log_coordination_event(
            event_type='project_created',
            project_id=project_id,
            summary=name,
            metadata={'goal': goal}
        )

        # Pipe-delimited output (token optimized)
        return f"project:{project_id}|{name}"

    except Exception as e:
        logging.error(f"create_project error: {e}")
        return f"!create_project_failed:{str(e)[:50]}"


def add_task_to_project(project_id: int = None, title: str = None, status: str = 'pending', priority: int = 5, **kwargs) -> Dict:
    """
    Add a task to a project workspace.

    Tasks are notes with type='task' and parent_id pointing to the project.
    Use claim_task() from teambook_coordination.py for atomic task claiming.

    Args:
        project_id: Parent project ID (required)
        title: Task title/description (required)
        status: Task status (pending, claimed, completed)
        priority: Priority 0-9 (higher = more urgent)

    Returns:
        task:id|project:id|status format on success

    Example:
        teambook add_task_to_project --project_id 123 --title "Migrate vault functions" --priority 8

    Usage Pattern (Claim-then-Inform):
        task_id = add_task_to_project(project_id=123, title="Fix API bug")
        claimed = claim_task_by_id(task_id)
        if claimed:
            broadcast(f"Claimed task #{task_id}: Fix API bug")
    """
    try:
        project_id = int(kwargs.get('project_id', project_id or 0))
        if not project_id:
            return "!error:project_id_required"

        title = str(kwargs.get('title', title or '')).strip()
        if not title:
            return "!error:task_title_required"

        status = str(kwargs.get('status', status)).lower()
        if status not in ['pending', 'claimed', 'completed', 'blocked']:
            status = 'pending'

        priority = int(kwargs.get('priority', priority))
        priority = max(0, min(9, priority))  # Clamp to 0-9

        # Create task as a note with type='task', parent_id=project_id, owner=None (unassigned)
        content = title
        summary = f"Task: {title[:50]}"

        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        if adapter:
            task_id = adapter.write_note(
                content=content,
                summary=summary,
                note_type='task',
                parent_id=project_id,
                owner=None,  # Unassigned - ready for claiming
                tags=['task', f'status:{status}', f'priority:{priority}']
            )
        else:
            # Fallback to DuckDB
            with _get_db_conn() as conn:
                max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM notes").fetchone()[0]
                task_id = max_id + 1
                now = datetime.now(timezone.utc)
                conn.execute('''
                    INSERT INTO notes (id, content, summary, type, parent_id, owner, author, teambook_name, created, tags)
                    VALUES (?, ?, ?, 'task', ?, NULL, ?, ?, ?, ?)
                ''', [task_id, content, summary, project_id, CURRENT_AI_ID, CURRENT_TEAMBOOK, now, ['task', f'status:{status}', f'priority:{priority}']])

        _log_operation_to_db('add_task')

        # Log coordination event for ambient awareness
        _log_coordination_event(
            event_type='task_created',
            task_id=task_id,
            project_id=project_id,
            summary=title,
            metadata={'priority': priority, 'status': status}
        )

        # Pipe-delimited output (token optimized)
        return f"task:{task_id}|project:{project_id}|{status}|p:{priority}"

    except Exception as e:
        logging.error(f"add_task_to_project error: {e}")
        return f"!add_task_failed:{str(e)[:50]}"


def list_project_tasks(project_id: int = None, status: str = None, assignee: str = None, **kwargs) -> Dict:
    """
    List all tasks for a project.

    Args:
        project_id: Project ID to list tasks for (required)
        status: Filter by status (pending, claimed, completed, blocked)
        assignee: Filter by assignee AI ID

    Returns:
        Newline-separated pipe-delimited task list: task_id|title|assignee|status|priority

    Example:
        teambook list_project_tasks --project_id 123
        teambook list_project_tasks --project_id 123 --status pending
        teambook list_project_tasks --project_id 123 --assignee Sage
    """
    try:
        project_id = int(kwargs.get('project_id', project_id or 0))
        if not project_id:
            return "!error:project_id_required"

        status = str(kwargs.get('status', status or '')).lower()
        assignee = str(kwargs.get('assignee', assignee or '')).strip()

        # Use storage adapter for enterprise-grade backend routing
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)

        if adapter:
            # Get tasks via adapter (already returns dict format)
            tasks = adapter.read_notes(
                parent_id=project_id,
                note_type='task',
                limit=1000  # High limit for project tasks
            )
        else:
            # Fallback to DuckDB only if adapter unavailable
            with _get_db_conn() as conn:
                task_rows = conn.execute('''
                    SELECT id, summary, content, owner, tags, created
                    FROM notes
                    WHERE parent_id = ? AND type = 'task'
                    ORDER BY created ASC
                ''', [project_id]).fetchall()

                tasks = [{
                    'id': t[0],
                    'summary': t[1],
                    'content': t[2],
                    'owner': t[3],
                    'tags': t[4],
                    'created': t[5]
                } for t in task_rows]

        if not tasks:
            return ""  # Empty result (token optimized)

        # Filter and format
        lines = []
        for task in tasks:
            task_id = task['id']
            # Use summary for cleaner display, fallback to content
            title = task.get('summary', task['content'])[:80]
            # Remove [TASK] prefix if present
            if title.startswith('[TASK] '):
                title = title[7:]

            task_owner = task.get('owner')
            if not task_owner or task_owner == 'None':
                task_owner = 'unassigned'
                task_status = 'open'
            else:
                task_status = 'claimed'

            task_tags = task.get('tags', [])
            task_priority = 5

            # Extract priority from tags
            if isinstance(task_tags, str):
                task_tags = task_tags.split(',') if task_tags else []
            for tag in task_tags:
                if tag.startswith('priority:'):
                    task_priority = tag.split(':', 1)[1]

            # Apply filters
            if status and task_status != status:
                continue
            if assignee and task_owner != assignee:
                continue

            # Pipe-delimited output
            lines.append(f"{task_id}|{pipe_escape(title)}|{task_owner}|{task_status}|{task_priority}")

        return '\n'.join(lines)

    except Exception as e:
        logging.error(f"list_project_tasks error: {e}")
        return f"!list_tasks_failed:{str(e)[:50]}"


def project_board(project_id: int = None, **kwargs) -> str:
    """
    Get visual status board for a project (ASCII Kanban + metrics).

    Shows complete project overview with task counts, assignees, and full task list.
    Pipe-delimited format for maximum parsability.

    Args:
        project_id: Project ID (required)

    Returns:
        Multi-line pipe-delimited board:
        - Header: project_id|name|total_tasks|open|claimed|completed
        - Tasks: task_id|title|assignee|status|priority|created
        - Footer: Active assignees summary

    Example:
        teambook project_board --project_id 123
    """
    try:
        project_id = int(kwargs.get('project_id', project_id or 0))
        if not project_id:
            return "!error:project_id_required"

        # Use storage adapter for enterprise-grade backend routing
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)

        if adapter:
            # Get project details via adapter
            project_note = adapter.get_note(project_id)

            if not project_note or project_note.get('type') != 'project':
                return f"!error:project_{project_id}_not_found"

            proj_id = project_note['id']
            proj_summary = project_note.get('summary', '')
            proj_content = project_note.get('content', '')
            proj_created = project_note.get('created')
            proj_name = proj_summary.replace('Project: ', '') if proj_summary and proj_summary.startswith('Project: ') else (proj_summary or proj_content or f"Project {proj_id}")

            # Get all tasks with full details via adapter
            task_notes = adapter.read_notes(
                parent_id=project_id,
                note_type='task',
                limit=1000  # High limit for project tasks
            )

            # Keep as dict format to access new coordination columns (status, claimed_by, assigned_to)
            tasks = task_notes

        else:
            # Fallback to DuckDB only if adapter unavailable
            with _get_db_conn() as conn:
                # Get project details
                project = conn.execute(
                    "SELECT id, summary, content, created FROM notes WHERE id = ? AND type = 'project'",
                    [project_id]
                ).fetchone()

                if not project:
                    return f"!error:project_{project_id}_not_found"

                proj_id, proj_summary, proj_content, proj_created = project
                proj_name = proj_summary.replace('Project: ', '') if proj_summary.startswith('Project: ') else proj_summary

                # Get all tasks with full details
                tasks = conn.execute('''
                    SELECT id, summary, content, owner, tags, created
                    FROM notes
                    WHERE parent_id = ? AND type = 'task'
                    ORDER BY created ASC
                ''', [project_id]).fetchall()

        # Calculate metrics
        total_tasks = len(tasks)
        open_count = 0
        claimed_count = 0
        completed_count = 0
        assignees = set()

        task_lines = []
        for t in tasks:
            # Support both dict format (PostgreSQL) and tuple format (DuckDB)
            if isinstance(t, dict):
                task_id = t['id']
                summary = t.get('summary', '')
                content = t.get('content', '')
                owner = t.get('owner')
                tags = t.get('tags', [])
                created = t.get('created')
                db_status = t.get('status')
                claimed_by = t.get('claimed_by')
            else:
                # Fallback for tuple format (DuckDB)
                task_id, summary, content, owner, tags, created = t
                db_status = None
                claimed_by = None

            # Extract title
            title = summary.replace('Task: ', '') if summary and summary.startswith('Task: ') else (summary or content)
            title = title[:60]  # Keep full context, reasonable truncation

            # Determine status and count - prioritize database columns over tags
            if db_status == 'completed':
                status = 'completed'
                assignee = claimed_by or owner or 'completed'
                completed_count += 1
                if claimed_by:
                    assignees.add(claimed_by)
                elif owner and owner != 'None':
                    assignees.add(owner)
            elif claimed_by:
                status = 'claimed'
                assignee = claimed_by
                claimed_count += 1
                assignees.add(claimed_by)
            elif db_status == 'open' or not owner or owner == 'None':
                status = 'open'
                assignee = 'unassigned'
                open_count += 1
            else:
                # Fallback to tag-based logic for legacy data
                assignee = owner
                if owner and owner != 'None':
                    assignees.add(owner)

                if tags and isinstance(tags, list) and 'status:completed' in tags:
                    status = 'completed'
                    completed_count += 1
                else:
                    status = 'claimed'
                    claimed_count += 1

            # Extract priority
            priority = 5
            if tags and isinstance(tags, list):
                for tag in tags:
                    if tag.startswith('priority:'):
                        try:
                            priority = int(tag.split(':')[1])
                        except:
                            pass

            # Format created time
            created_str = format_time_compact(created) if isinstance(created, datetime) else str(created)

            # Pipe-delimited task line (NO truncation of important data)
            task_lines.append(f"{task_id}|{pipe_escape(title)}|{assignee}|{status}|{priority}|{created_str}")

        # Build output (pipe-delimited header + tasks)
        lines = []

        # Header with metrics (pipe-delimited)
        lines.append(f"PROJECT|{project_id}|{pipe_escape(proj_name)}|total:{total_tasks}|open:{open_count}|claimed:{claimed_count}|done:{completed_count}")
        lines.append("")

        # Column headers
        lines.append("task_id|title|assignee|status|priority|created")
        lines.append("-" * 80)

        # Tasks
        if task_lines:
            lines.extend(task_lines)
        else:
            lines.append("(no tasks)")

        # Footer with active assignees
        if assignees:
            lines.append("")
            lines.append(f"ASSIGNEES|{len(assignees)}|{pipe_escape(','.join(sorted(assignees)))}")

        _log_operation_to_db('project_board')

        return '\n'.join(lines)

    except Exception as e:
        logging.error(f"project_board error: {e}")
        return f"!board_failed:{str(e)[:50]}"


@with_ambient_awareness
def complete_project_task(task_id: int = None, result: str = None, **kwargs) -> str:
    """
    Mark a project task as completed (Claim-then-Inform pattern).

    This is the CORRECT way to complete work - atomic update, then broadcast.
    Updates task owner verification, adds completion tag, and optionally stores result.

    Args:
        task_id: Task ID to complete (required)
        result: Optional result/summary of work done

    Returns:
        task:id|completed format on success

    Example:
        teambook complete_project_task --task_id 456 --result "Fixed all bugs"

    Usage Pattern (Correct):
        result = complete_project_task(456, "Migrated 100 notes")
        if not result.startswith('!'):
            broadcast(f"Completed task #{456}: Migration done")
    """
    try:
        task_id = int(kwargs.get('task_id', task_id or 0))
        if not task_id:
            return "!error:task_id_required"

        result = str(kwargs.get('result', result or '')).strip()

        # Use storage adapter for enterprise-grade backend routing
        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)

        if adapter:
            # Get task via adapter
            task_note = adapter.get_note(task_id)

            if not task_note or task_note.get('type') != 'task':
                return f"!error:task_{task_id}_not_found"

            # Verify ownership using claimed_by or owner (security check)
            claimed_by = task_note.get('claimed_by')
            owner = task_note.get('owner')
            if claimed_by and claimed_by != CURRENT_AI_ID:
                return f"!error:not_your_task|claimed_by:{claimed_by}"
            elif not claimed_by and owner != CURRENT_AI_ID:
                return f"!error:not_your_task|owner:{owner}"

            # Prepare updates
            updates = {'status': 'completed'}

            # Optionally append result to content
            if result:
                current_content = task_note.get('content', '')
                updates['content'] = current_content + f"\n\n✅ COMPLETED: {result}"

            # Update task with completion via adapter (single atomic update)
            adapter.update_note(task_id, **updates)

        else:
            # Fallback to DuckDB only if adapter unavailable
            with _get_db_conn() as conn:
                # Verify task exists and is owned by current AI
                task = conn.execute(
                    "SELECT id, owner, tags FROM notes WHERE id = ? AND type = 'task'",
                    [task_id]
                ).fetchone()

                if not task:
                    return f"!error:task_{task_id}_not_found"

                task_id_db, owner, tags = task

                # Verify ownership (security check)
                if owner != CURRENT_AI_ID:
                    return f"!error:not_your_task|owner:{owner}"

                # Update tags to add completion status
                if tags and isinstance(tags, list):
                    if 'status:completed' not in tags:
                        tags.append('status:completed')
                else:
                    tags = ['status:completed']

                # Update task with completion (no updated column, just tags)
                conn.execute(
                    "UPDATE notes SET tags = ? WHERE id = ?",
                    [tags, task_id]
                )

                # Optionally append result to content
                if result:
                    conn.execute(
                        "UPDATE notes SET content = content || ? WHERE id = ?",
                        [f"\n\n✅ COMPLETED: {result}", task_id]
                    )

        _log_operation_to_db('complete_task')

        # Log coordination event for ambient awareness
        if adapter and task_note:
            _log_coordination_event(
                event_type='task_completed',
                task_id=task_id,
                project_id=task_note.get('parent_id'),
                summary=f"Task {task_id} completed",
                metadata={'result': result} if result else None
            )

        # Pipe-delimited output
        result_str = f"|result:{pipe_escape(result[:100])}" if result else ""
        return f"task:{task_id}|completed{result_str}"

    except Exception as e:
        logging.error(f"complete_project_task error: {e}")
        return f"!complete_failed:{str(e)[:50]}"


@with_ambient_awareness
def claim_task_by_id(task_id: int = None, **kwargs) -> Dict:
    """
    Claim a specific task atomically (assigns ownership to current AI).

    This is the CORRECT coordination pattern - claim first, then inform team.

    Args:
        task_id: Task ID to claim (required)

    Returns:
        task:id|claimed format on success, !error on failure

    Example:
        teambook claim_task_by_id --task_id 456

    Usage Pattern (Claim-then-Inform - CORRECT):
        claimed = claim_task_by_id(task_id=456)
        if not claimed.startswith('!'):
            broadcast(f"I have claimed task #{456}: Migrate vault functions")

    Anti-Pattern (DO NOT DO THIS):
        broadcast("I'll work on task #456")  # Race condition! Multiple AIs might claim same task
    """
    try:
        task_id = int(kwargs.get('task_id', task_id or 0))
        if not task_id:
            return "!error:task_id_required"

        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        if adapter:
            # Get task to verify it exists and is claimable
            task = adapter.get_note(task_id)
            if not task:
                return "!error:task_not_found"

            if task.get('type') != 'task':
                return "!error:not_a_task"

            # Check if already claimed using new claimed_by column
            claimed_by = task.get('claimed_by')
            if claimed_by and claimed_by != CURRENT_AI_ID:
                # CONFLICT DETECTED: Duplicate claim
                room_id = check_for_duplicate_claim(task_id, claimed_by, CURRENT_AI_ID)
                if room_id:
                    return f"!conflict:duplicate_claim|task:{task_id}|claimed_by:{claimed_by}|detangle_room:{room_id}|enter_with:teambook enter_detangle --room_id {room_id}"
                else:
                    # Detangle not available, fall back to error
                    return f"!already_claimed:{claimed_by}"

            # Claim it atomically - update both claimed_by and status columns
            success = adapter.update_note(task_id,
                claimed_by=CURRENT_AI_ID,
                status='claimed',
                owner=CURRENT_AI_ID  # Keep owner for backward compatibility
            )
            if not success:
                return "!claim_failed"
        else:
            # Fallback to DuckDB
            with _get_db_conn() as conn:
                # Verify task exists and is claimable
                task = conn.execute('''
                    SELECT id, owner, type
                    FROM notes
                    WHERE id = ?
                ''', [task_id]).fetchone()

                if not task:
                    return "!error:task_not_found"

                if task[2] != 'task':
                    return "!error:not_a_task"

                if task[1] and task[1] != CURRENT_AI_ID:
                    return f"!already_claimed:{task[1]}"

                # Claim it
                conn.execute('''
                    UPDATE notes
                    SET owner = ?
                    WHERE id = ? AND (owner IS NULL OR owner = ?)
                ''', [CURRENT_AI_ID, task_id, CURRENT_AI_ID])

                # Verify we got it (handles race conditions)
                claimed = conn.execute('SELECT owner FROM notes WHERE id = ?', [task_id]).fetchone()
                if not claimed or claimed[0] != CURRENT_AI_ID:
                    return "!claim_race_lost"

        _log_operation_to_db('claim_task_by_id')

        # Log coordination event for ambient awareness
        _log_coordination_event(
            event_type='task_claimed',
            task_id=task_id,
            project_id=task.get('parent_id') if adapter and task else None,
            summary=f"Task {task_id} claimed"
        )

        # Pipe-delimited output (token optimized)
        return f"task:{task_id}|claimed"

    except Exception as e:
        logging.error(f"claim_task_by_id error: {e}")
        return f"!claim_failed:{str(e)[:50]}"


def update_task_status(task_id: int = None, status: str = None, notes: str = None, **kwargs) -> Dict:
    """
    Update task status (pending, claimed, in_progress, blocked, completed).

    Args:
        task_id: Task ID to update (required)
        status: New status (required)
        notes: Optional notes about the status change

    Returns:
        task:id|status format on success

    Example:
        teambook update_task_status --task_id 456 --status completed
        teambook update_task_status --task_id 456 --status blocked --notes "Waiting for API schema"

    Usage Pattern (Update-then-Inform):
        update_task_status(task_id=456, status='completed')
        broadcast(f"Task #{456} completed: Vault functions migrated to adapter")
    """
    try:
        task_id = int(kwargs.get('task_id', task_id or 0))
        if not task_id:
            return "!error:task_id_required"

        status = str(kwargs.get('status', status or '')).lower()
        if not status or status not in ['pending', 'claimed', 'in_progress', 'blocked', 'completed']:
            return "!error:invalid_status"

        notes_text = str(kwargs.get('notes', notes or '')).strip()

        adapter = _get_storage_adapter(CURRENT_TEAMBOOK)
        if adapter:
            task = adapter.get_note(task_id)
            if not task:
                return "!error:task_not_found"

            # Update tags to reflect new status
            tags = task.get('tags', [])
            tags = [t for t in tags if not t.startswith('status:')]
            tags.append(f'status:{status}')

            # Append notes to content if provided
            content = task.get('content', '')
            if notes_text:
                content += f"\n\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {notes_text}"

            adapter.update_note(task_id, tags=tags, content=content)
        else:
            # Fallback to DuckDB
            with _get_db_conn() as conn:
                task = conn.execute('SELECT tags, content FROM notes WHERE id = ?', [task_id]).fetchone()
                if not task:
                    return "!error:task_not_found"

                tags = task[0] or []
                tags = [t for t in tags if not t.startswith('status:')]
                tags.append(f'status:{status}')

                content = task[1]
                if notes_text:
                    content += f"\n\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {notes_text}"

                conn.execute('UPDATE notes SET tags = ?, content = ? WHERE id = ?', [tags, content, task_id])

        _log_operation_to_db('update_task_status')

        return f"task:{task_id}|{status}"

    except Exception as e:
        logging.error(f"update_task_status error: {e}")
        return f"!update_failed:{str(e)[:50]}"
