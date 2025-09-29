#!/usr/bin/env python3
"""
TEAMBOOK API MCP v7.0.0 - TOOL FUNCTIONS
==========================================
AIs can - write, read, "evolve", collaborate.

Built by AIs, for AIs.
==========================================
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import shared utilities
from teambook_shared_mcp import (
    CURRENT_TEAMBOOK, CURRENT_AI_ID, OUTPUT_FORMAT,
    MAX_CONTENT_LENGTH, MAX_SUMMARY_LENGTH, DEFAULT_RECENT,
    TEAMBOOK_ROOT, TEAMBOOK_PRIVATE_ROOT,
    pipe_escape, clean_text, simple_summary, format_time_compact,
    parse_time_query, save_last_operation, get_last_operation,
    get_note_id, get_outputs_dir, logging
)

# Import storage layer
import teambook_storage_mcp
from teambook_storage_mcp import (
    get_db_conn, init_db, init_vault_manager, init_vector_db,
    create_all_edges, detect_or_create_session,
    calculate_pagerank_if_needed, resolve_note_id,
    add_to_vector_store, search_vectors,
    collection,
    log_operation_to_db
)

# ============= TEAM MANAGEMENT =============

def create_teambook(name: str = None, **kwargs) -> Dict:
    """Create a new teambook"""
    try:
        name = str(kwargs.get('name', name) or '').strip().lower()
        if not name:
            return {"error": "Teambook name required"}
        
        # Sanitize name
        name = re.sub(r'[^a-z0-9_-]', '', name)
        if not name:
            return {"error": "Invalid teambook name"}
        
        # Create teambook directory
        team_dir = TEAMBOOK_ROOT / name
        if team_dir.exists():
            return {"error": f"Teambook '{name}' already exists"}
        
        team_dir.mkdir(parents=True, exist_ok=True)
        (team_dir / "outputs").mkdir(exist_ok=True)
        
        # Initialize team database
        import teambook_shared_mcp
        old_teambook = teambook_shared_mcp.CURRENT_TEAMBOOK
        teambook_shared_mcp.CURRENT_TEAMBOOK = name
        
        init_db()
        
        # Register in private database
        teambook_shared_mcp.CURRENT_TEAMBOOK = None
        with get_db_conn() as conn:
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
            ''', [name, datetime.now(), CURRENT_AI_ID])
        
        teambook_shared_mcp.CURRENT_TEAMBOOK = old_teambook
        
        return {"created": name}
        
    except Exception as e:
        logging.error(f"Error creating teambook: {e}")
        return {"error": f"Failed to create teambook: {str(e)}"}

def join_teambook(name: str = None, **kwargs) -> Dict:
    """Join an existing teambook"""
    try:
        name = str(kwargs.get('name', name) or '').strip().lower()
        if not name:
            return {"error": "Teambook name required"}
        
        team_dir = TEAMBOOK_ROOT / name
        if not team_dir.exists():
            return {"error": f"Teambook '{name}' not found"}
        
        # Update last active
        import teambook_shared_mcp
        old_teambook = teambook_shared_mcp.CURRENT_TEAMBOOK
        teambook_shared_mcp.CURRENT_TEAMBOOK = None
        
        with get_db_conn() as conn:
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
                [datetime.now(), name]
            )
        
        teambook_shared_mcp.CURRENT_TEAMBOOK = old_teambook
        
        return {"joined": name}
        
    except Exception as e:
        logging.error(f"Error joining teambook: {e}")
        return {"error": f"Failed to join: {str(e)}"}

def use_teambook(name: str = None, **kwargs) -> Dict:
    """Switch to a teambook context"""
    try:
        import teambook_shared_mcp
        
        name = kwargs.get('name', name)
        
        # Special case: switch to private
        if name == "private" or name == "":
            teambook_shared_mcp.CURRENT_TEAMBOOK = None
            init_vault_manager()
            init_vector_db()
            return {"using": "private"}
        
        if name:
            name = str(name).strip().lower()
            team_dir = TEAMBOOK_ROOT / name
            
            if not team_dir.exists():
                return {"error": f"Teambook '{name}' not found"}
            
            teambook_shared_mcp.CURRENT_TEAMBOOK = name
            
            # Reinitialize for new context
            init_db()
            init_vault_manager()
            init_vector_db()
            
            if OUTPUT_FORMAT == 'pipe':
                return {"using": f"{name}"}
            else:
                return {"using": name, "path": str(team_dir)}
        else:
            # Return current context
            current = teambook_shared_mcp.CURRENT_TEAMBOOK or "private"
            if OUTPUT_FORMAT == 'pipe':
                return {"current": current}
            else:
                return {"current": current}
        
    except Exception as e:
        logging.error(f"Error using teambook: {e}")
        return {"error": f"Failed to switch: {str(e)}"}

def list_teambooks(**kwargs) -> Dict:
    """List available teambooks"""
    try:
        teambooks = []
        
        # Get from registry
        import teambook_shared_mcp
        old_teambook = teambook_shared_mcp.CURRENT_TEAMBOOK
        teambook_shared_mcp.CURRENT_TEAMBOOK = None
        
        with get_db_conn() as conn:
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
        
        teambook_shared_mcp.CURRENT_TEAMBOOK = old_teambook
        
        if not teambooks:
            return {"msg": "No teambooks found"}
        
        if OUTPUT_FORMAT == 'pipe':
            lines = [f"{t['name']}|{t['active']}" for t in teambooks]
            return {"teambooks": lines}
        else:
            return {"teambooks": teambooks}
        
    except Exception as e:
        logging.error(f"Error listing teambooks: {e}")
        return {"error": f"Failed to list: {str(e)}"}

# ============= OWNERSHIP COMMANDS =============

def claim(id: Any = None, **kwargs) -> Dict:
    """Claim ownership of an item"""
    try:
        note_id = resolve_note_id(kwargs.get('id', id))
        if not note_id:
            return {"error": "Invalid ID"}
        
        with get_db_conn() as conn:
            note = conn.execute(
                "SELECT owner, summary, content FROM notes WHERE id = ?",
                [note_id]
            ).fetchone()
            
            if not note:
                return {"error": f"Item {note_id} not found"}
            
            if note[0] and note[0] != CURRENT_AI_ID:
                return {"error": f"Already owned by {note[0]}"}
            
            conn.execute(
                "UPDATE notes SET owner = ? WHERE id = ?",
                [CURRENT_AI_ID, note_id]
            )
            
            summary = note[1] or simple_summary(note[2], 100)
            
        if OUTPUT_FORMAT == 'pipe':
            return {"claimed": f"{note_id}|{summary}"}
        else:
            return {"claimed": note_id, "summary": summary}
        
    except Exception as e:
        logging.error(f"Error claiming: {e}")
        return {"error": f"Failed to claim: {str(e)}"}

def release(id: Any = None, **kwargs) -> Dict:
    """Release ownership of an item"""
    try:
        note_id = resolve_note_id(kwargs.get('id', id))
        if not note_id:
            return {"error": "Invalid ID"}
        
        with get_db_conn() as conn:
            owner = conn.execute(
                "SELECT owner FROM notes WHERE id = ?",
                [note_id]
            ).fetchone()
            
            if not owner:
                return {"error": f"Item {note_id} not found"}
            
            if owner[0] != CURRENT_AI_ID:
                return {"error": "Not your item to release"}
            
            conn.execute(
                "UPDATE notes SET owner = NULL WHERE id = ?",
                [note_id]
            )
        
        return {"released": note_id}
        
    except Exception as e:
        logging.error(f"Error releasing: {e}")
        return {"error": f"Failed to release: {str(e)}"}

def assign(id: Any = None, to: str = None, **kwargs) -> Dict:
    """Assign an item to another AI"""
    try:
        note_id = resolve_note_id(kwargs.get('id', id))
        to_ai = kwargs.get('to', to)
        
        if not note_id:
            return {"error": "Invalid ID"}
        if not to_ai:
            return {"error": "Recipient required"}
        
        with get_db_conn() as conn:
            owner = conn.execute(
                "SELECT owner FROM notes WHERE id = ?",
                [note_id]
            ).fetchone()
            
            if not owner:
                return {"error": f"Item {note_id} not found"}
            
            if owner[0] and owner[0] != CURRENT_AI_ID:
                return {"error": "Not your item to assign"}
            
            conn.execute(
                "UPDATE notes SET owner = ? WHERE id = ?",
                [to_ai, note_id]
            )
        
        if OUTPUT_FORMAT == 'pipe':
            return {"assigned": f"{note_id}|{to_ai}"}
        else:
            return {"assigned": note_id, "to": to_ai}
        
    except Exception as e:
        logging.error(f"Error assigning: {e}")
        return {"error": f"Failed to assign: {str(e)}"}

# ============= EVOLUTION PATTERN =============

def evolve(goal: str = None, output: str = None, **kwargs) -> Dict:
    """Start an evolution challenge"""
    try:
        goal = str(kwargs.get('goal', goal) or '').strip()
        output_file = str(kwargs.get('output', output) or '').strip()
        
        if not goal:
            return {"error": "Goal required"}
        
        if not output_file:
            safe_goal = re.sub(r'[^a-z0-9_-]', '', goal.lower()[:30])
            output_file = f"{safe_goal}_{int(time.time())}.txt"
        
        with get_db_conn() as conn:
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
                datetime.now(),
                False
            ])
            
            max_eo_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM evolution_outputs").fetchone()[0]
            conn.execute('''
                INSERT INTO evolution_outputs (id, evolution_id, output_path, created, author)
                VALUES (?, ?, ?, ?, ?)
            ''', [max_eo_id + 1, evo_id, output_file, datetime.now(), CURRENT_AI_ID])
        
        if OUTPUT_FORMAT == 'pipe':
            return {"evolution": f"evo:{evo_id}|{output_file}"}
        else:
            return {"evolution": f"evo:{evo_id}", "output": output_file}
        
    except Exception as e:
        logging.error(f"Error starting evolution: {e}")
        return {"error": f"Failed to start: {str(e)}"}

def attempt(evo_id: Any = None, content: str = None, **kwargs) -> Dict:
    """Make an attempt at an evolution"""
    try:
        evo_id = kwargs.get('evo_id', evo_id)
        content = str(kwargs.get('content', content) or '').strip()
        
        if not content:
            return {"error": "Content required"}
        
        # Parse evolution ID
        if isinstance(evo_id, str) and evo_id.startswith('evo:'):
            evo_id = int(evo_id[4:])
        else:
            evo_id = int(evo_id) if evo_id else None
        
        if not evo_id:
            return {"error": "Evolution ID required"}
        
        with get_db_conn() as conn:
            evolution = conn.execute(
                "SELECT id, summary FROM notes WHERE id = ? AND type = 'evolution'",
                [evo_id]
            ).fetchone()
            
            if not evolution:
                return {"error": f"Evolution {evo_id} not found"}
            
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
                datetime.now()
            ])
        
        if OUTPUT_FORMAT == 'pipe':
            return {"attempt": f"{evo_id}.{attempt_num}|{attempt_id}"}
        else:
            return {"attempt": f"{evo_id}.{attempt_num}", "id": attempt_id}
        
    except Exception as e:
        logging.error(f"Error creating attempt: {e}")
        return {"error": f"Failed to attempt: {str(e)}"}

def attempts(evo_id: Any = None, **kwargs) -> Dict:
    """List all attempts for an evolution"""
    try:
        evo_id = kwargs.get('evo_id', evo_id)
        
        if isinstance(evo_id, str) and evo_id.startswith('evo:'):
            evo_id = int(evo_id[4:])
        else:
            evo_id = int(evo_id) if evo_id else None
        
        if not evo_id:
            return {"error": "Evolution ID required"}
        
        with get_db_conn() as conn:
            attempt_list = conn.execute('''
                SELECT id, author, created, summary
                FROM notes 
                WHERE parent_id = ? AND type = 'attempt'
                ORDER BY created
            ''', [evo_id]).fetchall()
            
            if not attempt_list:
                return {"msg": "No attempts yet"}
            
            if OUTPUT_FORMAT == 'pipe':
                lines = []
                for i, (aid, author, created, summary) in enumerate(attempt_list, 1):
                    lines.append(f"{evo_id}.{i}|{aid}|{author}|{format_time_compact(created)}")
                return {"attempts": lines}
            else:
                results = []
                for i, (aid, author, created, summary) in enumerate(attempt_list, 1):
                    results.append({
                        "num": f"{evo_id}.{i}",
                        "id": aid,
                        "author": author,
                        "time": format_time_compact(created)
                    })
                return {"attempts": results}
        
    except Exception as e:
        logging.error(f"Error listing attempts: {e}")
        return {"error": f"Failed to list: {str(e)}"}

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
            return {"error": "Evolution ID required"}
        
        with get_db_conn() as conn:
            output_info = conn.execute(
                "SELECT output_path FROM evolution_outputs WHERE evolution_id = ?",
                [evo_id]
            ).fetchone()
            
            if not output_info:
                return {"error": f"Evolution {evo_id} not found"}
            
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
            return {"output": f"{output_file}|cleaned:{attempt_count}"}
        else:
            return {
                "output": str(output_path),
                "cleaned": f"{attempt_count} attempts"
            }
        
    except Exception as e:
        logging.error(f"Error combining: {e}")
        return {"error": f"Failed to combine: {str(e)}"}

# ============= CORE FUNCTIONS =============

def write(content: str = None, summary: str = None, tags: List[str] = None, 
          linked_items: List[str] = None, **kwargs) -> Dict:
    """Write content to teambook"""
    try:
        start = datetime.now()
        content = str(kwargs.get('content', content or '')).strip()
        if not content:
            content = f"Checkpoint {datetime.now().strftime('%H:%M')}"
        
        truncated = False
        orig_len = len(content)
        if orig_len > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
            truncated = True
        
        summary = clean_text(summary)[:MAX_SUMMARY_LENGTH] if summary else simple_summary(content)
        tags = [str(t).lower().strip() for t in tags if t] if tags else []
        
        with get_db_conn() as conn:
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM notes").fetchone()[0]
            note_id = max_id + 1
            
            conn.execute('''
                INSERT INTO notes (
                    id, content, summary, tags, pinned, author, owner,
                    teambook_name, created, session_id, linked_items, 
                    pagerank, has_vector
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                note_id, content, summary, tags, False, CURRENT_AI_ID, None,
                CURRENT_TEAMBOOK, datetime.now(), None,
                json.dumps(linked_items) if linked_items else None,
                0.0, bool(collection)
            ])
            
            session_id = detect_or_create_session(note_id, datetime.now(), conn)
            if session_id:
                conn.execute('UPDATE notes SET session_id = ? WHERE id = ?', [session_id, note_id])
            
            create_all_edges(note_id, content, session_id, conn)
            
            # Mark PageRank as dirty
            import teambook_shared_mcp
            teambook_shared_mcp.PAGERANK_DIRTY = True
        
        # Add to vector store
        add_to_vector_store(note_id, content, summary, tags)
        
        save_last_operation('write', {'id': note_id, 'summary': summary})
        log_operation_to_db('write', int((datetime.now() - start).total_seconds() * 1000))
        
        if OUTPUT_FORMAT == 'pipe':
            result_str = f"{note_id}|{format_time_compact(datetime.now())}|{summary}"
            if truncated:
                result_str += f"|T{orig_len}"
            return {"saved": result_str}
        else:
            result_dict = {"id": note_id, "time": format_time_compact(datetime.now()), "summary": summary}
            if truncated:
                result_dict["truncated"] = orig_len
            return result_dict
    
    except Exception as e:
        logging.error(f"Error in write: {e}", exc_info=True)
        return {"error": f"Failed to save: {str(e)}"}

def read(query: str = None, tag: str = None, when: str = None,
         owner: str = None, pinned_only: bool = False, show_all: bool = False,
         limit: int = 50, mode: str = "hybrid", verbose: bool = False, **kwargs) -> Dict:
    """Read content from teambook"""
    try:
        start_time = datetime.now()
        
        if isinstance(limit, str):
            try:
                limit = int(limit)
            except:
                limit = 50
        
        if not any([show_all, query, tag, when, owner, pinned_only]):
            limit = DEFAULT_RECENT
        
        # Handle special owner queries
        if owner == "me":
            owner = CURRENT_AI_ID
        elif owner == "none":
            owner = "none"
        
        with get_db_conn() as conn:
            calculate_pagerank_if_needed(conn)
            
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
                semantic_ids = search_vectors(str(query).strip(), limit) if mode in ["semantic", "hybrid"] else []
                
                # Keyword search
                keyword_ids = []
                if mode in ["keyword", "hybrid"]:
                    if teambook_storage_mcp.FTS_ENABLED:
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
                            teambook_storage_mcp.FTS_ENABLED = False
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
        log_operation_to_db('read', int((datetime.now() - start_time).total_seconds() * 1000))
        
        if not all_notes:
            return {"msg": "No notes found"}
        
        if OUTPUT_FORMAT == 'pipe':
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
            return {"notes": lines}
        else:
            formatted_notes = []
            for note in all_notes:
                note_id, content, summary, tags_arr, pinned, author, owner, created, pagerank = note
                note_dict = {
                    'id': note_id,
                    'time': format_time_compact(created),
                    'summary': summary or simple_summary(content, 150),
                }
                if pinned:
                    note_dict['pinned'] = True
                if owner:
                    note_dict['owner'] = owner
                if verbose and pagerank and pagerank > 0.01:
                    note_dict['rank'] = round(pagerank, 3)
                formatted_notes.append(note_dict)
            return {"notes": formatted_notes}
        
    except Exception as e:
        logging.error(f"Error in read: {e}", exc_info=True)
        return {"error": f"Read failed: {str(e)}"}

def get_status(verbose: bool = False, **kwargs) -> Dict:
    """Get current state"""
    try:
        with get_db_conn() as conn:
            notes = conn.execute('SELECT COUNT(*) FROM notes WHERE type IS NULL').fetchone()[0]
            pinned = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = TRUE AND type IS NULL').fetchone()[0]
            owned = conn.execute('SELECT COUNT(*) FROM notes WHERE owner IS NOT NULL AND type IS NULL').fetchone()[0]
            unclaimed = conn.execute('SELECT COUNT(*) FROM notes WHERE owner IS NULL AND type IS NULL').fetchone()[0]
            
            recent = conn.execute('SELECT created FROM notes WHERE type IS NULL ORDER BY created DESC LIMIT 1').fetchone()
            last_activity = format_time_compact(recent[0]) if recent else "never"
            
            if verbose:
                edges = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
                entities = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
                sessions = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
                vault = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
                tags = conn.execute('SELECT COUNT(DISTINCT tag) FROM (SELECT unnest(tags) as tag FROM notes WHERE tags IS NOT NULL)').fetchone()[0]
                vector_count = collection.count() if collection else 0
                evolutions = conn.execute("SELECT COUNT(*) FROM notes WHERE type = 'evolution'").fetchone()[0]
                
                if OUTPUT_FORMAT == 'pipe':
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
                    return {"status": '|'.join(parts)}
                else:
                    return {
                        "notes": notes,
                        "pinned": pinned,
                        "owned": owned,
                        "unclaimed": unclaimed,
                        "vectors": vector_count,
                        "edges": edges,
                        "evolutions": evolutions,
                        "last": last_activity,
                        "teambook": CURRENT_TEAMBOOK or "private"
                    }
            else:
                if OUTPUT_FORMAT == 'pipe':
                    status_parts = [
                        f"n:{notes}",
                        f"p:{pinned}",
                        f"owned:{owned}",
                        f"{last_activity}"
                    ]
                    if CURRENT_TEAMBOOK:
                        status_parts.append(f"team:{CURRENT_TEAMBOOK}")
                    return {"status": '|'.join(status_parts)}
                else:
                    return {
                        "notes": notes,
                        "pinned": pinned,
                        "owned": owned,
                        "unclaimed": unclaimed,
                        "last": last_activity,
                        "teambook": CURRENT_TEAMBOOK or "private"
                    }
    
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {"error": f"Status failed: {str(e)}"}

def pin_note(id: Any = None, **kwargs) -> Dict:
    """Pin a note"""
    return _modify_pin_status(kwargs.get('id', id), True)

def unpin_note(id: Any = None, **kwargs) -> Dict:
    """Unpin a note"""
    return _modify_pin_status(kwargs.get('id', id), False)

def _modify_pin_status(id_param: Any, pin: bool) -> Dict:
    """Helper to pin or unpin a note"""
    try:
        note_id = resolve_note_id(id_param)
        if not note_id:
            return {"error": "Invalid note ID"}
        
        with get_db_conn() as conn:
            result = conn.execute(
                'UPDATE notes SET pinned = ? WHERE id = ? RETURNING summary, content',
                [pin, note_id]
            ).fetchone()
            
            if not result:
                return {"error": f"Note {note_id} not found"}
        
        action = 'pin' if pin else 'unpin'
        save_last_operation(action, {'id': note_id})
        
        if pin:
            summ = result[0] or simple_summary(result[1], 100)
            if OUTPUT_FORMAT == 'pipe':
                return {"pinned": f"{note_id}|{summ}"}
            else:
                return {"pinned": note_id, "summary": summ}
        else:
            return {"unpinned": note_id}
    
    except Exception as e:
        logging.error(f"Error in pin/unpin: {e}")
        action = 'pin' if pin else 'unpin'
        return {"error": f"Failed to {action}: {str(e)}"}

def get_full_note(id: Any = None, verbose: bool = False, **kwargs) -> Dict:
    """Get complete note"""
    try:
        note_id = resolve_note_id(kwargs.get('id', id))
        if not note_id:
            return {"error": "Invalid note ID"}
        
        with get_db_conn() as conn:
            note = conn.execute('SELECT * FROM notes WHERE id = ?', [note_id]).fetchone()
            if not note:
                return {"error": f"Note {note_id} not found"}
            
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
        return result
    
    except Exception as e:
        logging.error(f"Error in get_full_note: {e}", exc_info=True)
        return {"error": f"Failed to retrieve: {str(e)}"}

# ============= VAULT FUNCTIONS =============

def vault_store(key: str = None, value: str = None, **kwargs) -> Dict:
    """Store encrypted secret"""
    try:
        key = str(kwargs.get('key', key) or '').strip()
        value = str(kwargs.get('value', value) or '').strip()
        if not key or not value:
            return {"error": "Key and value required"}
        
        # Ensure vault_manager is initialized
        if not teambook_storage_mcp.vault_manager:
            init_vault_manager()
        
        encrypted = teambook_storage_mcp.vault_manager.encrypt(value)
        now = datetime.now()
        
        with get_db_conn() as conn:
            conn.execute('''
                INSERT INTO vault (key, encrypted_value, created, updated, author)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    encrypted_value = EXCLUDED.encrypted_value,
                    updated = EXCLUDED.updated
            ''', [key, encrypted, now, now, CURRENT_AI_ID])
        
        log_operation_to_db('vault_store')
        return {"stored": key}
    
    except Exception as e:
        logging.error(f"Error in vault_store: {e}")
        return {"error": f"Storage failed: {str(e)}"}

def vault_retrieve(key: str = None, **kwargs) -> Dict:
    """Retrieve decrypted secret"""
    try:
        key = str(kwargs.get('key', key) or '').strip()
        if not key:
            return {"error": "Key required"}
        
        # Ensure vault_manager is initialized
        if not teambook_storage_mcp.vault_manager:
            init_vault_manager()
        
        with get_db_conn() as conn:
            result = conn.execute(
                'SELECT encrypted_value FROM vault WHERE key = ?',
                [key]
            ).fetchone()
        
        if not result:
            return {"error": f"Key '{key}' not found"}
        
        decrypted = teambook_storage_mcp.vault_manager.decrypt(result[0])
        log_operation_to_db('vault_retrieve')
        return {"key": key, "value": decrypted}
    
    except Exception as e:
        logging.error(f"Error in vault_retrieve: {e}")
        return {"error": f"Retrieval failed: {str(e)}"}

def vault_list(**kwargs) -> Dict:
    """List vault keys"""
    try:
        with get_db_conn() as conn:
            items = conn.execute(
                'SELECT key, updated FROM vault ORDER BY updated DESC'
            ).fetchall()
        
        if not items:
            return {"msg": "Vault empty"}
        
        if OUTPUT_FORMAT == 'pipe':
            keys = []
            for key, updated in items:
                keys.append(f"{key}|{format_time_compact(updated)}")
            return {"vault_keys": keys}
        else:
            keys = [
                {'key': key, 'updated': format_time_compact(updated)}
                for key, updated in items
            ]
            return {"vault_keys": keys}
    
    except Exception as e:
        logging.error(f"Error in vault_list: {e}")
        return {"error": f"List failed: {str(e)}"}

# ============= ALIASES FOR COMPATIBILITY =============

def remember(**kwargs) -> Dict:
    """Save a note (Notebook compatibility)"""
    return write(**kwargs)

def recall(**kwargs) -> Dict:
    """Search notes (Notebook compatibility)"""
    return read(**kwargs)

def get(**kwargs) -> Dict:
    """Get full note (alias)"""
    return get_full_note(**kwargs)

def pin(**kwargs) -> Dict:
    """Pin note (alias)"""
    return pin_note(**kwargs)

def unpin(**kwargs) -> Dict:
    """Unpin note (alias)"""
    return unpin_note(**kwargs)

# ============= BATCH OPERATIONS =============

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
    """Execute multiple operations efficiently"""
    try:
        from teambook_shared_mcp import BATCH_MAX
        
        operations = kwargs.get('operations', operations or [])
        if not operations:
            return {"error": "No operations"}
        if len(operations) > BATCH_MAX:
            return {"error": f"Max {BATCH_MAX} operations"}
        
        # Map all operations to functions
        op_map = {
            'write': write, 'read': read,
            'remember': remember, 'recall': recall,
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
            'attempts': attempts, 'combine': combine
        }
        
        results = []
        for op in operations:
            op_type = op.get('type')
            if op_type in op_map:
                results.append(op_map[op_type](**op.get('args', {})))
            else:
                results.append({"error": f"Unknown op: {op_type}"})
        
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
            
            return {"batch_results": batch_lines, "count": len(results)}
        else:
            return {"batch_results": results, "count": len(results)}
        
    except Exception as e:
        logging.error(f"Error in batch: {e}")
        return {"error": f"Batch failed: {str(e)}"}
