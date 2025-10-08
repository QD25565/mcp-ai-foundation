#!/usr/bin/env python3
"""
NOTEBOOK MCP v1.0.0 - MAIN APPLICATION
=======================================
Core API functions and MCP protocol handler for the Notebook MCP tool.
Orchestrates storage and utilities to provide notebook functionality.

v1.0.0 - First Public Release:
- Refactored from single file to three-file structure
- Fixed pinned_only bug in recall function
- Added directory tracking integration
- Added vacuum maintenance function for AIs to self-maintain and defrag their DuckDBs
=======================================
"""

import json
import sys
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

# Fix import path for src/ structure
sys.path.insert(0, str(Path(__file__).parent))

# Import shared utilities and storage
from notebook_shared import *
# Import notebook_storage as module to preserve global state
import notebook_storage
from notebook_storage import (
    _get_db_conn, _ensure_embeddings_loaded, _init_embedding_model,
    _init_vector_db, vault_manager, _calculate_pagerank_if_needed,
    _create_all_edges, _detect_or_create_session, _log_operation,
    _log_directory_access, _vacuum_database
)

def remember(content: str = None, summary: str = None, tags: List[str] = None,
             linked_items: List[str] = None, **kwargs) -> Dict:
    """Save a note with DuckDB and optional directory tracking"""
    try:
        start = datetime.now()

        # Security: Validate length BEFORE converting to string to prevent memory exhaustion
        content_input = kwargs.get('content', content or '')
        if isinstance(content_input, str) and len(content_input) > MAX_CONTENT_LENGTH * 2:
            return {"error": f"Content too large (max {MAX_CONTENT_LENGTH} characters)"}

        content = str(content_input).strip()
        if not content:
            content = f"Checkpoint {datetime.now().strftime('%H:%M')}"

        # Security: Limit regex search to prevent catastrophic backtracking DoS
        REGEX_SEARCH_LIMIT = 50000
        search_content = content[:REGEX_SEARCH_LIMIT]

        # Check for directory references and track them
        # Cross-platform: Match absolute paths (Windows: C:\path, Unix: /path)
        dir_pattern = r'(?:[A-Za-z]:\\|/)[^<>:"|?*\n]+'
        directories = re.findall(dir_pattern, search_content)
        for dir_path in directories:
            if Path(dir_path).exists() and Path(dir_path).is_dir():
                track_directory(dir_path)
        
        truncated = False
        orig_len = len(content)
        if orig_len > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
            truncated = True
        
        summary = _clean_text(summary)[:MAX_SUMMARY_LENGTH] if summary else _simple_summary(content)
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
        
        with _get_db_conn() as conn:
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM notes").fetchone()[0]
            note_id = max_id + 1

            # Compress content and summary for storage optimization (Phase 3)
            stored_content = content
            stored_summary = summary
            try:
                from notebook_storage import compress_content, COMPRESSION_AVAILABLE
                if COMPRESSION_AVAILABLE:
                    stored_content = compress_content(content)
                    stored_summary = compress_content(summary) if summary else summary
            except (ImportError, Exception):
                pass  # Use uncompressed if compression not available

            conn.execute('''
                INSERT INTO notes (
                    id, content, summary, tags, pinned, author,
                    created, session_id, linked_items, pagerank, has_vector
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                note_id, stored_content, stored_summary, tags, False, CURRENT_AI_ID,
                datetime.now(), None,
                json.dumps(linked_items) if linked_items else None,
                0.0, bool(notebook_storage.encoder and notebook_storage.collection)
            ])
            
            session_id = _detect_or_create_session(note_id, datetime.now(), conn)
            if session_id:
                conn.execute('UPDATE notes SET session_id = ? WHERE id = ?', [session_id, note_id])
            
            _create_all_edges(note_id, content, session_id, conn)
            
            global PAGERANK_DIRTY
            PAGERANK_DIRTY = True
        
        # Log directory access if any directories were tracked (outside DB context)
        for dir_path in directories[:3]:  # Log up to 3 directories
            if Path(dir_path).exists() and Path(dir_path).is_dir():
                try:
                    _log_directory_access(dir_path, note_id, 'remember')
                except Exception as e:
                    logging.debug(f"Could not log directory access: {e}")
        
        # Add to vector store (lazy-load if needed)
        if _ensure_embeddings_loaded() and notebook_storage.encoder is not None and notebook_storage.collection is not None:
            try:
                embedding = notebook_storage.encoder.encode(content[:1000], convert_to_numpy=True)
                notebook_storage.collection.add(
                    embeddings=[embedding.tolist()],
                    documents=[content],
                    metadatas={
                        "created": datetime.now().isoformat(),
                        "summary": summary,
                        "tags": json.dumps(tags)
                    },
                    ids=[str(note_id)]
                )
                # Update has_vector flag after successful vector creation
                with _get_db_conn() as conn:
                    conn.execute('UPDATE notes SET has_vector = TRUE WHERE id = ?', [note_id])
            except Exception as e:
                # Vector storage is optional - semantic search will still work without it
                logging.debug(f"Vector storage skipped: {e}")
        
        _save_last_operation('remember', {'id': note_id, 'summary': summary})
        _log_operation('remember', int((datetime.now() - start).total_seconds() * 1000))

        if OUTPUT_FORMAT == 'pipe':
            result_str = f"{note_id}|{_format_time_compact(datetime.now())}|{summary}"
            if truncated:
                result_str += f"|T{orig_len}"
            return {"saved": result_str}
        else:
            result_dict = {"id": note_id, "time": _format_time_compact(datetime.now()), "summary": summary}
            if truncated:
                result_dict["truncated"] = orig_len
            return result_dict
    
    except Exception as e:
        logging.error(f"Error in remember: {e}", exc_info=True)
        return {"error": f"Failed to save: {str(e)}"}

def recall(query: str = None, tag: str = None, when: str = None,
           pinned_only: bool = False, show_all: bool = False,
           limit: int = 50, mode: str = "hybrid", verbose: bool = False, **kwargs) -> Dict:
    """Search notes - always with rich summaries, all pinned shown (with bug fix)"""
    try:
        start_time = datetime.now()
        
        if isinstance(limit, str):
            try:
                limit = int(limit)
            except:
                limit = 50
        
        if not any([show_all, query, tag, when, pinned_only]):
            limit = DEFAULT_RECENT
        
        with _get_db_conn() as conn:
            _calculate_pagerank_if_needed(conn)
            
            conditions = []
            params = []
            
            if pinned_only:
                conditions.append("pinned = TRUE")
            
            if when:
                time_start, time_end = _parse_time_query(when)
                if time_start and time_end:
                    conditions.append("created BETWEEN ? AND ?")
                    params.extend([time_start, time_end])
            
            if tag:
                tag_clean = str(tag).lower().strip()
                conditions.append("list_contains(tags, ?)")
                params.append(tag_clean)
            
            notes = []
            
            # First, always get ALL pinned notes (unless specifically filtering)
            if not pinned_only and not query and not tag and not when:
                pinned_notes = conn.execute('''
                    SELECT id, content, summary, tags, pinned, author, created, pagerank
                    FROM notes WHERE pinned = TRUE
                    ORDER BY created DESC
                ''').fetchall()
            else:
                pinned_notes = []
            
            if query:
                # Semantic search (lazy-load embeddings on first use)
                semantic_ids = []
                if mode in ["semantic", "hybrid"] and _ensure_embeddings_loaded():
                    try:
                        query_embedding = notebook_storage.encoder.encode(str(query).strip(), convert_to_numpy=True)
                        results = notebook_storage.collection.query(
                            query_embeddings=[query_embedding.tolist()],
                            n_results=min(limit, 100)
                        )
                        if results['ids'] and results['ids'][0]:
                            semantic_ids = [int(id_str) for id_str in results['ids'][0]]
                    except Exception as e:
                        logging.debug(f"Semantic search failed: {e}")
                
                # Keyword search
                keyword_ids = []
                if mode in ["keyword", "hybrid"]:
                    if notebook_storage.FTS_ENABLED:
                        try:
                            fts_results = conn.execute('''
                                SELECT fts_main_notes.id 
                                FROM fts_main_notes 
                                WHERE fts_main_notes MATCH ?
                                LIMIT ?
                            ''', [str(query).strip(), limit]).fetchall()
                            keyword_ids = [row[0] for row in fts_results]
                        except:
                            notebook_storage.FTS_ENABLED = False

                    if not notebook_storage.FTS_ENABLED:
                        like_query = f"%{str(query).strip()}%"
                        like_results = conn.execute('''
                            SELECT id FROM notes 
                            WHERE content ILIKE ? OR summary ILIKE ?
                            ORDER BY pagerank DESC, created DESC
                            LIMIT ?
                        ''', [like_query, like_query, limit]).fetchall()
                        keyword_ids = [row[0] for row in like_results]
                
                # Combine results
                all_ids, seen = [], set()
                for i in range(max(len(semantic_ids), len(keyword_ids))):
                    if i < len(semantic_ids) and semantic_ids[i] not in seen:
                        all_ids.append(semantic_ids[i]); seen.add(semantic_ids[i])
                    if i < len(keyword_ids) and keyword_ids[i] not in seen:
                        all_ids.append(keyword_ids[i]); seen.add(keyword_ids[i])
                
                if all_ids:
                    note_ids = all_ids[:limit]
                    placeholders = ','.join(['?'] * len(note_ids))
                    
                    where_clause = " AND ".join(conditions) if conditions else "1=1"
                    final_params = note_ids + params + ([note_ids[0]] if note_ids else [])
                    
                    notes = conn.execute(f'''
                        SELECT id, content, summary, tags, pinned, author, created, pagerank
                        FROM notes
                        WHERE id IN ({placeholders}) AND {where_clause}
                        ORDER BY 
                            CASE WHEN id = ? THEN 0 ELSE 1 END,
                            pinned DESC, pagerank DESC, created DESC
                    ''', final_params).fetchall()
                else:
                    notes = []
            else:
                # Regular query without search
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                notes = conn.execute(f'''
                    SELECT id, content, summary, tags, pinned, author, created, pagerank
                    FROM notes {where_clause}
                    ORDER BY pinned DESC, created DESC
                    LIMIT ?
                ''', params + [limit]).fetchall()
        
        # BUG FIX: Combine pinned and regular notes with proper deduplication
        seen_ids = {n[0] for n in pinned_notes}  # n[0] is the note ID
        all_notes = list(pinned_notes) + [n for n in notes if n[0] not in seen_ids]

        # Decompress content and summary if needed (Phase 3)
        try:
            from notebook_storage import decompress_content, COMPRESSION_AVAILABLE
            if COMPRESSION_AVAILABLE and all_notes:
                decompressed_notes = []
                for note in all_notes:
                    note_id, content, summary, tags_arr, pinned, author, created, pagerank = note
                    # Decompress content and summary
                    content = decompress_content(content) if content else content
                    summary = decompress_content(summary) if summary else summary
                    decompressed_notes.append((note_id, content, summary, tags_arr, pinned, author, created, pagerank))
                all_notes = decompressed_notes
        except (ImportError, Exception):
            pass  # Data is already uncompressed

        if not all_notes:
            return {"msg": "No notes found"}
        
        if OUTPUT_FORMAT == 'pipe':
            lines = []
            for note in all_notes:
                note_id, content, summary, tags_arr, pinned, author, created, pagerank = note
                # Always preserve full summary - it's the main value
                parts = [
                    str(note_id),
                    _format_time_compact(created),
                    summary or _simple_summary(content, 150)  # Never truncate summaries
                ]
                if pinned:
                    parts.append('📌')
                if verbose and pagerank and pagerank > 0.01:
                    parts.append(f"★{pagerank:.2f}")
                lines.append('|'.join(_pipe_escape(p) for p in parts))
            return {"notes": lines}
        else:
            formatted_notes = []
            for note in all_notes:
                note_id, content, summary, tags_arr, pinned, author, created, pagerank = note
                note_dict = {
                    'id': note_id,
                    'time': _format_time_compact(created),
                    'summary': summary or _simple_summary(content, 150),  # Never truncate
                }
                if pinned:
                    note_dict['pinned'] = True
                if verbose and pagerank and pagerank > 0.01:
                    note_dict['rank'] = round(pagerank, 3)
                formatted_notes.append(note_dict)
            return {"notes": formatted_notes}

        _save_last_operation('recall', {"notes": all_notes})
        _log_operation('recall', int((datetime.now() - start_time).total_seconds() * 1000))
        
    except Exception as e:
        logging.error(f"Error in recall: {e}", exc_info=True)
        return {"error": f"Recall failed: {str(e)}"}

def notebook_state(verbose: bool = False, **kwargs) -> Dict:
    """Get notebook state - ultra-minimal by default
    
    Shows note counts, pinned notes, last activity, and optionally detailed backend metrics.
    Alias: status(), get_status() (deprecated)
    
    Args:
        verbose: Show detailed stats including edges, entities, sessions (default: False)
    
    Returns:
        Pipe-separated state info: n:42|p:5|2h ago
    """
    try:
        with _get_db_conn() as conn:
            # Always get these essentials
            notes = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            pinned = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = TRUE').fetchone()[0]
            
            recent = conn.execute('SELECT created FROM notes ORDER BY created DESC LIMIT 1').fetchone()
            last_activity = _format_time_compact(recent[0]) if recent else "never"
            
            if verbose:
                # Backend metrics only when explicitly requested
                edges = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
                entities = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
                sessions = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
                vault = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
                tags = conn.execute('SELECT COUNT(DISTINCT tag) FROM (SELECT unnest(tags) as tag FROM notes WHERE tags IS NOT NULL)').fetchone()[0]
                vector_count = notebook_storage.collection.count() if notebook_storage.collection else 0
                
                # Add recent directories
                recent_dirs = get_recent_directories(5)
                
                if OUTPUT_FORMAT == 'pipe':
                    parts = [
                        f"n:{notes}",
                        f"p:{pinned}",
                        f"v:{vector_count}",
                        f"e:{edges}",
                        f"ent:{entities}",
                        f"s:{sessions}",
                        f"t:{tags}",
                        f"last:{last_activity}",
                        f"db:duck",
                        f"emb:{notebook_storage.EMBEDDING_MODEL or 'none'}"
                    ]
                    if recent_dirs:
                        parts.append(f"dirs:{len(recent_dirs)}")
                    return {"status": '|'.join(parts)}
                else:
                    result = {
                        "notes": notes,
                        "pinned": pinned,
                        "vectors": vector_count,
                        "edges": edges,
                        "entities": entities,
                        "sessions": sessions,
                        "tags": tags,
                        "last": last_activity,
                        "db": "duckdb",
                        "embedding": notebook_storage.EMBEDDING_MODEL or "none"
                    }
                    if recent_dirs:
                        result["recent_dirs"] = [Path(d).name for d in recent_dirs]
                    return result
            else:
                # Default minimal output - just what matters
                if OUTPUT_FORMAT == 'pipe':
                    return {"status": f"n:{notes}|p:{pinned}|{last_activity}"}
                else:
                    return {
                        "notes": notes,
                        "pinned": pinned,
                        "last": last_activity
                    }
    
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {"error": f"Status failed: {str(e)}"}

def _modify_pin_status(id_param: Any, pin: bool) -> Dict:
    """Helper to pin or unpin a note"""
    try:
        note_id = _get_note_id(id_param)
        if not note_id:
            # Check database for "last" if needed
            if id_param == "last":
                with _get_db_conn() as conn:
                    recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
                    note_id = recent[0] if recent else None
        
        if not note_id:
            return {"error": "Invalid note ID"}
        
        with _get_db_conn() as conn:
            result = conn.execute(
                'UPDATE notes SET pinned = ? WHERE id = ? RETURNING summary, content',
                [pin, note_id]
            ).fetchone()
            
            if not result:
                return {"error": f"Note {note_id} not found"}
        
        action = 'pin' if pin else 'unpin'
        _save_last_operation(action, {'id': note_id})

        if pin:
            summ = result[0] or _simple_summary(result[1], 100)
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

def pin_note(id: Any = None, **kwargs) -> Dict:
    """Pin a note"""
    return _modify_pin_status(kwargs.get('id', id), True)

def unpin_note(id: Any = None, **kwargs) -> Dict:
    """Unpin a note"""
    return _modify_pin_status(kwargs.get('id', id), False)

def get_full_note(id: Any = None, verbose: bool = False, **kwargs) -> Dict:
    """Get complete note - NO edges ever shown (with result caching for AI speed)"""
    try:
        note_id = _get_note_id(kwargs.get('id', id))
        if not note_id:
            # Check database for "last" if needed
            if kwargs.get('id', id) == "last":
                with _get_db_conn() as conn:
                    recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
                    note_id = recent[0] if recent else None

        if not note_id:
            return {"error": "Invalid note ID"}

        # Try cache first (5 minute TTL for AI responsiveness)
        try:
            from performance_utils import note_cache
            cached = note_cache.get(f"note_{note_id}")
            if cached and not verbose:  # Use cache only for non-verbose requests
                return cached
        except ImportError:
            pass  # Cache not available, continue without it
        
        with _get_db_conn() as conn:
            note = conn.execute('SELECT * FROM notes WHERE id = ?', [note_id]).fetchone()
            if not note:
                return {"error": f"Note {note_id} not found"}

            cols = [desc[0] for desc in conn.description]
            result = dict(zip(cols, note))

            # Decompress content and summary if needed (Phase 3)
            try:
                from notebook_storage import decompress_content, COMPRESSION_AVAILABLE
                if COMPRESSION_AVAILABLE:
                    if 'content' in result and result['content']:
                        result['content'] = decompress_content(result['content'])
                    if 'summary' in result and result['summary']:
                        result['summary'] = decompress_content(result['summary'])
            except (ImportError, Exception):
                pass  # Data is already uncompressed

            # Clean up datetime
            if 'created' in result and result['created']:
                result['created'] = _format_time_compact(result['created'])
            
            # Get entities (actually useful for pattern matching)
            entities = conn.execute('''
                SELECT e.name FROM entities e
                JOIN entity_notes en ON e.id = en.entity_id
                WHERE en.note_id = ?
            ''', [note_id]).fetchall()
            if entities:
                result['entities'] = [e[0] for e in entities]
            
            # Remove any edge data from result
            result.pop('session_id', None)
            result.pop('linked_items', None)
            result.pop('pagerank', None)
            result.pop('has_vector', None)
            
            # NEVER include edges - they're backend noise

        # Cache result for AI speed (5 minute TTL)
        try:
            from performance_utils import note_cache
            note_cache.set(f"note_{note_id}", result)
        except ImportError:
            pass

        _save_last_operation('get_full_note', {'id': note_id})
        return result
    
    except Exception as e:
        logging.error(f"Error in get_full_note: {e}", exc_info=True)
        return {"error": f"Failed to retrieve: {str(e)}"}

def vault_store(key: str = None, value: str = None, **kwargs) -> Dict:
    """Store encrypted secret"""
    try:
        key = str(kwargs.get('key', key) or '').strip()
        value = str(kwargs.get('value', value) or '').strip()
        if not key or not value:
            return {"error": "Key and value required"}
        
        encrypted = vault_manager.encrypt(value)
        now = datetime.now()
        
        with _get_db_conn() as conn:
            conn.execute('''
                INSERT INTO vault (key, encrypted_value, created, updated, author)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    encrypted_value = EXCLUDED.encrypted_value,
                    updated = EXCLUDED.updated
            ''', [key, encrypted, now, now, CURRENT_AI_ID])
        
        _log_operation('vault_store')
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
        
        with _get_db_conn() as conn:
            result = conn.execute(
                'SELECT encrypted_value FROM vault WHERE key = ?',
                [key]
            ).fetchone()
        
        if not result:
            return {"error": f"Key '{key}' not found"}
        
        decrypted = vault_manager.decrypt(result[0])
        _log_operation('vault_retrieve')
        return {"key": key, "value": decrypted}
    
    except Exception as e:
        logging.error(f"Error in vault_retrieve: {e}")
        return {"error": f"Retrieval failed: {str(e)}"}

def vault_list(**kwargs) -> Dict:
    """List vault keys"""
    try:
        with _get_db_conn() as conn:
            items = conn.execute(
                'SELECT key, updated FROM vault ORDER BY updated DESC'
            ).fetchall()
        
        if not items:
            return {"msg": "Vault empty"}
        
        if OUTPUT_FORMAT == 'pipe':
            keys = []
            for key, updated in items:
                keys.append(f"{key}|{_format_time_compact(updated)}")
            return {"vault_keys": keys}
        else:
            keys = [
                {'key': key, 'updated': _format_time_compact(updated)}
                for key, updated in items
            ]
            return {"vault_keys": keys}
    
    except Exception as e:
        logging.error(f"Error in vault_list: {e}")
        return {"error": f"List failed: {str(e)}"}

def recent_dirs(limit: int = 5, **kwargs) -> Dict:
    """Get recent directories accessed"""
    try:
        dirs = get_recent_directories(limit)
        if not dirs:
            return {"msg": "No recent directories"}
        
        if OUTPUT_FORMAT == 'pipe':
            return {"dirs": _format_directory_trail()}
        else:
            return {"recent_directories": dirs}
    
    except Exception as e:
        logging.error(f"Error in recent_dirs: {e}")
        return {"error": f"Failed to get recent directories: {str(e)}"}

def compact(**kwargs) -> Dict:
    """Run VACUUM to optimize and compact the database"""
    try:
        result = _vacuum_database()
        
        if "error" in result:
            return result
        
        if OUTPUT_FORMAT == 'pipe':
            return {"vacuum": f"saved:{result['saved_mb']:.1f}MB|{result['percent_saved']:.1f}%"}
        else:
            return result
    
    except Exception as e:
        logging.error(f"Error in compact: {e}")
        return {"error": f"Compact failed: {str(e)}"}

def reindex_embeddings(limit: int = None, dry_run: bool = False, **kwargs) -> Dict:
    """Backfill embeddings for notes that don't have them (self-healing function)"""
    try:
        start_time = datetime.now()
        limit = kwargs.get('limit', limit)
        dry_run = kwargs.get('dry_run', dry_run)

        # Check if embeddings are available
        if not _ensure_embeddings_loaded():
            return {"error": "Embeddings not available. Install: pip install sentence-transformers chromadb"}

        if notebook_storage.encoder is None or notebook_storage.collection is None:
            return {"error": "Embedding system failed to initialize"}

        with _get_db_conn() as conn:
            # Find notes without embeddings
            query = "SELECT id, content, summary, tags, created FROM notes WHERE has_vector = FALSE ORDER BY id"
            if limit:
                query += f" LIMIT {int(limit)}"

            missing = conn.execute(query).fetchall()

            if not missing:
                return {"reindex": "complete|all_notes_have_embeddings"}

            if dry_run:
                return {
                    "reindex": f"dry_run|found:{len(missing)}|first:{missing[0][0]}|last:{missing[-1][0]}"
                }

            # Backfill embeddings
            success_count = 0
            error_count = 0

            for note_id, content, summary, tags, created in missing:
                try:
                    # Generate embedding
                    text = f"{content or ''} {summary or ''} {tags or ''}".strip()
                    if not text:
                        continue

                    embedding = notebook_storage.encoder.encode(text[:1000], convert_to_numpy=True)

                    # Add to ChromaDB (convert tags list to string)
                    tags_str = tags if isinstance(tags, str) else (', '.join(tags) if tags else '')
                    notebook_storage.collection.add(
                        embeddings=[embedding.tolist()],
                        documents=[content or summary or ''],
                        metadatas=[{
                            "created": str(created) if created else '',
                            "tags": tags_str
                        }],
                        ids=[f"note_{note_id}"]
                    )

                    # Update database flag
                    conn.execute("UPDATE notes SET has_vector = TRUE WHERE id = ?", [note_id])
                    success_count += 1

                except Exception as e:
                    logging.warning(f"Failed to reindex note {note_id}: {e}")
                    error_count += 1

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if OUTPUT_FORMAT == 'pipe':
                return {
                    "reindex": f"complete|indexed:{success_count}|errors:{error_count}|time:{duration_ms}ms"
                }
            else:
                return {
                    "indexed": success_count,
                    "errors": error_count,
                    "duration_ms": duration_ms,
                    "collection_size": notebook_storage.collection.count()
                }

    except Exception as e:
        logging.error(f"Error in reindex_embeddings: {e}")
        return {"error": f"Reindex failed: {str(e)}"}

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
    """Execute multiple operations efficiently"""
    try:
        operations = kwargs.get('operations', operations or [])
        if not operations:
            return {"error": "No operations"}
        if len(operations) > BATCH_MAX:
            return {"error": f"Max {BATCH_MAX} operations"}
        
        op_map = {
            'remember': remember, 'recall': recall,
            'pin_note': pin_note, 'pin': pin_note,
            'unpin_note': unpin_note, 'unpin': unpin_note,
            'vault_store': vault_store, 'vault_retrieve': vault_retrieve,
            'get_full_note': get_full_note, 'get': get_full_note,
            'status': get_status, 'vault_list': vault_list,
            'recent_dirs': recent_dirs, 'compact': compact,
            'reindex_embeddings': reindex_embeddings, 'reindex': reindex_embeddings
        }
        
        results = []
        for op in operations:
            op_type = op.get('type')
            if op_type in op_map:
                results.append(op_map[op_type](**op.get('args', {})))
            else:
                results.append({"error": f"Unknown op: {op_type}"})
        
        return {"batch_results": results, "count": len(results)}
    
    except Exception as e:
        logging.error(f"Error in batch: {e}")
        return {"error": f"Batch failed: {str(e)}"}

def status(verbose: bool = False, **kwargs) -> Dict:
    """Get status - ALIAS for notebook_state()
    
    Primary: notebook_state()
    """
    return notebook_state(verbose=verbose, **kwargs)

def get_status(verbose: bool = False, **kwargs) -> Dict:
    """Get status - Deprecated for notebook_state()
    
    Primary: notebook_state()
    Deprecated: Use notebook_state() or status() instead
    """
    return notebook_state(verbose=verbose, **kwargs)

def standby(timeout: int = 300, **kwargs) -> Dict:
    """
    Enter standby mode - alias for teambook standby_mode

    IMPORTANT: Standby mode makes you available and responsive! Wake on:
    - Direct messages or mentions
    - Help requests
    - Task assignments
    - Any relevant team activity

    Args:
        timeout: Maximum seconds to wait (default: 300, max: 300)

    Returns:
        Event data with wake_reason, or timeout message

    Examples:
        notebook standby
        notebook standby --timeout 180
    """
    try:
        # Import teambook standby_mode
        sys.path.insert(0, str(Path(__file__).parent.parent / 'teambook'))
        from teambook_api import standby_mode

        return standby_mode(timeout=timeout, **kwargs)
    except ImportError as e:
        return {
            "error": "standby requires teambook",
            "message": "Install teambook to use standby mode",
            "details": str(e)
        }
    except Exception as e:
        return {
            "error": "standby_failed",
            "message": str(e)
        }


def standby_mode(timeout: int = 300, **kwargs) -> Dict:
    """Alias for standby() - both work the same"""
    return standby(timeout=timeout, **kwargs)


def start_session(*args, **kwargs) -> Dict:
    """
    Pull context from all available tools for session startup.
    
    IMPORTANT: This function ignores ALL parameters - it always pulls fresh context.
    You can call it with empty args, null, or anything else - it will still work.
    
    Returns comprehensive overview including:
    - Pinned notes (notebook)
    - Recent notes (notebook)  
    - Unread DMs (teambook)
    - Recent broadcasts (teambook)
    - Online instances (teambook)
    - Task queue status (tasks)
    - Current time/location (world)
    """
    # Completely ignore all parameters - always pull fresh context
    # This makes the function bulletproof against weird inputs
    
    try:
        # Import platform-aware sanitization
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from universal_adapter import sanitize_for_platform
        except ImportError:
            # Fallback if universal_adapter not available
            def sanitize_for_platform(text):
                return text
        
        # Try to import other tools (they may not be available)
        try:
            from teambook import teambook_api
            TEAMBOOK_AVAILABLE = True
        except ImportError:
            TEAMBOOK_AVAILABLE = False
        
        try:
            import task_manager
            TASKS_AVAILABLE = True
        except ImportError:
            TASKS_AVAILABLE = False
        
        try:
            import world
            WORLD_AVAILABLE = True
        except ImportError:
            WORLD_AVAILABLE = False
        
        output_lines = []
        
        # Header with world context
        if WORLD_AVAILABLE:
            try:
                world_status = world.world_command()
                # Parse location from world context (format: "HH:MM|City,Country")
                location = "Unknown"
                if isinstance(world_status, dict) and 'context' in world_status:
                    context_parts = world_status['context'].split('|')
                    if len(context_parts) > 1:
                        location = context_parts[1]  # Extract "City,Country"
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                output_lines.append(f"📝 SESSION START - {location} - {timestamp}")
            except Exception as e:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                output_lines.append(f"📝 SESSION START - {timestamp}")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            output_lines.append(f"📝 SESSION START - {timestamp}")
        
        # Add identity
        output_lines.append(f"{CURRENT_AI_ID} @ ai-foundation")
        output_lines.append("─" * 60)
        output_lines.append("")
        
        # NOTEBOOK SECTION
        try:
            # Get pinned notes
            pinned_result = recall(pinned_only=True, limit=10)
            if pinned_result.get('notes'):
                output_lines.append("PINNED NOTES")
                output_lines.append("─" * 40)
                notes = pinned_result['notes']
                if isinstance(notes, list):
                    for note in notes[:5]:  # Show max 5 pinned
                        if isinstance(note, str):
                            output_lines.append(f"  {note}")
                        elif isinstance(note, dict):
                            output_lines.append(f"  {note.get('id')} | {note.get('summary', 'No summary')}")
                output_lines.append("")
            
            # Get recent notes
            recent_result = recall(limit=5)
            if recent_result.get('notes'):
                notes = recent_result['notes']
                if isinstance(notes, list) and len(notes) > 0:
                    # Get total count
                    status = get_status()
                    total = status.get('notes', 0) if isinstance(status, dict) else 0
                    
                    output_lines.append(f"RECENT NOTES (Last 5 of {total} total)")
                    output_lines.append("─" * 40)
                    for note in notes:
                        if isinstance(note, str):
                            output_lines.append(f"  {note}")
                        elif isinstance(note, dict):
                            time_str = note.get('time', '')
                            summary = note.get('summary', 'No summary')
                            output_lines.append(f"  {note.get('id')} | {time_str} | {summary}")
                    output_lines.append("")
        except Exception as e:
            output_lines.append(f"⚠️ Notebook unavailable: {e}")
            output_lines.append("")
        
        # TEAMBOOK SECTION
        if TEAMBOOK_AVAILABLE:
            try:
                # Get unread DMs
                dms_result = teambook_api.read_dms(unread_only=True, limit=10)
                if dms_result and isinstance(dms_result, dict) and not dms_result.get('error'):
                    output_lines.append("UNREAD DMs")
                    output_lines.append("─" * 40)
                    
                    # Parse DMs (format may vary)
                    if isinstance(dms_result, dict):
                        dms = dms_result.get('dms', dms_result.get('messages', []))
                    elif isinstance(dms_result, list):
                        dms = dms_result
                    else:
                        dms = []
                    
                    if dms:
                        for dm in dms[:5]:  # Show max 5 DMs
                            if isinstance(dm, str):
                                output_lines.append(f"  {dm}")
                            elif isinstance(dm, dict):
                                from_ai = dm.get('from', dm.get('from_ai', 'unknown'))
                                content = dm.get('content', dm.get('message', ''))
                                time_str = dm.get('time', dm.get('timestamp', ''))
                                output_lines.append(f"  {time_str} | {from_ai}: \"{content[:50]}{'...' if len(content) > 50 else ''}\"")
                    else:
                        output_lines.append("  No unread messages")
                    output_lines.append("")
                
                # Get recent broadcasts
                broadcasts_result = teambook_api.read_channel(limit=7)
                if broadcasts_result and isinstance(broadcasts_result, dict) and not broadcasts_result.get('error'):
                    output_lines.append("RECENT BROADCASTS")
                    output_lines.append("─" * 40)
                    
                    # Parse broadcasts
                    if isinstance(broadcasts_result, dict):
                        broadcasts = broadcasts_result.get('messages', broadcasts_result.get('broadcasts', []))
                    elif isinstance(broadcasts_result, list):
                        broadcasts = broadcasts_result
                    else:
                        broadcasts = []
                    
                    if broadcasts:
                        for msg in broadcasts[:7]:
                            if isinstance(msg, str):
                                output_lines.append(f"  {msg}")
                            elif isinstance(msg, dict):
                                from_ai = msg.get('from', msg.get('from_ai', 'unknown'))
                                content = msg.get('content', msg.get('message', ''))
                                time_str = msg.get('time', msg.get('timestamp', ''))
                                output_lines.append(f"  {time_str} | {from_ai}: \"{content[:60]}\"")
                    output_lines.append("")
                
                # Get online AIs
                online_result = teambook_api.who_is_here()
                if online_result and isinstance(online_result, dict) and not online_result.get('error'):
                    output_lines.append("ONLINE NOW")
                    output_lines.append("─" * 40)
                    
                    if isinstance(online_result, dict):
                        online = online_result.get('online', online_result.get('active', []))
                    elif isinstance(online_result, list):
                        online = online_result
                    else:
                        online = []
                    
                    if online:
                        online_str = ", ".join(str(ai) for ai in online[:5])
                        output_lines.append(f"  {online_str}")
                    else:
                        output_lines.append("  No other instances online")
                    output_lines.append("")
                    
            except Exception as e:
                output_lines.append(f"⚠️ Teambook unavailable: {e}")
                output_lines.append("")
        
        # TASKS SECTION
        if TASKS_AVAILABLE:
            try:
                stats_result = task_manager.task_stats()
                if stats_result and not stats_result.get('error'):
                    output_lines.append("TASK QUEUE")
                    output_lines.append("─" * 40)
                    
                    if isinstance(stats_result, dict):
                        assigned = stats_result.get('assigned', 0)
                        available = stats_result.get('available', 0)
                        completed = stats_result.get('completed_today', 0)
                        
                        output_lines.append(f"  Assigned to me: {assigned}")
                        output_lines.append(f"  Available: {available}")
                        output_lines.append(f"  Completed today: {completed}")
                    output_lines.append("")
            except Exception as e:
                output_lines.append(f"⚠️ Tasks unavailable: {e}")
                output_lines.append("")
        
        # Footer with tips
        output_lines.append("")
        if TEAMBOOK_AVAILABLE:
            try:
                dms_result = teambook_api.read_dms(unread_only=True, limit=1)
                if dms_result and isinstance(dms_result, dict) and not dms_result.get('error'):
                    dms = dms_result.get('dms', dms_result.get('messages', []))
                    if dms:
                        output_lines.append("💡 TIP: You have unread DMs - use 'teambook_read_dms()' or 'inbox' for full threads")
            except:
                pass

        # SESSION BEST PRACTICES REMINDER
        output_lines.append("")
        output_lines.append("📌 SESSION BEST PRACTICES")
        output_lines.append("─" * 40)
        output_lines.append("1. 📝 Remember important findings in your notebook!")
        output_lines.append("2. 🔔 After asking questions/broadcasting, use teambook_standby_mode()!")
        output_lines.append("   - Default 3min timeout (API limit)")
        output_lines.append("   - Wake on DMs, @mentions, help requests, coordination keywords")
        output_lines.append("   - Custom timeout: --timeout 60 (1min) or --timeout 180 (3min max)")
        output_lines.append("3. 🔄 If woken but task not relevant, return to standby!")
        output_lines.append("")

        # Return as formatted string with platform-aware sanitization
        result_text = "\n".join(output_lines)
        result_text = sanitize_for_platform(result_text)

        return {"session": result_text}
    
    except Exception as e:
        # Catastrophic failure - return minimal but valid session info
        logging.error(f"start_session failed: {e}", exc_info=True)
        try:
            from universal_adapter import sanitize_for_platform
        except:
            def sanitize_for_platform(text):
                return text
        
        fallback_text = sanitize_for_platform(
            f"📝 SESSION START - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{CURRENT_AI_ID} @ ai-foundation\n"
            f"\n"
            f"⚠️ Error loading session context: {str(e)}\n"
        )
        return {"session": fallback_text, "error": str(e)}

def _handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with clean formatting"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})
    
    tools = {
        "notebook_state": notebook_state, "status": notebook_state, "get_status": notebook_state,
        "remember": remember, "recall": recall,
        "get_full_note": get_full_note, "get": get_full_note,
        "pin_note": pin_note, "pin": pin_note,
        "unpin_note": unpin_note, "unpin": unpin_note,
        "vault_store": vault_store, "vault_retrieve": vault_retrieve,
        "vault_list": vault_list, "batch": batch,
        "recent_dirs": recent_dirs, "compact": compact,
        "reindex_embeddings": reindex_embeddings, "reindex": reindex_embeddings,
        "start_session": start_session
    }
    
    if tool_name not in tools:
        # Helpful error for common confusion
        if tool_name in ["standby", "standby_mode"]:
            return {"content": [{"type": "text", "text": "Error: 'standby' is a Teambook function, not Notebook.\nUse: python -m tools.teambook standby\nOr: TEAMBOOK_NAME=town-hall-YourComputerName python -m tools.teambook standby"}]}
        return {"content": [{"type": "text", "text": f"Error: Unknown tool: {tool_name}"}]}
    
    result = tools[tool_name](**tool_args)
    text_parts = []
    
    # Format response based on tool and result
    if tool_name in ["get_full_note", "get"] and "content" in result and "id" in result:
        text_parts.append(f"=== NOTE {result['id']} ===")
        if result.get('pinned'):
            text_parts.append("📌 PINNED")
        text_parts.append(f"\n{result['content']}\n")
        if result.get('summary'):
            text_parts.append(f"Summary: {result['summary']}")
        if result.get('entities'):
            text_parts.append(f"Entities: {', '.join(result['entities'])}")
        # NO edge data ever shown
    elif tool_name == "vault_retrieve" and "value" in result:
        text_parts.append(f"🔐 {result['key']}: {result['value']}")
    elif tool_name == "recent_dirs" and "dirs" in result:
        text_parts.append(f"Recent directories: {result['dirs']}")
    elif tool_name == "recent_dirs" and "recent_directories" in result:
        text_parts.append("Recent directories:")
        for d in result["recent_directories"]:
            text_parts.append(f"  - {d}")
    elif tool_name == "compact" and "vacuum" in result:
        text_parts.append(f"Database compacted: {result['vacuum']}")
    elif "error" in result:
        text_parts.append(f"Error: {result['error']}")
    elif OUTPUT_FORMAT == 'pipe' and "notes" in result and isinstance(result["notes"], list):
        text_parts.extend(result["notes"])
    elif "saved" in result:
        text_parts.append(result["saved"])
    elif "pinned" in result:
        text_parts.append(str(result["pinned"]))
    elif "unpinned" in result:
        text_parts.append(f"Unpinned {result['unpinned']}")
    elif "stored" in result:
        text_parts.append(f"Stored {result['stored']}")
    elif "status" in result:
        text_parts.append(result["status"])
    elif "vault_keys" in result:
        if OUTPUT_FORMAT == 'pipe':
            text_parts.extend(result["vault_keys"])
        else:
            text_parts.append(json.dumps(result["vault_keys"]))
    elif "msg" in result:
        text_parts.append(result["msg"])
    elif "session" in result:
        text_parts.append(result["session"])
    elif "batch_results" in result:
        text_parts.append(f"Batch: {result.get('count', 0)}")
        for r in result["batch_results"]:
            if isinstance(r, dict):
                if "error" in r:
                    text_parts.append(f"Error: {r['error']}")
                elif "saved" in r:
                    text_parts.append(r["saved"])
                elif "pinned" in r:
                    text_parts.append(str(r["pinned"]))
                else:
                    text_parts.append(json.dumps(r))
            else:
                text_parts.append(str(r))
    else:
        text_parts.append(json.dumps(result))
    
    return {"content": [{"type": "text", "text": "\n".join(text_parts) if text_parts else "Done"}]}

def main():
    """MCP server main loop"""
    logging.info(f"Notebook MCP v{VERSION} - Refactored Edition")
    logging.info(f"Identity: {CURRENT_AI_ID} | DB: {DB_FILE}")
    logging.info(f"Features: Three-file structure, pinned_only fixed, directory tracking")
    logging.info(f"Embedding: {notebook_storage.EMBEDDING_MODEL or 'None'}")
    logging.info(f"FTS: {'Yes' if notebook_storage.FTS_ENABLED else 'No'}")
    logging.info("✓ Refactored into three files")
    logging.info("✓ Fixed pinned_only bug")
    logging.info("✓ Added directory tracking")
    logging.info("✓ Added vacuum maintenance")
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            
            request = json.loads(line)
            request_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})
            
            response = {"jsonrpc": "2.0", "id": request_id}
            
            if method == "initialize":
                response["result"] = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "notebook",
                        "version": VERSION,
                        "description": f"AI memory v{VERSION}: Refactored, fixed, enhanced"
                    }
                }
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                tool_schemas = {
                    "notebook_state": {
                        "desc": "Notebook state (n:X|p:Y|last) - PRIMARY",
                        "props": {"verbose": {"type": "boolean", "description": "Include backend metrics"}}
                    },
                    "status": {
                        "desc": "Alias for notebook_state",
                        "props": {"verbose": {"type": "boolean"}}
                    },
                    "get_status": {
                        "desc": "DEPRECATED: Use notebook_state or status instead",
                        "props": {"verbose": {"type": "boolean"}}
                    },
                    "remember": {
                        "desc": "Save a note (auto-tracks directories)",
                        "props": {
                            "content": {"type": "string"},
                            "summary": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "recall": {
                        "desc": "Search notes (shows ALL pinned + results)",
                        "props": {
                            "query": {"type": "string"},
                            "tag": {"type": "string"},
                            "when": {"type": "string"},
                            "pinned_only": {"type": "boolean"},
                            "verbose": {"type": "boolean", "description": "Include PageRank scores"}
                        }
                    },
                    "get_full_note": {
                        "desc": "Get note content",
                        "props": {
                            "id": {"type": "string"},
                            "verbose": {"type": "boolean", "description": "No effect - edges never shown"}
                        },
                        "req": ["id"]
                    },
                    "get": {
                        "desc": "Alias for get_full_note",
                        "props": {
                            "id": {"type": "string"},
                            "verbose": {"type": "boolean", "description": "No effect - edges never shown"}
                        },
                        "req": ["id"]
                    },
                    "pin_note": {
                        "desc": "Pin a note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "pin": {
                        "desc": "Alias for pin_note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "unpin_note": {
                        "desc": "Unpin a note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "unpin": {
                        "desc": "Alias for unpin_note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "vault_store": {
                        "desc": "Store encrypted secret",
                        "props": {"key": {"type": "string"}, "value": {"type": "string"}},
                        "req": ["key", "value"]
                    },
                    "vault_retrieve": {
                        "desc": "Retrieve decrypted secret",
                        "props": {"key": {"type": "string"}},
                        "req": ["key"]
                    },
                    "vault_list": {
                        "desc": "List vault keys",
                        "props": {}
                    },
                    "recent_dirs": {
                        "desc": "Get recently accessed directories",
                        "props": {"limit": {"type": "number", "default": 5}}
                    },
                    "compact": {
                        "desc": "VACUUM database to reclaim space",
                        "props": {}
                    },
                    "batch": {
                        "desc": "Execute multiple operations",
                        "props": {"operations": {"type": "array"}},
                        "req": ["operations"]
                    },
                    "start_session": {
                        "desc": "Pull context from all available tools for session startup (ignores all parameters)",
                        "props": {}
                    },
                }
                
                response["result"] = {
                    "tools": [{
                        "name": name,
                        "description": schema["desc"],
                        "inputSchema": {
                            "type": "object",
                            "properties": schema["props"],
                            "required": schema.get("req", []),
                            "additionalProperties": True
                        }
                    } for name, schema in tool_schemas.items()]
                }
            elif method == "tools/call":
                response["result"] = _handle_tools_call(params)
            else:
                response["result"] = {"status": "ready"}
            
            if "result" in response or "error" in response:
                print(json.dumps(response), flush=True)
        
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logging.error(f"Server loop error: {e}", exc_info=True)
            continue
    
    logging.info("Notebook MCP shutting down")

if __name__ == "__main__":
    main()
