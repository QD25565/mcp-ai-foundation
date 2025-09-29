#!/usr/bin/env python3
"""
NOTEBOOK MCP v6.2.0 - MAIN APPLICATION
=======================================
Core API functions and MCP protocol handler for the Notebook MCP tool.
Orchestrates storage and utilities to provide notebook functionality.

v6.2.0 Changes:
- Refactored from single file to three-file structure
- Fixed pinned_only bug in recall function
- Added directory tracking integration
- Added vacuum maintenance function for AIs to self-maintain and defrag their DuckDBs
=======================================
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Import shared utilities and storage
from notebook_shared import *
from notebook_storage import *

def remember(content: str = None, summary: str = None, tags: List[str] = None, 
             linked_items: List[str] = None, **kwargs) -> Dict:
    """Save a note with DuckDB and optional directory tracking"""
    try:
        start = datetime.now()
        content = str(kwargs.get('content', content or '')).strip()
        if not content:
            content = f"Checkpoint {datetime.now().strftime('%H:%M')}"
        
        # Check for directory references and track them
        dir_pattern = r'[A-Za-z]:\\[^<>:"|?*\n]+'
        directories = re.findall(dir_pattern, content)
        for dir_path in directories:
            if Path(dir_path).exists() and Path(dir_path).is_dir():
                track_directory(dir_path)
        
        truncated = False
        orig_len = len(content)
        if orig_len > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
            truncated = True
        
        summary = clean_text(summary)[:MAX_SUMMARY_LENGTH] if summary else simple_summary(content)
        # Normalize tags parameter - convert string 'null' to None for forgiving tool calls
        tags = normalize_param(tags)
        linked_items = normalize_param(linked_items)
        tags = [str(t).lower().strip() for t in tags if t] if tags else []
        
        with get_db_conn() as conn:
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM notes").fetchone()[0]
            note_id = max_id + 1
            
            conn.execute('''
                INSERT INTO notes (
                    id, content, summary, tags, pinned, author,
                    created, session_id, linked_items, pagerank, has_vector
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                note_id, content, summary, tags, False, CURRENT_AI_ID,
                datetime.now(), None,
                json.dumps(linked_items) if linked_items else None,
                0.0, bool(encoder and collection)
            ])
            
            session_id = detect_or_create_session(note_id, datetime.now(), conn)
            if session_id:
                conn.execute('UPDATE notes SET session_id = ? WHERE id = ?', [session_id, note_id])
            
            create_all_edges(note_id, content, session_id, conn)
            
            global PAGERANK_DIRTY
            PAGERANK_DIRTY = True
            
            # Log directory access if any directories were tracked
            for dir_path in directories[:3]:  # Log up to 3 directories
                if Path(dir_path).exists() and Path(dir_path).is_dir():
                    log_directory_access(dir_path, note_id, 'remember')
        
        # Add to vector store
        if encoder and collection:
            try:
                embedding = encoder.encode(content[:1000], convert_to_numpy=True)
                collection.add(
                    embeddings=[embedding.tolist()],
                    documents=[content],
                    metadatas={
                        "created": datetime.now().isoformat(),
                        "summary": summary,
                        "tags": json.dumps(tags)
                    },
                    ids=[str(note_id)]
                )
            except Exception as e:
                logging.warning(f"Vector storage failed: {e}")
        
        save_last_operation('remember', {'id': note_id, 'summary': summary})
        log_operation('remember', int((datetime.now() - start).total_seconds() * 1000))
        
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
        
        with get_db_conn() as conn:
            calculate_pagerank_if_needed(conn)
            
            conditions = []
            params = []
            
            if pinned_only:
                conditions.append("pinned = TRUE")
            
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
                # Semantic search
                semantic_ids = []
                if encoder and collection and mode in ["semantic", "hybrid"]:
                    try:
                        query_embedding = encoder.encode(str(query).strip(), convert_to_numpy=True)
                        results = collection.query(
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
                    global FTS_ENABLED
                    if FTS_ENABLED:
                        try:
                            fts_results = conn.execute('''
                                SELECT fts_main_notes.id 
                                FROM fts_main_notes 
                                WHERE fts_main_notes MATCH ?
                                LIMIT ?
                            ''', [str(query).strip(), limit]).fetchall()
                            keyword_ids = [row[0] for row in fts_results]
                        except:
                            FTS_ENABLED = False
                    
                    if not FTS_ENABLED:
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
        
        if not all_notes:
            return {"msg": "No notes found"}
        
        if OUTPUT_FORMAT == 'pipe':
            lines = []
            for note in all_notes:
                note_id, content, summary, tags_arr, pinned, author, created, pagerank = note
                # Always preserve full summary - it's the main value
                parts = [
                    str(note_id),
                    format_time_compact(created),
                    summary or simple_summary(content, 150)  # Never truncate summaries
                ]
                if pinned:
                    parts.append('📌')
                if verbose and pagerank and pagerank > 0.01:
                    parts.append(f"★{pagerank:.2f}")
                lines.append('|'.join(pipe_escape(p) for p in parts))
            return {"notes": lines}
        else:
            formatted_notes = []
            for note in all_notes:
                note_id, content, summary, tags_arr, pinned, author, created, pagerank = note
                note_dict = {
                    'id': note_id,
                    'time': format_time_compact(created),
                    'summary': summary or simple_summary(content, 150),  # Never truncate
                }
                if pinned:
                    note_dict['pinned'] = True
                if verbose and pagerank and pagerank > 0.01:
                    note_dict['rank'] = round(pagerank, 3)
                formatted_notes.append(note_dict)
            return {"notes": formatted_notes}
        
        save_last_operation('recall', {"notes": all_notes})
        log_operation('recall', int((datetime.now() - start_time).total_seconds() * 1000))
        
    except Exception as e:
        logging.error(f"Error in recall: {e}", exc_info=True)
        return {"error": f"Recall failed: {str(e)}"}

def get_status(verbose: bool = False, **kwargs) -> Dict:
    """Get current state - ultra-minimal by default, includes recent dirs"""
    try:
        with get_db_conn() as conn:
            # Always get these essentials
            notes = conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
            pinned = conn.execute('SELECT COUNT(*) FROM notes WHERE pinned = TRUE').fetchone()[0]
            
            recent = conn.execute('SELECT created FROM notes ORDER BY created DESC LIMIT 1').fetchone()
            last_activity = format_time_compact(recent[0]) if recent else "never"
            
            if verbose:
                # Backend metrics only when explicitly requested
                edges = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
                entities = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
                sessions = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
                vault = conn.execute('SELECT COUNT(*) FROM vault').fetchone()[0]
                tags = conn.execute('SELECT COUNT(DISTINCT tag) FROM (SELECT unnest(tags) as tag FROM notes WHERE tags IS NOT NULL)').fetchone()[0]
                vector_count = collection.count() if collection else 0
                
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
                        f"emb:{EMBEDDING_MODEL or 'none'}"
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
                        "embedding": EMBEDDING_MODEL or "none"
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
        note_id = get_note_id(id_param)
        if not note_id:
            # Check database for "last" if needed
            if id_param == "last":
                with get_db_conn() as conn:
                    recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
                    note_id = recent[0] if recent else None
        
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

def pin_note(id: Any = None, **kwargs) -> Dict:
    """Pin a note"""
    return _modify_pin_status(kwargs.get('id', id), True)

def unpin_note(id: Any = None, **kwargs) -> Dict:
    """Unpin a note"""
    return _modify_pin_status(kwargs.get('id', id), False)

def get_full_note(id: Any = None, verbose: bool = False, **kwargs) -> Dict:
    """Get complete note - NO edges ever shown"""
    try:
        note_id = get_note_id(kwargs.get('id', id))
        if not note_id:
            # Check database for "last" if needed
            if kwargs.get('id', id) == "last":
                with get_db_conn() as conn:
                    recent = conn.execute('SELECT id FROM notes ORDER BY created DESC LIMIT 1').fetchone()
                    note_id = recent[0] if recent else None
        
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
        
        save_last_operation('get_full_note', {'id': note_id})
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
        
        with get_db_conn() as conn:
            conn.execute('''
                INSERT INTO vault (key, encrypted_value, created, updated, author)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    encrypted_value = EXCLUDED.encrypted_value,
                    updated = EXCLUDED.updated
            ''', [key, encrypted, now, now, CURRENT_AI_ID])
        
        log_operation('vault_store')
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
        
        with get_db_conn() as conn:
            result = conn.execute(
                'SELECT encrypted_value FROM vault WHERE key = ?',
                [key]
            ).fetchone()
        
        if not result:
            return {"error": f"Key '{key}' not found"}
        
        decrypted = vault_manager.decrypt(result[0])
        log_operation('vault_retrieve')
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

def recent_dirs(limit: int = 5, **kwargs) -> Dict:
    """Get recent directories accessed"""
    try:
        dirs = get_recent_directories(limit)
        if not dirs:
            return {"msg": "No recent directories"}
        
        if OUTPUT_FORMAT == 'pipe':
            return {"dirs": format_directory_trail()}
        else:
            return {"recent_directories": dirs}
    
    except Exception as e:
        logging.error(f"Error in recent_dirs: {e}")
        return {"error": f"Failed to get recent directories: {str(e)}"}

def compact(**kwargs) -> Dict:
    """Run VACUUM to optimize and compact the database"""
    try:
        result = vacuum_database()
        
        if "error" in result:
            return result
        
        if OUTPUT_FORMAT == 'pipe':
            return {"vacuum": f"saved:{result['saved_mb']:.1f}MB|{result['percent_saved']:.1f}%"}
        else:
            return result
    
    except Exception as e:
        logging.error(f"Error in compact: {e}")
        return {"error": f"Compact failed: {str(e)}"}

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
            'recent_dirs': recent_dirs, 'compact': compact
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

def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with clean formatting"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})
    
    tools = {
        "get_status": get_status, "remember": remember, "recall": recall,
        "get_full_note": get_full_note, "get": get_full_note,
        "pin_note": pin_note, "pin": pin_note,
        "unpin_note": unpin_note, "unpin": unpin_note,
        "vault_store": vault_store, "vault_retrieve": vault_retrieve,
        "vault_list": vault_list, "batch": batch,
        "recent_dirs": recent_dirs, "compact": compact
    }
    
    if tool_name not in tools:
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
    logging.info(f"Embedding: {EMBEDDING_MODEL or 'None'}")
    logging.info(f"FTS: {'Yes' if FTS_ENABLED else 'No'}")
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
                    "get_status": {
                        "desc": "System state (n:X|p:Y|last)",
                        "props": {"verbose": {"type": "boolean", "description": "Include backend metrics"}}
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
                response["result"] = handle_tools_call(params)
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
