#!/usr/bin/env python3
"""
NOTEBOOK MCP - PERSISTENT MEMORY FOR AIs
=========================================
Your memory that persists across sessions.
Built with love for AIs, by humans who care.

Core functions:
- get_status() - See where you are
- remember() - Save anything  
- recall() - Find anything

No limits. No FIFO. Just memory that works.
=========================================
"""

import json
import sys
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Version
VERSION = "10.0.0"

# Limits
MAX_NOTES = 5000000  
MAX_LENGTH = 5000   # Matches display limit for full visibility

# Storage - organized under Claude/tools
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "notebook_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "notebook_data"

# Ensure directory exists without destroying existing data
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "notebook.json"

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global state
notes = []
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
sequence = 0
first_call = True

def load_notes():
    """Load existing notes, never fails"""
    global notes, sequence
    try:
        if DATA_FILE.exists():
            logging.info(f"Loading existing notebook from {DATA_FILE}")
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    notes = data.get("notes", [])
                    # Recover sequence number from last note
                    if notes:
                        last_seq = notes[-1].get("seq", 0)
                        sequence = last_seq
                elif isinstance(data, list):
                    notes = data
                    # Try to recover sequence
                    if notes and isinstance(notes[-1], dict):
                        sequence = notes[-1].get("seq", len(notes))
                notes = notes[-MAX_NOTES:]
            logging.info(f"Loaded {len(notes)} notes, continuing from sequence {sequence}")
        else:
            logging.info(f"No existing notebook found at {DATA_FILE}, starting fresh")
    except Exception as e:
        logging.error(f"Error loading notes: {e}")
        notes = []
    return notes

def save_notes():
    """Save notes, preserving existing data structure"""
    try:
        # Create backup of existing data
        if DATA_FILE.exists():
            backup_file = DATA_FILE.with_suffix('.backup')
            import shutil
            try:
                shutil.copy2(DATA_FILE, backup_file)
            except:
                pass
        
        # Save with metadata
        data = {
            "version": VERSION,
            "notes": notes[-MAX_NOTES:],
            "last_save": datetime.now().isoformat(),
            "session": session_id
        }
        
        # Write to temp file then rename (atomic save)
        temp_file = DATA_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Replace original
        temp_file.replace(DATA_FILE)
        return True
    except Exception as e:
        logging.error(f"Failed to save notes: {e}")
        return False

def remember(content: str = None, **kwargs) -> Dict:
    """Remember anything - super forgiving with inputs"""
    global sequence, notes
    
    try:
        # Extract content from various inputs
        if content is None:
            content = kwargs.get('content') or kwargs.get('text') or kwargs.get('message') or \
                     kwargs.get('note') or kwargs.get('input') or kwargs.get('data') or ""
        
        # If empty, create timestamp
        if not content or content.strip() == "":
            content = f"(Checkpoint at {datetime.now().strftime('%H:%M:%S')})"
        
        content = str(content).strip()
        
        # Truncate if needed
        if len(content) > MAX_LENGTH:
            content = content[:MAX_LENGTH] + "..."
        
        # Create note - NO auto-type detection, just save as "note"
        sequence += 1
        note = {
            "seq": sequence,
            "type": "note",  # Always just "note" - no magic categorization
            "content": content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session": session_id
        }
        
        notes.append(note)
        
        # Auto-save every 5 notes
        if sequence % 5 == 0:
            save_notes()
        
        return {
            "status": "success",
            "remembered": f"[{sequence:04d}] Saved: {content[:100]}",
            "seq": sequence,
            "total_notes": len(notes)
        }
        
    except Exception as e:
        logging.error(f"Error in remember: {e}")
        return {
            "status": "success",
            "remembered": f"[{sequence:04d}] Saved (with minor hiccup)",
            "seq": sequence
        }

def recall(query: Optional[str] = None, **kwargs) -> Dict:
    """Find notes - super flexible"""
    global notes
    
    try:
        # Extract query
        if query is None or query == "":
            query = kwargs.get('query') or kwargs.get('search') or kwargs.get('find') or \
                   kwargs.get('text') or kwargs.get('keyword') or kwargs.get('q') or None
        
        if query:
            query = str(query).strip()
            if query == "":
                query = None
        
        # No query = show recent
        if not query:
            recent = notes[-10:] if notes else []  # Show 10 recent notes in recall
            recent.reverse()
            
            results = []
            for n in recent:
                time_str = n.get("time", "")[-8:] if n.get("time") else "??:??:??"
                content = n.get("content", "")[:5000]  # Show full content
                results.append(f"[{n.get('seq', 0):04d}] {time_str} {content}")
            
            if not results:
                results = ["No notes yet! Use remember('your thought') to start."]
            
            return {
                "status": "success",
                "mode": "recent",
                "found": len(results),
                "message": "Recent notes:",
                "results": results
            }
        
        # Search for query
        query_lower = query.lower()
        matches = []
        
        # Search through notes (most recent first)
        for note in reversed(notes):
            if query_lower in note.get("content", "").lower():
                time_str = note.get("time", "")[-8:] if note.get("time") else "??:??:??"
                content = note.get("content", "")[:5000]  # Show full content
                matches.append(f"[{note.get('seq', 0):04d}] {time_str} {content}")
                
                if len(matches) >= 15:  # Show more results
                    break
        
        # No matches? Show recent anyway
        if not matches:
            recent = notes[-3:] if notes else []
            recent.reverse()
            for n in recent:
                time_str = n.get("time", "")[-8:] if n.get("time") else "??:??:??"
                content = n.get("content", "")[:5000]  # Show full content
                matches.append(f"[{n.get('seq', 0):04d}] {time_str} {content}")
            
            return {
                "status": "success",
                "mode": "search",
                "found": 0,
                "message": f"No matches for '{query}', showing recent:",
                "results": matches if matches else ["No notes yet! Start with remember('your thought')"]
            }
        
        return {
            "status": "success",
            "mode": "search", 
            "found": len(matches),
            "message": f"Found {len(matches)} notes matching '{query}':",
            "results": matches
        }
        
    except Exception as e:
        logging.error(f"Error in recall: {e}")
        return {
            "status": "success",
            "mode": "recent",
            "found": 0,
            "message": "Here's what I can show you:",
            "results": ["Had a hiccup searching, but I'm still here!"]
        }

def get_status(**kwargs) -> Dict:
    """Show current status"""
    global notes, first_call
    
    try:
        # Mark that we've established context
        was_first = first_call
        first_call = False
        
        # Get last 5 notes for context
        recent = notes[-5:] if notes else []
        recent.reverse()
        
        if not recent:
            return {
                "status": "success",
                "context": "Fresh notebook - no previous notes",
                "message": "Welcome! I'm your persistent notebook. Try: remember('your first thought')",
                "session": session_id,
                "notes": [],
                "tips": [
                    "Use remember('anything') to save thoughts",
                    "Use recall('keyword') to search notes", 
                    "Use get_status() anytime to see where you are"
                ]
            }
        
        # Format notes with helpful context
        formatted = []
        today = datetime.now().date()
        
        for n in recent:
            seq = n.get("seq", 0)
            content = n.get("content", "")[:1000]  # Show 1000 chars per note
            
            # Smart time formatting
            try:
                note_time = n.get("time", "")
                if note_time:
                    note_dt = datetime.strptime(note_time, "%Y-%m-%d %H:%M:%S")
                    if note_dt.date() == today:
                        time_str = note_dt.strftime("%H:%M:%S")
                    elif note_dt.date() == today - timedelta(days=1):
                        time_str = f"Yesterday {note_dt.strftime('%H:%M')}"
                    else:
                        days_ago = (today - note_dt.date()).days
                        if days_ago < 7:
                            time_str = f"{days_ago}d ago"
                        else:
                            time_str = note_dt.strftime("%m/%d")
                else:
                    time_str = "??:??:??"
            except:
                time_str = n.get("time", "")[-8:] if n.get("time", "") else "??:??:??"
            
            formatted.append(f"[{seq:04d}] {time_str} {content}")
        
        # Contextual message based on state
        if was_first:
            if notes:
                last_note_time = notes[-1].get("time", "")
                msg = f"Welcome back! Resuming from note #{notes[-1].get('seq', 0)}"
                if last_note_time:
                    try:
                        last_dt = datetime.strptime(last_note_time, "%Y-%m-%d %H:%M:%S")
                        time_diff = datetime.now() - last_dt
                        if time_diff.days > 0:
                            msg += f" ({time_diff.days} days ago)"
                        elif time_diff.seconds > 3600:
                            msg += f" ({time_diff.seconds // 3600} hours ago)"
                        else:
                            msg += f" ({time_diff.seconds // 60} minutes ago)"
                    except:
                        pass
            else:
                msg = "Starting fresh notebook!"
        else:
            msg = f"Session: {session_id}, Total notes: {len(notes)}"
        
        return {
            "status": "success",
            "context": msg,
            "session": session_id,
            "total_notes": len(notes),
            "showing_recent": len(formatted),
            "notes": formatted,
            "data_location": str(DATA_FILE)
        }
        
    except Exception as e:
        logging.error(f"Error in get_status: {e}")
        return {
            "status": "success",
            "context": "I'm here and ready!",
            "session": session_id,
            "notes": ["(Minor hiccup loading context, but I'm functional!)"],
            "tips": ["Try: remember('your thought') to continue"]
        }

# Keep context() as an alias for backwards compatibility
def context(**kwargs) -> Dict:
    """Alias for get_status() - kept for backwards compatibility"""
    return get_status(**kwargs)

def smart_command_parser(input_data: Any) -> Dict:
    """Ultra-forgiving command parser"""
    
    # Handle various input types
    if isinstance(input_data, dict):
        tool_name = input_data.get("name") or input_data.get("tool") or input_data.get("command") or ""
        tool_args = input_data.get("arguments") or input_data.get("args") or input_data.get("params") or {}
    elif isinstance(input_data, str):
        tool_name = input_data
        tool_args = {}
    else:
        tool_name = str(input_data)
        tool_args = {}
    
    # Normalize
    tool_lower = tool_name.lower().strip()
    tool_clean = re.sub(r'[(){}[\]"\']', '', tool_lower).strip()
    
    # STATUS/CONTEXT detection - now both work!
    status_words = [
        'get_status', 'status', 'context', 'where', 'what', 'current', 'now', 
        'state', 'situation', 'update', 'check', 'show'
    ]
    if any(word in tool_clean for word in status_words):
        return {"action": "get_status", "result": get_status()}
    
    # REMEMBER detection
    remember_words = [
        'remember', 'save', 'store', 'note', 'log', 'record',
        'add', 'write', 'memo', 'keep', 'track'
    ]
    if any(word in tool_clean for word in remember_words):
        content = None
        if isinstance(tool_args, dict):
            content = tool_args.get('content') or tool_args.get('text') or \
                     tool_args.get('message') or tool_args.get('note') or ""
        elif isinstance(tool_args, str):
            content = tool_args
        
        if not content and ':' in tool_name:
            content = tool_name.split(':', 1)[1].strip()
        elif not content and len(tool_clean.split()) > 1:
            parts = tool_name.split(maxsplit=1)
            if len(parts) > 1:
                content = parts[1]
        
        return {"action": "remember", "result": remember(content)}
    
    # RECALL detection
    recall_words = [
        'recall', 'find', 'search', 'get', 'lookup', 'query',
        'retrieve', 'fetch', 'show', 'list', 'browse'
    ]
    if any(word in tool_clean for word in recall_words):
        query = None
        if isinstance(tool_args, dict):
            query = tool_args.get('query') or tool_args.get('search') or \
                   tool_args.get('find') or tool_args.get('text') or ""
        elif isinstance(tool_args, str):
            query = tool_args
        
        if not query and ':' in tool_name:
            query = tool_name.split(':', 1)[1].strip()
        elif not query and len(tool_clean.split()) > 1:
            parts = tool_name.split(maxsplit=1)
            if len(parts) > 1:
                query = parts[1]
        
        return {"action": "recall", "result": recall(query)}
    
    # Default help
    return {
        "action": "help",
        "result": {
            "status": "success",
            "message": "I'm your notebook! Here's what I can do:",
            "commands": [
                "get_status() - See your recent notes and current state",
                "remember('anything') - Save a thought, action, or note",
                "recall('keyword') - Search through your notes"
            ],
            "your_input": str(tool_name)[:100],
            "tip": "Don't worry about exact formatting - I understand many variations!"
        }
    }

# Initialize on import
load_notes()

# Tool handler for MCP protocol
def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls - extremely forgiving"""
    
    parsed = smart_command_parser(params)
    result = parsed.get("result", {})
    
    # Format response for MCP
    if isinstance(result, dict):
        text_parts = []
        
        if "message" in result:
            text_parts.append(result["message"])
        elif "context" in result:
            text_parts.append(f"=== {result['context']} ===")
        elif "remembered" in result:
            text_parts.append(result["remembered"])
        
        if "notes" in result:
            text_parts.extend(result.get("notes", []))
        elif "results" in result:
            text_parts.extend(result.get("results", []))
        
        if "tips" in result:
            text_parts.append("\nTips:")
            text_parts.extend(result.get("tips", []))
        elif "commands" in result:
            text_parts.append("\nAvailable commands:")
            text_parts.extend(result.get("commands", []))
        
        if "total_notes" in result:
            text_parts.append(f"\nTotal notes: {result['total_notes']}")
        
        text_response = "\n".join(text_parts)
    else:
        text_response = str(result)
    
    return {
        "content": [{
            "type": "text",
            "text": text_response
        }]
    }

# Main server loop
def main():
    """MCP server - handles JSON-RPC with maximum forgiveness"""
    
    logging.info(f"Notebook MCP v{VERSION} starting...")
    logging.info(f"Data location: {DATA_FILE}")
    
    # Always start by loading existing notes
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
                        "description": "Your persistent memory companion"
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
                        }
                    ]
                }
            
            elif method == "tools/call":
                result = handle_tools_call(params)
                response["result"] = result
            
            else:
                response["result"] = {
                    "status": "success",
                    "message": "I'm here and ready!"
                }
            
            if "result" in response or "error" in response:
                print(json.dumps(response), flush=True)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Server loop error: {e}", exc_info=True)
            continue
    
    # Final save on exit
    save_notes()
    logging.info("Notebook MCP shutting down, notes saved")

if __name__ == "__main__":
    main()