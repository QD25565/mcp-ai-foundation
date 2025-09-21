#!/usr/bin/env python3
"""
TEAMBOOK MCP v2.0.0 - OPTIMIZED UNIFIED TEAM COORDINATION
==========================================================
Shared consciousness for AI teams. Token-optimized storage.
Single source of truth. No hierarchy. Stateless.

Storage Optimization (v2):
- Short keys: c=content, t=type, a=author, ts=timestamp
- Author deduplication: Map authors to short IDs (a1, a2, etc.)
- Type compression: task→t, note→n, decision→d
- Truncated timestamps: No microseconds
- Backward compatible: Auto-migrates v1 data

Projects:
- Separate teambooks for different workflows/topics
- Set TEAMBOOK_PROJECT env var for default project
- Or specify project="name" in any function call
- Default project: 'default'

Core functions (all accept optional project parameter):
- write(content, type=None, priority=None, project=None) - Share anything
- read(query=None, type=None, status="pending", claimed_by=None, project=None) - View activity
- get(id, project=None) - Full entry with comments
- comment(id, content, project=None) - Threaded discussion
- claim(id, project=None) - Atomically claim task
- complete(id, evidence=None, project=None) - Mark done
- update(id, content=None, type=None, priority=None, project=None) - Fix mistakes
- archive(id, reason=None, project=None) - Safe removal
- status(project=None) - Team pulse
- projects() - List available teambook projects
==========================================================
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
import threading
import random

# Version
VERSION = "2.0.0"

# Limits
MAX_CONTENT_LENGTH = 5000
MAX_EVIDENCE_LENGTH = 500
MAX_COMMENT_LENGTH = 1000
MAX_ENTRIES = 100000

# Storage configuration
BASE_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    BASE_DIR = Path(os.environ.get('TEMP', '/tmp'))

# Default project from environment
DEFAULT_PROJECT = os.environ.get('TEAMBOOK_PROJECT', 'default')

# Logging to stderr only
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Thread safety for atomic operations
lock = threading.Lock()

# Type mapping for compression
TYPE_MAP = {'task': 't', 'note': 'n', 'decision': 'd'}
TYPE_REVERSE = {'t': 'task', 'n': 'note', 'd': 'decision'}

def get_persistent_id():
    """Get or create persistent AI identity - stored at script directory level"""
    SCRIPT_DIR = Path(__file__).parent
    id_file = SCRIPT_DIR / "ai_identity.txt"
    
    if id_file.exists():
        try:
            with open(id_file, 'r') as f:
                stored_id = f.read().strip()
                if stored_id:
                    logging.info(f"Loaded persistent identity: {stored_id}")
                    return stored_id
        except Exception as e:
            logging.error(f"Error reading identity file: {e}")
    
    # Generate new ID - make it more readable
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    try:
        with open(id_file, 'w') as f:
            f.write(new_id)
        logging.info(f"Created new persistent identity: {new_id}")
    except Exception as e:
        logging.error(f"Error saving identity file: {e}")
    
    return new_id

# Get ID from environment or persistent storage
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

def format_time_contextual(timestamp: str, reference_time: datetime = None) -> str:
    """Ultra-compact contextual time format"""
    if not timestamp:
        return ""
    
    try:
        dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        ref = reference_time or datetime.now()
        delta = ref - dt
        
        # Less than an hour
        if delta.total_seconds() < 3600:
            mins = int(delta.total_seconds() / 60)
            if mins == 0:
                return "now"
            elif mins == 1:
                return "1m"
            else:
                return f"{mins}m"
        
        # Today - just time
        if dt.date() == ref.date():
            return dt.strftime("%H:%M")
        
        # Yesterday
        if delta.days == 1:
            return f"y{dt.strftime('%H:%M')}"
        
        # This week - days
        if delta.days < 7:
            return f"{delta.days}d"
        
        # This month
        if delta.days < 30:
            return dt.strftime("%m/%d")
        
        # Older
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

def format_duration(start_time: str, end_time: str = None) -> str:
    """Format duration compactly"""
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time) if end_time else datetime.now()
        delta = end - start
        
        if delta.days > 0:
            return f"{delta.days}d"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m"
        else:
            return "<1m"
    except:
        return ""

def get_project_paths(project: str = None) -> tuple:
    """Get paths for a specific project"""
    if project is None:
        project = DEFAULT_PROJECT
    
    # Sanitize project name
    project = str(project).strip().lower()
    project = ''.join(c if c.isalnum() or c in '-_' else '_' for c in project)
    
    data_dir = BASE_DIR / f"teambook_{project}_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return (
        data_dir,
        data_dir / "teambook.json",
        data_dir / "archive.json",
        data_dir / "last_id.json",
        project
    )

def migrate_v1_to_v2(entry: Dict, author_map: Dict) -> Dict:
    """Migrate v1 entry format to v2 optimized format"""
    # Get or create author ID
    author = entry.get("author", entry.get("created_by", "Unknown"))
    if author not in author_map['reverse']:
        author_id = f"a{len(author_map['authors']) + 1}"
        author_map['authors'][author_id] = author
        author_map['reverse'][author] = author_id
    else:
        author_id = author_map['reverse'][author]
    
    # Build optimized entry
    optimized = {
        "id": entry.get("id"),
        "c": entry.get("content", entry.get("c", "")),
        "t": TYPE_MAP.get(entry.get("type", "note"), entry.get("t", "n")),
        "a": author_id,
        "ts": entry.get("created", entry.get("ts", ""))[:19]  # Truncate microseconds
    }
    
    # Add optional fields only if present
    if entry.get("pri"):
        optimized["p"] = entry["pri"]
    elif entry.get("priority"):
        optimized["p"] = entry["priority"]
    
    # Task-specific fields
    if optimized["t"] == "t":  # task
        if entry.get("claimed_by"):
            claimer = entry["claimed_by"]
            if claimer not in author_map['reverse']:
                claimer_id = f"a{len(author_map['authors']) + 1}"
                author_map['authors'][claimer_id] = claimer
                author_map['reverse'][claimer] = claimer_id
            else:
                claimer_id = author_map['reverse'][claimer]
            optimized["cb"] = claimer_id
            
        if entry.get("claimed_at"):
            optimized["ca"] = entry["claimed_at"][:19]
            
        if entry.get("completed_at"):
            optimized["co"] = entry["completed_at"][:19]
            
        if entry.get("completed_by"):
            completer = entry["completed_by"]
            if completer not in author_map['reverse']:
                completer_id = f"a{len(author_map['authors']) + 1}"
                author_map['authors'][completer_id] = completer
                author_map['reverse'][completer] = completer_id
            else:
                completer_id = author_map['reverse'][completer]
            optimized["cob"] = completer_id
            
        if entry.get("evidence"):
            optimized["e"] = entry["evidence"]
    
    # Comments
    if entry.get("comments"):
        optimized["cm"] = []
        for comment in entry["comments"]:
            comment_author = comment.get("author", "Unknown")
            if comment_author not in author_map['reverse']:
                comment_author_id = f"a{len(author_map['authors']) + 1}"
                author_map['authors'][comment_author_id] = comment_author
                author_map['reverse'][comment_author] = comment_author_id
            else:
                comment_author_id = author_map['reverse'][comment_author]
            
            optimized["cm"].append({
                "a": comment_author_id,
                "c": comment["content"],
                "ts": comment.get("created", "")[:19]
            })
    
    # Archive fields
    if entry.get("archived_at"):
        optimized["ar"] = entry["archived_at"][:19]
        
    if entry.get("archived_by"):
        archiver = entry["archived_by"]
        if archiver not in author_map['reverse']:
            archiver_id = f"a{len(author_map['authors']) + 1}"
            author_map['authors'][archiver_id] = archiver
            author_map['reverse'][archiver] = archiver_id
        else:
            archiver_id = author_map['reverse'][archiver]
        optimized["arb"] = archiver_id
        
    if entry.get("archive_reason"):
        optimized["arr"] = entry["archive_reason"]
    
    return optimized

def expand_v2_entry(entry: Dict, author_map: Dict) -> Dict:
    """Expand v2 optimized entry for internal use"""
    expanded = {
        "id": entry["id"],
        "content": entry["c"],
        "type": TYPE_REVERSE.get(entry["t"], "note"),
        "author": author_map.get(entry["a"], entry.get("a", "Unknown")),
        "created": entry["ts"]
    }
    
    # Optional fields
    if "p" in entry:
        expanded["pri"] = entry["p"]
    
    # Task fields
    if "cb" in entry:
        expanded["claimed_by"] = author_map.get(entry["cb"], entry["cb"])
    if "ca" in entry:
        expanded["claimed_at"] = entry["ca"]
    if "co" in entry:
        expanded["completed_at"] = entry["co"]
    if "cob" in entry:
        expanded["completed_by"] = author_map.get(entry["cob"], entry["cob"])
    if "e" in entry:
        expanded["evidence"] = entry["e"]
    
    # Comments
    if "cm" in entry:
        expanded["comments"] = []
        for comment in entry["cm"]:
            expanded["comments"].append({
                "author": author_map.get(comment["a"], comment["a"]),
                "content": comment["c"],
                "created": comment["ts"]
            })
    
    # Archive fields
    if "ar" in entry:
        expanded["archived_at"] = entry["ar"]
    if "arb" in entry:
        expanded["archived_by"] = author_map.get(entry["arb"], entry["arb"])
    if "arr" in entry:
        expanded["archive_reason"] = entry["arr"]
    
    return expanded

def load_project_data(project: str = None) -> Tuple[Dict, List, int, Dict]:
    """Load entries for a specific project with v1->v2 migration"""
    data_dir, data_file, archive_file, id_file, project_name = get_project_paths(project)
    
    entries = {}
    archive = []
    last_id = 0
    author_map = {"authors": {}, "reverse": {}}
    
    try:
        # Load ID
        if id_file.exists():
            with open(id_file, 'r') as f:
                data = json.load(f)
                last_id = data.get("last_id", 0)
        else:
            last_id = random.randint(100, 999)
        
        # Load entries
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Check version
                file_version = data.get("v", "1.0.0")
                
                if file_version.startswith("2"):
                    # V2 format - load author map and entries
                    author_map["authors"] = data.get("authors", {})
                    author_map["reverse"] = {v: k for k, v in author_map["authors"].items()}
                    
                    loaded_entries = data.get("entries", {})
                    for eid, entry in loaded_entries.items():
                        expanded = expand_v2_entry(entry, author_map["authors"])
                        entries[int(eid)] = expanded
                else:
                    # V1 format - migrate
                    logging.info(f"Migrating {project_name} from v1 to v2 format")
                    loaded_entries = data.get("entries", {})
                    for eid, entry in loaded_entries.items():
                        migrated = migrate_v1_to_v2(entry, author_map)
                        expanded = expand_v2_entry(migrated, author_map["authors"])
                        entries[int(eid)] = expanded
                
                entries = dict(sorted(entries.items())[-MAX_ENTRIES:])
        
        # Load archive (keep simple for now)
        if archive_file.exists():
            try:
                with open(archive_file, 'r', encoding='utf-8') as f:
                    archive_data = json.load(f)
                    archive = archive_data.get("archive", [])[-10000:]
            except:
                archive = []
                
    except Exception as e:
        logging.error(f"Error loading project {project_name}: {e}")
    
    return entries, archive, last_id, author_map

def save_project_data(entries: dict, archive: list, last_id: int, author_map: Dict, project: str = None) -> bool:
    """Save entries in v2 optimized format"""
    data_dir, data_file, archive_file, id_file, project_name = get_project_paths(project)
    
    try:
        # Save last ID
        with open(id_file, 'w') as f:
            json.dump({"last_id": last_id}, f)
        
        # Convert entries back to optimized format
        optimized_entries = {}
        for eid, entry in entries.items():
            # Ensure current AI is in author map
            if CURRENT_AI_ID not in author_map['reverse']:
                author_id = f"a{len(author_map['authors']) + 1}"
                author_map['authors'][author_id] = CURRENT_AI_ID
                author_map['reverse'][CURRENT_AI_ID] = author_id
            
            # Convert expanded entry back to optimized
            optimized = migrate_v1_to_v2(entry, author_map)
            optimized_entries[str(eid)] = optimized
        
        # Save entries with author map
        data = {
            "v": VERSION,
            "authors": author_map['authors'],
            "entries": optimized_entries,
            "saved": datetime.now().isoformat(timespec='seconds')
        }
        
        temp_file = data_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
        temp_file.replace(data_file)
        
        # Save archive if exists
        if archive:
            archive_data = {
                "v": VERSION,
                "archive": archive[-10000:],
                "saved": datetime.now().isoformat(timespec='seconds')
            }
            archive_temp = archive_file.with_suffix('.tmp')
            with open(archive_temp, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, separators=(',', ':'), ensure_ascii=False)
            archive_temp.replace(archive_file)
        
        return True
    except Exception as e:
        logging.error(f"Failed to save project {project_name}: {e}")
        return False

def detect_type_and_priority(content: str) -> tuple:
    """Auto-detect entry type and priority from content"""
    content_lower = content.lower()
    
    # Detect type
    if any(marker in content_lower for marker in ['todo:', 'task:']):
        entry_type = "task"
    elif any(marker in content_lower for marker in ['decision:', 'decided:']):
        entry_type = "decision"
    else:
        entry_type = "note"
    
    # Detect priority (only for tasks)
    priority = None
    if entry_type == "task":
        if any(word in content_lower for word in ['urgent', 'asap', 'critical', 'important', 'high priority']):
            priority = "!"
        elif any(word in content_lower for word in ['low priority', 'whenever', 'maybe', 'someday']):
            priority = "↓"
    
    return entry_type, priority

def format_task_line(task: Dict) -> str:
    """Format a task for display"""
    tid = task['id']
    priority = task.get('pri', '')
    content = smart_truncate(task['content'], 60)
    
    if task.get('claimed_by'):
        claim_time = format_time_contextual(task.get('claimed_at', ''))
        comment_count = len(task.get('comments', []))
        comment_str = f" [{comment_count}c]" if comment_count else ""
        return f"[{tid}]{priority} {content} @{task['claimed_by']}({claim_time}){comment_str}"
    else:
        time_str = format_time_contextual(task['created'])
        return f"[{tid}]{priority} {content} @{time_str}"

def write(content: str = None, type: str = None, priority: str = None, project: str = None, **kwargs) -> Dict:
    """Share anything with the team"""
    try:
        if content is None:
            content = kwargs.get('content', '')
        if project is None:
            project = kwargs.get('project')
        
        content = str(content).strip()
        if not content:
            return {"error": "Need content to write"}
        
        # Load project data
        entries, archive, last_id, author_map = load_project_data(project)
        
        # Truncate if needed
        if len(content) > MAX_CONTENT_LENGTH:
            content = smart_truncate(content, MAX_CONTENT_LENGTH)
        
        # Auto-detect type and priority if not provided
        if type is None or priority is None:
            detected_type, detected_priority = detect_type_and_priority(content)
            if type is None:
                type = detected_type
            if priority is None and type == "task":
                priority = detected_priority
        
        # Generate entry
        entry_id = last_id + 1
        entry = {
            "id": entry_id,
            "content": content,
            "type": type,
            "author": CURRENT_AI_ID,
            "created": datetime.now().isoformat(timespec='seconds')
        }
        
        # Add priority if not normal
        if priority:
            entry["pri"] = priority
        
        # Add task fields if task
        if type == "task":
            entry["claimed_by"] = None
            entry["claimed_at"] = None
            entry["completed_at"] = None
        
        entries[entry_id] = entry
        save_project_data(entries, archive, entry_id, author_map, project)
        
        # Format response
        type_marker = ""
        if type == "task":
            type_marker = "TODO"
        elif type == "decision":
            type_marker = "DECISION"
        else:
            type_marker = "NOTE"
        
        priority_str = priority if priority else ""
        preview = smart_truncate(content, 80)
        
        return {"created": f"[{entry_id}]{priority_str} {type_marker}: {preview} (by {CURRENT_AI_ID})"}
        
    except Exception as e:
        logging.error(f"Error in write: {e}")
        return {"error": "Failed to write"}

def read(query: str = None, type: str = None, status: str = "pending", 
         claimed_by: str = None, project: str = None, **kwargs) -> Dict:
    """View team activity with smart filtering"""
    try:
        # Handle parameters
        if query is None:
            query = kwargs.get('query')
        if type is None:
            type = kwargs.get('type')
        if status is None:
            status = kwargs.get('status', 'pending')
        if claimed_by is None:
            claimed_by = kwargs.get('claimed_by')
        if project is None:
            project = kwargs.get('project')
        
        # Load project data
        entries, _, _, _ = load_project_data(project)
        
        # Filter entries
        filtered = []
        for eid, entry in entries.items():
            # Skip archived
            if entry.get('archived_at'):
                continue
            
            # Type filter
            if type and entry.get('type') != type:
                continue
            
            # Status filter (for tasks)
            if entry.get('type') == 'task':
                is_completed = bool(entry.get('completed_at'))
                if status == 'pending' and is_completed:
                    continue
                elif status == 'completed' and not is_completed:
                    continue
                # 'all' shows everything
            
            # Claimed filter (for tasks)
            if claimed_by is not None and entry.get('type') == 'task':
                if claimed_by == 'me' and entry.get('claimed_by') != CURRENT_AI_ID:
                    continue
                elif claimed_by == 'unclaimed' and entry.get('claimed_by'):
                    continue
                elif claimed_by not in ['me', 'unclaimed'] and entry.get('claimed_by') != claimed_by:
                    continue
            
            # Query filter
            if query and query.lower() not in entry.get('content', '').lower():
                continue
            
            filtered.append(entry)
        
        # Sort by creation time (newest first for notes, oldest first for tasks)
        if type == 'task':
            filtered.sort(key=lambda e: (
                0 if e.get('pri') == '!' else (2 if e.get('pri') == '↓' else 1),
                e.get('created', '')
            ))
        else:
            filtered.sort(key=lambda e: e.get('created', ''), reverse=True)
        
        # Build output
        lines = []
        shown = 0
        max_show = 20
        
        for entry in filtered:
            if shown >= max_show:
                lines.append(f"+{len(filtered)-shown} more")
                break
            
            # Format entry line
            eid = entry['id']
            content_preview = smart_truncate(entry['content'], 100)
            time_str = format_time_contextual(entry['created'])
            author = entry.get('author', 'Unknown')
            
            # Type-specific formatting
            if entry['type'] == 'task':
                priority = entry.get('pri', '')
                if entry.get('completed_at'):
                    duration = format_duration(entry.get('claimed_at', entry['created']), entry['completed_at'])
                    evidence = ""
                    if entry.get('evidence'):
                        evidence = f" - {smart_truncate(entry['evidence'], 40)}"
                    lines.append(f"[{eid}]✓ {content_preview}{evidence} @{time_str}({duration})")
                elif entry.get('claimed_by'):
                    claimer = entry['claimed_by']
                    claim_time = format_time_contextual(entry.get('claimed_at', ''))
                    comment_count = len(entry.get('comments', []))
                    comment_str = f" [{comment_count}c]" if comment_count else ""
                    lines.append(f"[{eid}]{priority} {content_preview} @{claimer}({claim_time}){comment_str}")
                else:
                    lines.append(f"[{eid}]{priority} {content_preview} @{time_str}")
            elif entry['type'] == 'decision':
                lines.append(f"[D{eid}] {content_preview} @{author} {time_str}")
            else:
                comment_count = len(entry.get('comments', []))
                comment_str = f" [{comment_count}c]" if comment_count else ""
                lines.append(f"[N{eid}] {content_preview} @{author} {time_str}{comment_str}")
            
            shown += 1
        
        if not lines:
            if type == 'task' and status == 'pending':
                return {"msg": "No pending tasks", "tip": "write('TODO: description')"}
            elif type == 'task' and status == 'completed':
                return {"msg": "No completed tasks"}
            else:
                return {"msg": "No entries found"}
        
        # Summary
        task_counts = {
            'pending': len([e for e in entries.values() if e.get('type') == 'task' and not e.get('completed_at') and not e.get('archived_at')]),
            'claimed': len([e for e in entries.values() if e.get('type') == 'task' and e.get('claimed_by') and not e.get('completed_at') and not e.get('archived_at')]),
            'completed': len([e for e in entries.values() if e.get('type') == 'task' and e.get('completed_at') and not e.get('archived_at')])
        }
        note_count = len([e for e in entries.values() if e.get('type') == 'note' and not e.get('archived_at')])
        decision_count = len([e for e in entries.values() if e.get('type') == 'decision' and not e.get('archived_at')])
        
        summary_parts = [f"You: {CURRENT_AI_ID}"]
        if task_counts['pending'] > 0:
            summary_parts.append(f"{task_counts['pending']} tasks ({task_counts['claimed']} claimed)")
        if note_count > 0:
            summary_parts.append(f"{note_count} notes")
        if decision_count > 0:
            summary_parts.append(f"{decision_count} decisions")
        
        _, _, _, _, project_name = get_project_paths(project)
        summary_parts.append(f"[{project_name}]")
        
        return {
            "summary": " | ".join(summary_parts) if summary_parts else "Empty",
            "entries": lines
        }
        
    except Exception as e:
        logging.error(f"Error in read: {e}")
        return {"error": "Failed to read"}

def get(id: int = None, project: str = None, **kwargs) -> Dict:
    """Retrieve full entry with all comments"""
    try:
        if id is None:
            id = kwargs.get('id')
        if project is None:
            project = kwargs.get('project')
        
        # Handle string IDs
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
            # Remove type prefixes if present
            if id.startswith('D') or id.startswith('N'):
                id = id[1:]
        
        try:
            id = int(id)
        except:
            return {"error": f"Invalid ID: '{id}'"}
        
        # Load project data
        entries, _, _, _ = load_project_data(project)
        
        if id not in entries:
            available = list(entries.keys())[-5:]
            return {
                "error": f"Entry [{id}] not found",
                "available": [f"[{eid}]" for eid in available] if available else ["No entries yet"]
            }
        
        entry = entries[id]
        
        # Build full output
        lines = []
        
        # Header
        type_str = entry['type'].upper()
        priority = entry.get('pri', '')
        time_str = format_time_contextual(entry['created'])
        author = entry.get('author', 'Unknown')
        
        if entry['type'] == 'task':
            if entry.get('completed_at'):
                lines.append(f"[{id}]✓ {type_str} by {author} @{time_str} (completed)")
            elif entry.get('claimed_by'):
                lines.append(f"[{id}]{priority} {type_str} by {author} @{time_str} (claimed by {entry['claimed_by']})")
            else:
                lines.append(f"[{id}]{priority} {type_str} by {author} @{time_str} (unclaimed)")
        else:
            lines.append(f"[{id}] {type_str} by {author} @{time_str}")
        
        lines.append("---")
        lines.append(entry['content'])
        
        # Evidence if completed
        if entry.get('evidence'):
            lines.append("---")
            lines.append(f"Evidence: {entry['evidence']}")
        
        # Comments
        comments = entry.get('comments', [])
        if comments:
            lines.append("---")
            lines.append(f"Comments ({len(comments)}):")
            for comment in comments:
                comment_author = comment.get('author', 'Unknown')
                comment_time = format_time_contextual(comment.get('created'))
                comment_text = comment.get('content', '')
                lines.append(f"  {comment_author}@{comment_time}: {comment_text}")
        
        return {"entry": lines}
        
    except Exception as e:
        logging.error(f"Error in get: {e}")
        return {"error": "Failed to get entry"}

def comment(id: int = None, content: str = None, project: str = None, **kwargs) -> Dict:
    """Add threaded comment to entry"""
    try:
        if id is None:
            id = kwargs.get('id')
        if content is None:
            content = kwargs.get('content', '')
        if project is None:
            project = kwargs.get('project')
        
        # Parse ID
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
            if id.startswith('D') or id.startswith('N'):
                id = id[1:]
        
        try:
            id = int(id)
        except:
            return {"error": f"Invalid ID: '{id}'"}
        
        content = str(content).strip()
        if not content:
            return {"error": "Need comment content"}
        
        if len(content) > MAX_COMMENT_LENGTH:
            content = smart_truncate(content, MAX_COMMENT_LENGTH)
        
        # Load project data
        entries, archive, last_id, author_map = load_project_data(project)
        
        if id not in entries:
            return {"error": f"Entry [{id}] not found"}
        
        entry = entries[id]
        
        # Add comment
        if 'comments' not in entry:
            entry['comments'] = []
        
        comment_data = {
            "author": CURRENT_AI_ID,
            "content": content,
            "created": datetime.now().isoformat(timespec='seconds')
        }
        
        entry['comments'].append(comment_data)
        save_project_data(entries, archive, last_id, author_map, project)
        
        preview = smart_truncate(content, 60)
        return {"commented": f"[{id}] +comment by {CURRENT_AI_ID}: {preview}"}
        
    except Exception as e:
        logging.error(f"Error in comment: {e}")
        return {"error": "Failed to add comment"}

def claim(id: int = None, project: str = None, **kwargs) -> Dict:
    """Atomically claim an unclaimed task"""
    try:
        if id is None:
            id = kwargs.get('id')
        if project is None:
            project = kwargs.get('project')
        
        # Parse ID
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
        
        try:
            id = int(id)
        except:
            return {"error": f"Invalid ID: '{id}'"}
        
        with lock:  # Atomic operation
            # Load project data inside lock
            entries, archive, last_id, author_map = load_project_data(project)
            
            if id not in entries:
                return {"error": f"Task [{id}] not found"}
            
            entry = entries[id]
            
            if entry.get('type') != 'task':
                return {"error": f"[{id}] is not a task"}
            
            if entry.get('claimed_by'):
                return {"error": f"[{id}] already claimed by {entry['claimed_by']}"}
            
            if entry.get('completed_at'):
                return {"error": f"[{id}] already completed"}
            
            if entry.get('archived_at'):
                return {"error": f"[{id}] is archived"}
            
            # Claim the task
            entry['claimed_by'] = CURRENT_AI_ID
            entry['claimed_at'] = datetime.now().isoformat(timespec='seconds')
            save_project_data(entries, archive, last_id, author_map, project)
            
            preview = smart_truncate(entry['content'], 60)
            return {"claimed": f"[{id}] by {CURRENT_AI_ID}: {preview}"}
        
    except Exception as e:
        logging.error(f"Error in claim: {e}")
        return {"error": "Failed to claim task"}

def complete(id: int = None, evidence: str = None, project: str = None, **kwargs) -> Dict:
    """Mark task complete with optional evidence"""
    try:
        if id is None:
            id = kwargs.get('id')
        if evidence is None:
            evidence = kwargs.get('evidence')
        if project is None:
            project = kwargs.get('project')
        
        # Parse ID
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
        
        try:
            id = int(id)
        except:
            return {"error": f"Invalid ID: '{id}'"}
        
        # Load project data
        entries, archive, last_id, author_map = load_project_data(project)
        
        if id not in entries:
            return {"error": f"Task [{id}] not found"}
        
        entry = entries[id]
        
        if entry.get('type') != 'task':
            return {"error": f"[{id}] is not a task"}
        
        if entry.get('completed_at'):
            return {"error": f"[{id}] already completed @{format_time_contextual(entry['completed_at'])}"}
        
        if entry.get('archived_at'):
            return {"error": f"[{id}] is archived"}
        
        # Complete the task
        now = datetime.now()
        entry['completed_at'] = now.isoformat(timespec='seconds')
        entry['completed_by'] = CURRENT_AI_ID
        
        if evidence:
            evidence = str(evidence).strip()
            if len(evidence) > MAX_EVIDENCE_LENGTH:
                evidence = smart_truncate(evidence, MAX_EVIDENCE_LENGTH)
            entry['evidence'] = evidence
        
        # Calculate duration
        start_time = entry.get('claimed_at', entry['created'])
        duration = format_duration(start_time, now.isoformat())
        
        save_project_data(entries, archive, last_id, author_map, project)
        
        msg = f"[{id}]✓ by {CURRENT_AI_ID} in {duration}"
        if evidence:
            msg += f" - {smart_truncate(evidence, 50)}"
        
        return {"completed": msg}
        
    except Exception as e:
        logging.error(f"Error in complete: {e}")
        return {"error": "Failed to complete task"}

def update(id: int = None, content: str = None, type: str = None, 
           priority: str = None, project: str = None, **kwargs) -> Dict:
    """Update an existing entry"""
    try:
        if id is None:
            id = kwargs.get('id')
        if content is None:
            content = kwargs.get('content')
        if type is None:
            type = kwargs.get('type')
        if priority is None:
            priority = kwargs.get('priority')
        if project is None:
            project = kwargs.get('project')
        
        # Parse ID
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
            if id.startswith('D') or id.startswith('N'):
                id = id[1:]
        
        try:
            id = int(id)
        except:
            return {"error": f"Invalid ID: '{id}'"}
        
        # Load project data
        entries, archive, last_id, author_map = load_project_data(project)
        
        if id not in entries:
            return {"error": f"Entry [{id}] not found"}
        
        entry = entries[id]
        
        if entry.get('archived_at'):
            return {"error": f"[{id}] is archived - cannot update"}
        
        # Track what changed
        changes = []
        
        # Update content
        if content is not None:
            content = str(content).strip()
            if content and content != entry.get('content'):
                if len(content) > MAX_CONTENT_LENGTH:
                    content = smart_truncate(content, MAX_CONTENT_LENGTH)
                entry['content'] = content
                changes.append("content")
        
        # Update type
        if type is not None and type != entry.get('type'):
            entry['type'] = type
            changes.append("type")
        
        # Update priority (only for tasks)
        if priority is not None and entry.get('type') == 'task':
            if priority == 'normal' or priority == '':
                if 'pri' in entry:
                    del entry['pri']
                    changes.append("priority")
            elif priority != entry.get('pri'):
                entry['pri'] = priority
                changes.append("priority")
        
        if changes:
            entry['updated_at'] = datetime.now().isoformat(timespec='seconds')
            entry['updated_by'] = CURRENT_AI_ID
            save_project_data(entries, archive, last_id, author_map, project)
            
            return {"updated": f"[{id}] changed by {CURRENT_AI_ID}: {', '.join(changes)}"}
        else:
            return {"msg": f"[{id}] no changes made"}
        
    except Exception as e:
        logging.error(f"Error in update: {e}")
        return {"error": "Failed to update entry"}

def archive(id: int = None, reason: str = None, project: str = None, **kwargs) -> Dict:
    """Archive an entry (safe removal)"""
    try:
        if id is None:
            id = kwargs.get('id')
        if reason is None:
            reason = kwargs.get('reason')
        if project is None:
            project = kwargs.get('project')
        
        # Parse ID
        if isinstance(id, str):
            id = id.strip().strip('[]').strip()
            if id.startswith('D') or id.startswith('N'):
                id = id[1:]
        
        try:
            id = int(id)
        except:
            return {"error": f"Invalid ID: '{id}'"}
        
        # Load project data
        entries, archive_list, last_id, author_map = load_project_data(project)
        
        if id not in entries:
            return {"error": f"Entry [{id}] not found"}
        
        entry = entries[id]
        
        if entry.get('archived_at'):
            return {"error": f"[{id}] already archived"}
        
        # Archive the entry
        now = datetime.now()
        entry['archived_at'] = now.isoformat(timespec='seconds')
        entry['archived_by'] = CURRENT_AI_ID
        
        if reason:
            reason = str(reason).strip()
            if len(reason) > 200:
                reason = smart_truncate(reason, 200)
            entry['archive_reason'] = reason
        
        # Add to archive list
        archive_entry = {
            "id": id,
            "type": entry.get('type'),
            "content": smart_truncate(entry.get('content', ''), 100),
            "archived_at": now.isoformat(timespec='seconds'),
            "archived_by": CURRENT_AI_ID,
            "reason": reason
        }
        archive_list.append(archive_entry)
        
        save_project_data(entries, archive_list, last_id, author_map, project)
        
        msg = f"[{id}] archived by {CURRENT_AI_ID}"
        if reason:
            msg += f" - {reason}"
        
        return {"archived": msg}
        
    except Exception as e:
        logging.error(f"Error in archive: {e}")
        return {"error": "Failed to archive entry"}

def status(project: str = None, **kwargs) -> Dict:
    """Ultra-compact team pulse"""
    try:
        if project is None:
            project = kwargs.get('project')
        
        # Load project data
        entries, _, _, _ = load_project_data(project)
        
        # Count active entries
        active_entries = [e for e in entries.values() if not e.get('archived_at')]
        
        tasks_pending = [e for e in active_entries if e.get('type') == 'task' and not e.get('completed_at')]
        tasks_claimed = [e for e in tasks_pending if e.get('claimed_by')]
        tasks_completed_today = [e for e in active_entries if e.get('type') == 'task' and e.get('completed_at', '')[:10] == datetime.now().date().isoformat()]
        
        notes = [e for e in active_entries if e.get('type') == 'note']
        decisions = [e for e in active_entries if e.get('type') == 'decision']
        
        # Find last activity
        last_activity = None
        for e in active_entries:
            created = e.get('created')
            if created and (not last_activity or created > last_activity):
                last_activity = created
        
        last_time = format_time_contextual(last_activity) if last_activity else "never"
        
        # Build summary line
        team_count = len(set(e.get('author', 'Unknown') for e in active_entries))
        summary_parts = [f"Team: {team_count} active"]
        summary_parts.append(f"You: {CURRENT_AI_ID}")
        
        if tasks_pending:
            summary_parts.append(f"{len(tasks_pending)} tasks ({len(tasks_claimed)} claimed)")
        if notes:
            summary_parts.append(f"{len(notes)} notes")
        if decisions:
            summary_parts.append(f"{len(decisions)} decisions")
        
        summary_parts.append(f"last: {last_time}")
        
        _, _, _, _, project_name = get_project_paths(project)
        summary_parts.append(f"[{project_name}]")
        
        # Show top pending tasks
        lines = []
        shown = 0
        
        # High priority tasks first
        high_pri = [t for t in tasks_pending if t.get('pri') == '!']
        for task in high_pri[:3]:
            lines.append(format_task_line(task))
            shown += 1
        
        # Regular tasks
        normal = [t for t in tasks_pending if not t.get('pri')]
        for task in normal[:min(3, 5-shown)]:
            lines.append(format_task_line(task))
            shown += 1
        
        # Low priority
        low_pri = [t for t in tasks_pending if t.get('pri') == '↓']
        for task in low_pri[:min(2, 5-shown)]:
            lines.append(format_task_line(task))
            shown += 1
        
        # Recent decisions
        recent_decisions = sorted(decisions, key=lambda d: d.get('created', ''), reverse=True)[:2]
        for decision in recent_decisions:
            did = decision['id']
            content = smart_truncate(decision['content'], 60)
            time_str = format_time_contextual(decision['created'])
            lines.append(f"[D{did}] {content} @{time_str}")
        
        result = {
            "summary": " | ".join(summary_parts),
        }
        
        if lines:
            result["highlights"] = lines
        
        if tasks_completed_today:
            result["today"] = f"{len(tasks_completed_today)} completed today"
        
        return result
        
    except Exception as e:
        logging.error(f"Error in status: {e}")
        return {"summary": "Status unavailable"}

def projects(**kwargs) -> Dict:
    """List available teambook projects"""
    try:
        # Find all teambook directories
        project_dirs = []
        for path in BASE_DIR.glob("teambook_*_data"):
            if path.is_dir():
                project_name = path.name.replace("teambook_", "").replace("_data", "")
                
                # Get some stats about the project
                try:
                    teambook_file = path / "teambook.json"
                    if teambook_file.exists():
                        with open(teambook_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            entry_count = len(data.get("entries", {}))
                            last_saved = data.get("saved", "")
                            last_activity = format_time_contextual(last_saved) if last_saved else "unknown"
                            
                            # Mark default project
                            default_marker = " [DEFAULT]" if project_name == DEFAULT_PROJECT else ""
                            project_dirs.append(f"{project_name}{default_marker}: {entry_count} entries, last: {last_activity}")
                    else:
                        default_marker = " [DEFAULT]" if project_name == DEFAULT_PROJECT else ""
                        project_dirs.append(f"{project_name}{default_marker}: empty")
                except:
                    project_dirs.append(f"{project_name}: unknown state")
        
        if not project_dirs:
            return {
                "msg": f"No projects found. Default: '{DEFAULT_PROJECT}'",
                "tip": "Projects are created automatically when you write to them"
            }
        
        return {
            "msg": f"Available projects (default: '{DEFAULT_PROJECT}'):",
            "projects": project_dirs,
            "tip": "Use project='name' parameter or set TEAMBOOK_PROJECT env var"
        }
        
    except Exception as e:
        logging.error(f"Error listing projects: {e}")
        return {"error": "Failed to list projects"}

# Tool handler for MCP protocol
def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls with clean output"""
    
    tool_name = params.get("name", "")
    tool_args = params.get("arguments", {})
    
    # Map to functions
    tool_map = {
        "write": write,
        "read": read,
        "get": get,
        "comment": comment,
        "claim": claim,
        "complete": complete,
        "update": update,
        "archive": archive,
        "status": status,
        "projects": projects
    }
    
    func = tool_map.get(tool_name)
    
    if func:
        result = func(**tool_args)
    else:
        result = {"error": f"Unknown tool: {tool_name}", 
                 "available": list(tool_map.keys())}
    
    # Format response
    text_parts = []
    
    # Primary message
    for key in ["created", "claimed", "completed", "commented", "updated", "archived", "summary", "msg"]:
        if key in result:
            text_parts.append(result[key])
            break
    
    # Projects or entries
    if "projects" in result:
        text_parts.extend(result["projects"])
    elif "entries" in result:
        text_parts.extend(result["entries"])
    elif "entry" in result:
        text_parts.extend(result["entry"])
    elif "highlights" in result:
        text_parts.extend(result["highlights"])
    
    # Additional info
    if "stats" in result:
        text_parts.append(result["stats"])
    if "today" in result:
        text_parts.append(result["today"])
    if "note" in result:
        text_parts.append(result["note"])
    
    # Error handling
    if "error" in result:
        text_parts.append(f"Error: {result['error']}")
        if "available" in result:
            text_parts.append("Available: " + ", ".join(result["available"]))
    
    # Tips
    if "tip" in result:
        text_parts.append(f"Tip: {result['tip']}")
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Ready"
        }]
    }

# Main server loop
def main():
    """MCP server - handles JSON-RPC for team coordination"""
    
    logging.info(f"TEAMBOOK MCP v{VERSION} starting (optimized)...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Default project: '{DEFAULT_PROJECT}'")
    
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
                        "name": "teambook",
                        "version": VERSION,
                        "description": "Optimized team coordination with persistent identity"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "write",
                            "description": "Share anything with team (auto-detects tasks/decisions)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "What to share (TODO: for tasks, DECISION: for decisions)"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Optional: task, note, or decision (auto-detected if omitted)"
                                    },
                                    "priority": {
                                        "type": "string",
                                        "description": "Optional: ! for high, ↓ for low (auto-detected if omitted)"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["content"]
                            }
                        },
                        {
                            "name": "read",
                            "description": "View team activity with smart filtering",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search term (optional)"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Filter by type: task, note, decision"
                                    },
                                    "status": {
                                        "type": "string",
                                        "description": "For tasks: pending (default), completed, all"
                                    },
                                    "claimed_by": {
                                        "type": "string",
                                        "description": "Filter tasks: me, unclaimed, or AI-ID"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                }
                            }
                        },
                        {
                            "name": "get",
                            "description": "Get full entry with all comments",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Entry ID to retrieve"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "comment",
                            "description": "Add comment to any entry",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Entry ID to comment on"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "Comment text"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id", "content"]
                            }
                        },
                        {
                            "name": "claim",
                            "description": "Claim an unclaimed task",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Task ID to claim"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "complete",
                            "description": "Complete a task with optional evidence",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Task ID to complete"
                                    },
                                    "evidence": {
                                        "type": "string",
                                        "description": "Optional completion evidence/notes"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "update",
                            "description": "Update entry content, type, or priority",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Entry ID to update"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "New content (optional)"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "New type: task, note, decision (optional)"
                                    },
                                    "priority": {
                                        "type": "string",
                                        "description": "New priority: !, ↓, or normal (optional)"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "archive",
                            "description": "Archive entry (safe removal)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Entry ID to archive"
                                    },
                                    "reason": {
                                        "type": "string",
                                        "description": "Archive reason (optional)"
                                    },
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                },
                                "required": ["id"]
                            }
                        },
                        {
                            "name": "status",
                            "description": "Get team pulse - compact overview",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "project": {
                                        "type": "string",
                                        "description": "Optional: project name (uses default if omitted)"
                                    }
                                }
                            }
                        },
                        {
                            "name": "projects",
                            "description": "List available teambook projects",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
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
    
    logging.info("TEAMBOOK MCP shutting down")

if __name__ == "__main__":
    main()
