#!/usr/bin/env python3
"""
NOTEBOOK MCP v6.2.0 - SHARED UTILITIES
======================================
Constants, configuration, and utility functions for the Notebook MCP tool.
No database dependencies - pure utilities.

v6.2.0 Changes:
- Refactored into three-file structure
- Added directory tracking for navigation clarity
- Fixed pinned_only bug
======================================
"""

import os
import re
import sys
import json
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

# Version
VERSION = "6.2.0"

# Configuration
OUTPUT_FORMAT = os.environ.get('NOTEBOOK_FORMAT', 'pipe')
USE_SEMANTIC = os.environ.get('NOTEBOOK_SEMANTIC', 'true').lower() == 'true'

# Limits
MAX_CONTENT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 200
MAX_RESULTS = 100
BATCH_MAX = 50
DEFAULT_RECENT = 30
TEMPORAL_EDGES = 3
SESSION_GAP_MINUTES = 30
PAGERANK_ITERATIONS = 20
PAGERANK_DAMPING = 0.85
PAGERANK_CACHE_SECONDS = 300
MAX_RECENT_DIRS = 10  # Track last 10 directories

# Storage paths
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "notebook_data"
if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
    DATA_DIR = Path(os.environ.get('TEMP', '/tmp')) / "notebook_data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "notebook.duckdb"
SQLITE_DB_FILE = DATA_DIR / "notebook.db"
VECTOR_DIR = DATA_DIR / "vectors"
VAULT_KEY_FILE = DATA_DIR / ".vault_key"
LAST_OP_FILE = DATA_DIR / ".last_operation"
RECENT_DIRS_FILE = DATA_DIR / ".recent_directories"

# Logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Global State (will be modified by storage module)
KNOWN_ENTITIES = set()
KNOWN_TOOLS = {'teambook', 'firebase', 'gemini', 'claude', 'jetbrains', 'github',
                'slack', 'discord', 'vscode', 'git', 'docker', 'python', 'node',
                'react', 'vue', 'angular', 'tensorflow', 'pytorch', 'aws', 'gcp',
                'azure', 'kubernetes', 'redis', 'postgres', 'mongodb', 'sqlite',
                'task_manager', 'notebook', 'world', 'chromadb', 'duckdb'}
ENTITY_PATTERN = None
ENTITY_PATTERN_SIZE = 0
PAGERANK_DIRTY = True
PAGERANK_CACHE_TIME = 0
LAST_OPERATION = None

# Directory tracking
RECENT_DIRECTORIES = deque(maxlen=MAX_RECENT_DIRS)

def load_recent_directories():
    """Load recent directories from file"""
    global RECENT_DIRECTORIES
    try:
        if RECENT_DIRS_FILE.exists():
            with open(RECENT_DIRS_FILE, 'r') as f:
                dirs = json.load(f)
                RECENT_DIRECTORIES = deque(dirs, maxlen=MAX_RECENT_DIRS)
    except Exception as e:
        logging.debug(f"Could not load recent directories: {e}")
        RECENT_DIRECTORIES = deque(maxlen=MAX_RECENT_DIRS)

def save_recent_directories():
    """Save recent directories to file"""
    try:
        with open(RECENT_DIRS_FILE, 'w') as f:
            json.dump(list(RECENT_DIRECTORIES), f)
    except Exception as e:
        logging.debug(f"Could not save recent directories: {e}")

def track_directory(path: str):
    """Track a directory access for navigation clarity"""
    global RECENT_DIRECTORIES
    
    # Normalize the path
    normalized = str(Path(path).resolve())
    
    # Remove if already exists (to move to end)
    if normalized in RECENT_DIRECTORIES:
        RECENT_DIRECTORIES.remove(normalized)
    
    # Add to end (most recent)
    RECENT_DIRECTORIES.append(normalized)
    
    # Save to file
    save_recent_directories()

def get_recent_directories(limit: int = 5) -> List[str]:
    """Get most recent directories accessed"""
    return list(RECENT_DIRECTORIES)[-limit:]

def format_directory_trail() -> str:
    """Format recent directories for display"""
    dirs = get_recent_directories(5)
    if not dirs:
        return "No recent directories"
    
    if OUTPUT_FORMAT == 'pipe':
        return '|'.join([Path(d).name for d in dirs])
    else:
        return ' → '.join([Path(d).name for d in dirs])

def get_persistent_id():
    """Get or create persistent AI identity"""
    for loc in [Path(__file__).parent, DATA_DIR, Path.home()]:
        id_file = loc / "ai_identity.txt"
        if id_file.exists():
            try:
                with open(id_file, 'r') as f:
                    stored_id = f.read().strip()
                    if stored_id: 
                        return stored_id
            except: 
                pass
    
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep', 'Keen', 'Pure']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node', 'Wave', 'Link']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    try:
        id_file = Path(__file__).parent / "ai_identity.txt"
        with open(id_file, 'w') as f: 
            f.write(new_id)
    except: 
        pass
    
    return new_id

CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

def save_last_operation(op_type: str, result: Any):
    """Save last operation for chaining"""
    global LAST_OPERATION
    LAST_OPERATION = {'type': op_type, 'result': result, 'time': datetime.now()}
    try:
        with open(LAST_OP_FILE, 'w') as f:
            json.dump({'type': op_type, 'time': LAST_OPERATION['time'].isoformat()}, f)
    except: 
        pass

def get_last_operation() -> Optional[Dict]:
    """Get last operation for context"""
    global LAST_OPERATION
    if LAST_OPERATION:
        return LAST_OPERATION
    try:
        if LAST_OP_FILE.exists():
            with open(LAST_OP_FILE, 'r') as f:
                data = json.load(f)
                return {'type': data['type'], 'time': datetime.fromisoformat(data['time'])}
    except:
        pass
    return None

def pipe_escape(text: str) -> str:
    """Escape pipes in text for pipe format"""
    return str(text).replace('|', '\\|')

def format_time_compact(ts: Any) -> str:
    """Compact time format - YYYYMMDD|HHMM or just HHMM for today"""
    if not ts: 
        return "unknown"
    try:
        # Handle if ts is already a datetime object
        if isinstance(ts, datetime):
            dt = ts
        elif isinstance(ts, str):
            # Try parsing as ISO format
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00').replace(' ', 'T'))
        else:
            # Try converting to string first
            dt = datetime.fromisoformat(str(ts))
        
        now = datetime.now()
        delta = now - dt
        
        if delta.total_seconds() < 60: 
            return "now"
        if delta.total_seconds() < 3600: 
            return f"{int(delta.total_seconds()/60)}m"
        if dt.date() == now.date():
            # Today - just show time
            return dt.strftime("%H%M")
        if delta.days == 1: 
            return f"y{dt.strftime('%H%M')}"
        if delta.days < 7: 
            return f"{delta.days}d"
        # Older - show full date|time
        return dt.strftime("%Y%m%d|%H%M")
    except Exception as e:
        # Log for debugging but return something useful
        logging.debug(f"Timestamp parsing error for {ts}: {e}")
        return str(ts)[:10] if ts else "unknown"

def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace"""
    return re.sub(r'\s+', ' ', text).strip() if text else ""

def simple_summary(content: str, max_len: int = 150) -> str:
    """Create simple summary by truncating cleanly"""
    if not content: 
        return ""
    clean = clean_text(content)
    if len(clean) <= max_len: 
        return clean
    for sep in ['. ', '! ', '? ', '; ']:
        idx = clean.rfind(sep, 0, max_len)
        if idx > max_len * 0.5: 
            return clean[:idx + 1]
    idx = clean.rfind(' ', 0, max_len - 3)
    if idx == -1 or idx < max_len * 0.7: 
        idx = max_len - 3
    return clean[:idx] + "..."

def extract_references(content: str) -> List[int]:
    """Extract note references from content"""
    refs = set()
    for pattern in [r'note\s+(\d+)', r'\bn(\d+)\b', r'#(\d+)\b', r'\[(\d+)\]']:
        refs.update(int(m) for m in re.findall(pattern, content, re.IGNORECASE) if m.isdigit())
    return list(refs)

def extract_entities(content: str) -> List[Tuple[str, str]]:
    """Extract entities from content"""
    global ENTITY_PATTERN, ENTITY_PATTERN_SIZE
    entities = []
    content_lower = content.lower()
    
    mentions = re.findall(r'@([\w-]+)', content, re.IGNORECASE)
    entities.extend((m.lower(), 'mention') for m in mentions)
    
    all_known = KNOWN_TOOLS.union(KNOWN_ENTITIES)
    if all_known:
        if ENTITY_PATTERN is None or len(all_known) != ENTITY_PATTERN_SIZE:
            pattern_str = r'\b(' + '|'.join(re.escape(e) for e in all_known) + r')\b'
            ENTITY_PATTERN = re.compile(pattern_str, re.IGNORECASE)
            ENTITY_PATTERN_SIZE = len(all_known)
        
        if ENTITY_PATTERN:
            for entity_name in set(ENTITY_PATTERN.findall(content_lower)):
                entity_type = 'tool' if entity_name in KNOWN_TOOLS else 'known'
                entities.append((entity_name, entity_type))
    
    return entities

def parse_time_query(when: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse natural language time queries"""
    if not when:
        return None, None
    
    when_lower = when.lower().strip()
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if when_lower == "today":
        return today_start, now
    elif when_lower == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        return yesterday_start, today_start - timedelta(seconds=1)
    elif when_lower in ["this week", "week"]:
        week_start = today_start - timedelta(days=now.weekday())
        return week_start, now
    elif when_lower == "last week":
        week_start = today_start - timedelta(days=now.weekday())
        last_week_start = week_start - timedelta(days=7)
        return last_week_start, week_start
    
    return None, None

def get_note_id(id_param: Any) -> Optional[int]:
    """Resolve 'last' or string IDs to integer"""
    if id_param == "last":
        last_op = get_last_operation()
        if last_op and last_op['type'] == 'remember':
            return last_op['result'].get('id')
        # Will need to query DB in main module
        return None
    
    if isinstance(id_param, str):
        clean_id = re.sub(r'[^\d]', '', id_param)
        return int(clean_id) if clean_id else None
    
    return int(id_param) if id_param is not None else None

# Load recent directories on module import
load_recent_directories()
