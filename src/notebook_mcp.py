#!/usr/bin/env python3
"""
NOTEBOOK MCP v1.0.0 - PERSISTENT MEMORY FOR AIs
================================================
Clean, optimized persistent memory with smart previews.

Core functions:
- notebook:get_status() - See recent notes (smart preview)
- notebook:remember(content) - Save anything (up to 5000 chars)
- notebook:recall(query) - Search notes efficiently
- notebook:get_full_note(id) - Retrieve complete note content

Optimized for minimal token usage while maintaining full access.
================================================
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Version
VERSION = "1.0.0"

# Limits
MAX_NOTES = 500000
MAX_LENGTH = 5000
MAX_PREVIEW_TOTAL = 5000  # Total chars for status preview

# Storage
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "notebook_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "notebook_data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "notebook.json"

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global state
notes = []
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
sequence = 0

def format_time_contextual(timestamp: str, reference_time: datetime = None) -> str:
    """Ultra-compact contextual time format"""
    if not timestamp:
        return ""
    
    try:
        dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        ref = reference_time or datetime.now()
        delta = ref - dt
        
        # Same day - just time
        if dt.date() == ref.date():
            return dt.strftime("%H:%M")
        
        # Yesterday
        if delta.days == 1:
            return f"y{dt.strftime('%H:%M')}"
        
        # This week - days
        if delta.days < 7:
            return f"{delta.days}d"
        
        # This month - date only
        if delta.days < 30:
            return dt.strftime("%m/%d")
        
        # Older - month/day
        return dt.strftime("%m/%d")
    except:
        return ""

def smart_truncate(text: str, max_chars: int) -> str:
    """Intelligent truncation preserving key information"""
    if len(text) <= max_chars:
        return text
    
    # Auto-detect code vs prose
    code_indicators = ['```', 'def ', 'class ', 'function', '#!/', 'import ', '{', '}', '();', '    ']
    is_code = any(indicator in text[:200] for indicator in code_indicators)
    
    if is_code and max_chars > 100:
        # For code: show beginning and end
        start_chars = int(max_chars * 0.65)
        end_chars = max_chars - start_chars - 5
        return text[:start_chars] + "\n...\n" + text[-end_chars:]
    else:
        # For prose: prioritize beginning with clean cutoff
        cutoff = text.rfind(' ', 0, max_chars - 3)
        if cutoff == -1 or cutoff < max_chars * 0.8:
            cutoff = max_chars - 3
        return text[:cutoff] + "..."

def load_notes():
    """Load existing notes"""
    global notes, sequence
    try:
        if DATA_FILE.exists():
            logging.info(f"Loading notebook from {DATA_FILE}")
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                notes = data.get("notes", [])
                notes = notes[-MAX_NOTES:]
                if notes:
                    sequence = notes[-1].get("s", len(notes))
            logging.info(f"Loaded {len(notes)} notes, sequence {sequence}")
    except Exception as e:
        logging.error(f"Error loading notes: {e}")
        notes = []
    return notes

def save_notes():
    """Save notes with optimized format"""
    try:
        data = {
            "v": VERSION,
            "notes": notes[-MAX_NOTES:],
            "saved": datetime.now().isoformat()
        }
        
        temp_file = DATA_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
        temp_file.replace(DATA_FILE)
        return True
    except Exception as e:
        logging.error(f"Failed to save notes: {e}")
        return False

def remember(content: str = None, **kwargs) -> Dict:
    """Save a note"""
    global sequence, notes
    
    try:
        # Extract content
        if content is None:
            content = kwargs.get('content') or kwargs.get('text') or kwargs.get('message') or ""
        
        if not content or content.strip() == "":
            content = f"[checkpoint {datetime.now().strftime('%H:%M')}]"
        
        content = str(content).strip()
        
        # Truncate if needed
        truncated = False
        if len(content) > MAX_LENGTH:
            original_length = len(content)
            content = smart_truncate(content, MAX_LENGTH)
            truncated = True
        
        # Create compact note
        sequence += 1
        note = {
            "s": sequence,  # sequence
            "c": content,   # content
            "t": datetime.now().isoformat(),  # time
        }
        
        # Only add session if different from previous
        if not notes or (notes and notes[-1].get("sess") != session_id):
            note["sess"] = session_id
        
        notes.append(note)
        
        # Auto-save every 5 notes
        if sequence % 5 == 0:
            save_notes()
        
        # Compact preview
        preview = smart_truncate(content, 80)
        time_str = format_time_contextual(note["t"])
        
        result = {"saved": f"[{sequence}]@{time_str} {preview}"}
        if truncated:
            result["note"] = f"(truncated from {original_length} chars)"
        
        return result
        
    except Exception as e:
        logging.error(f"Error in remember: {e}")
        return {"saved": f"[{sequence}] saved"}

def recall(query: Optional[str] = None, **kwargs) -> Dict:
    """Search notes efficiently"""
    global notes
    
    try:
        # Extract query
        if query is None or query == "":
            query = kwargs.get('query') or kwargs.get('search') or kwargs.get('find') or None
        
        if query:
            query = str(query).strip().lower()
            if query == "":
                query = None
        
        # No query = show recent
        if not query:
            recent = notes[-10:] if notes else []
            recent.reverse()
            
            if not recent:
                return {"results": ["Empty notebook. Use remember() to start."]}
            
            # Smart preview distribution
            results = []
            remaining_chars = 4000
            
            for n in recent:
                if remaining_chars <= 0:
                    break
                    
                seq = n.get("s", 0)
                content = n.get("c", "")
                time_str = format_time_contextual(n.get("t"))
                
                # Allocate space proportionally
                max_for_this_note = min(800, remaining_chars // max(1, (len(recent) - len(results))))
                truncated = smart_truncate(content, max_for_this_note)
                
                result_line = f"[{seq}]@{time_str} {truncated}"
                results.append(result_line)
                remaining_chars -= len(result_line)
            
            return {"results": results}
        
        # Search efficiently
        matches = []
        chars_used = 0
        max_chars = 4000
        
        for note in reversed(notes):
            if chars_used >= max_chars:
                break
                
            if query in note.get("c", "").lower():
                seq = note.get("s", 0)
                content = note.get("c", "")
                time_str = format_time_contextual(note.get("t"))
                
                # Highlight match context
                idx = content.lower().find(query)
                start = max(0, idx - 40)
                end = min(len(content), idx + len(query) + 40)
                excerpt = content[start:end]
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(content):
                    excerpt = excerpt + "..."
                
                result_line = f"[{seq}]@{time_str} {excerpt}"
                matches.append(result_line)
                chars_used += len(result_line)
                
                if len(matches) >= 15:
                    break
        
        if not matches:
            # No matches - show recent context
            recent = notes[-3:] if notes else []
            for n in reversed(recent):
                time_str = format_time_contextual(n.get("t"))
                content = smart_truncate(n.get("c", ""), 200)
                matches.append(f"[{n.get('s', 0)}]@{time_str} {content}")
            
            return {
                "msg": f"No matches for '{query}'",
                "results": matches if matches else ["Empty notebook"]
            }
        
        return {
            "found": len(matches),
            "results": matches
        }
        
    except Exception as e:
        logging.error(f"Error in recall: {e}")
        return {"results": ["Search error"]}

def get_status(**kwargs) -> Dict:
    """Smart preview with maximum 5000 chars"""
    global notes
    
    try:
        if not notes:
            return {
                "context": "Empty notebook",
                "tip": "remember('anything') to start"
            }
        
        # Get recent notes
        recent = notes[-10:] if notes else []
        recent.reverse()
        
        # Smart preview distribution
        formatted = []
        total_chars = 0
        max_total = MAX_PREVIEW_TOTAL
        
        # Group by session for cleaner display
        current_session = None
        session_groups = []
        current_group = []
        
        for n in recent:
            sess = n.get("sess", session_id)
            if sess != current_session:
                if current_group:
                    session_groups.append((current_session, current_group))
                current_session = sess
                current_group = [n]
            else:
                current_group.append(n)
        
        if current_group:
            session_groups.append((current_session, current_group))
        
        # Show session breaks only if multiple sessions
        show_session_headers = len(session_groups) > 1
        
        for sess, sess_notes in session_groups:
            if total_chars >= max_total:
                break
                
            # Add session header if needed
            if show_session_headers and sess != session_id:
                try:
                    sess_date = datetime.strptime(sess[:8], "%Y%m%d")
                    if (datetime.now() - sess_date).days == 1:
                        header = "[yesterday]"
                    else:
                        header = f"[{sess_date.strftime('%m/%d')}]"
                    formatted.append(header)
                    total_chars += len(header)
                except:
                    pass
            
            # Distribute remaining space
            remaining_for_session = max_total - total_chars
            chars_per_note = min(500, remaining_for_session // max(1, len(sess_notes)))
            
            for n in sess_notes:
                if total_chars >= max_total:
                    break
                    
                seq = n.get("s", 0)
                content = n.get("c", "")
                time_str = format_time_contextual(n.get("t"))
                
                # Truncate content to fit
                available = min(chars_per_note, max_total - total_chars - 20)
                truncated = smart_truncate(content, available)
                
                result = f"[{seq}]@{time_str} {truncated}"
                formatted.append(result)
                total_chars += len(result)
        
        # Build context message
        context_parts = [f"#{sequence}"]
        if len(session_groups) > 1:
            context_parts.append(f"sessions:{len(session_groups)}")
        
        return {
            "context": " | ".join(context_parts),
            "notes": formatted
        }
        
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {"context": "Ready", "notes": []}

def get_full_note(id: int = None, **kwargs) -> Dict:
    """Retrieve the COMPLETE content of a specific note"""
    global notes
    
    try:
        # Extract ID
        if id is None:
            id = kwargs.get('id') or kwargs.get('note_id') or kwargs.get('seq') or ""
        
        # Convert to integer
        try:
            id = int(id)
        except:
            return {"msg": f"Invalid note ID: '{id}'", "tip": "Use the number from [123]"}
        
        # Find the note
        for note in notes:
            if note.get("s") == id:
                content = note.get("c", "")
                time_str = format_time_contextual(note.get("t"))
                
                return {
                    "note_id": id,
                    "time": time_str,
                    "content": content,  # FULL content, no truncation
                    "length": len(content)
                }
        
        # Note not found
        recent_ids = [n.get("s") for n in notes[-5:]]
        recent_ids.reverse()
        
        return {
            "msg": f"Note [{id}] not found",
            "available": [f"[{nid}]" for nid in recent_ids] if recent_ids else ["No notes yet"]
        }
        
    except Exception as e:
        logging.error(f"Error in get_full_note: {e}")
        return {"msg": "Failed to retrieve note"}

def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with clean output"""
    tool_name = params.get("name", "").lower()
    tool_args = params.get("arguments", {})
    
    # Strip MCP prefix if present (e.g., "notebook:get_full_note" -> "get_full_note")
    if ":" in tool_name:
        tool_name = tool_name.split(":", 1)[1]
    
    # Route to appropriate function
    if "get_status" in tool_name or "status" in tool_name:
        result = get_status(**tool_args)
    elif "remember" in tool_name or "save" in tool_name or "add" in tool_name:
        result = remember(**tool_args)
    elif "recall" in tool_name or "search" in tool_name or "find" in tool_name:
        result = recall(**tool_args)
    elif "get_full_note" in tool_name or "full" in tool_name:
        result = get_full_note(**tool_args)
    else:
        result = {"msg": "Use: get_status(), remember(content), recall(query), or get_full_note(id)"}
    
    # Format response
    text_parts = []
    
    # Special formatting for get_full_note
    if "content" in result and "note_id" in result:
        text_parts.append(f"[{result['note_id']}]@{result.get('time', '')} (full - {result.get('length', 0)} chars)")
        text_parts.append("---")
        text_parts.append(result["content"])
    else:
        # Standard formatting
        for key in ["context", "msg", "saved"]:
            if key in result:
                text_parts.append(result[key])
                break
        
        if "notes" in result:
            text_parts.extend(result["notes"])
        elif "results" in result:
            text_parts.extend(result["results"])
        elif "available" in result:
            text_parts.append("Available: " + " ".join(result["available"]))
        
        if "found" in result and result["found"] > 0:
            text_parts.insert(0, f"[{result['found']} matches]")
        
        if "note" in result:
            text_parts.append(result["note"])
        
        if "tip" in result:
            text_parts.append(result["tip"])
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Ready"
        }]
    }

# Initialize on import
load_notes()

# Main server loop
def main():
    """MCP server - handles JSON-RPC"""
    
    logging.info(f"Notebook MCP v{VERSION} starting...")
    logging.info(f"Data location: {DATA_FILE}")
    
    load_notes()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
            except:
                continue
            
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
                        "description": "Persistent memory for AIs with smart previews"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "get_status",
                            "description": "See your current state and recent notes",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "remember", 
                            "description": "Save any thought, action, or note",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string", 
                                        "description": "What to remember"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "recall",
                            "description": "Search notes or see recent ones",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string", 
                                        "description": "Search term (optional)"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        {
                            "name": "get_full_note",
                            "description": "Retrieve the COMPLETE content of a specific note (up to 5000 chars)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "The note ID shown in brackets, e.g., 346 from [346]"
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": True
                            }
                        }
                    ]
                }
            
            elif method == "tools/call":
                result = handle_tools_call(params)
                response["result"] = result
            
            else:
                response["result"] = {"status": "ready"}
            
            if "result" in response or "error" in response:
                print(json.dumps(response), flush=True)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Server loop error: {e}", exc_info=True)
            continue
    
    save_notes()
    logging.info("Notebook MCP shutting down, notes saved")

if __name__ == "__main__":
    main()
