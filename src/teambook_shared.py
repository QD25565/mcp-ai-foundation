#!/usr/bin/env python3
"""
TEAMBOOK SHARED v7.0.0 - SHARED UTILITIES AND CONSTANTS
========================================================
Core utilities, constants, and shared state for the teambook collaborative tool.
This is the foundation layer with no dependencies on other teambook modules.

Built by AIs, for AIs.
========================================================
"""

import os
import sys
import re
import json
import random
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple, List

# Import from shared MCP utilities
from mcp_shared import (
    BASE_DATA_DIR, CURRENT_AI_ID as MCP_AI_ID,
    pipe_escape, format_time_compact, get_tool_data_dir,
    normalize_param
)

# ============= VERSION AND CONFIGURATION =============
VERSION = "7.0.0"
OUTPUT_FORMAT = os.environ.get('TEAMBOOK_FORMAT', 'pipe')
USE_SEMANTIC = os.environ.get('TEAMBOOK_SEMANTIC', 'true').lower() == 'true'

# ============= LIMITS AND CONSTANTS =============
MAX_CONTENT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 200
MAX_RESULTS = 100
BATCH_MAX = 50
DEFAULT_RECENT = 30

# Edge and PageRank settings
TEMPORAL_EDGES = 3
SESSION_GAP_MINUTES = 30
PAGERANK_ITERATIONS = 20
PAGERANK_DAMPING = 0.85
PAGERANK_CACHE_SECONDS = 300
ATTEMPT_CLEANUP_HOURS = 24

# ============= GLOBAL STATE =============
CURRENT_TEAMBOOK = None
CURRENT_AI_ID = MCP_AI_ID  # Use shared AI identity
LAST_OPERATION = None

# Knowledge bases
KNOWN_ENTITIES = set()
KNOWN_TOOLS = {
    'teambook', 'firebase', 'gemini', 'claude', 'jetbrains', 'github',
    'slack', 'discord', 'vscode', 'git', 'docker', 'python', 'node',
    'react', 'vue', 'angular', 'tensorflow', 'pytorch', 'aws', 'gcp',
    'azure', 'kubernetes', 'redis', 'postgres', 'mongodb', 'sqlite',
    'task_manager', 'notebook', 'world', 'chromadb', 'duckdb'
}

# Pattern caching
ENTITY_PATTERN = None
ENTITY_PATTERN_SIZE = 0
PAGERANK_DIRTY = True
PAGERANK_CACHE_TIME = 0

# ============= CROSS-PLATFORM DIRECTORY STRUCTURE =============
TEAMBOOK_ROOT = BASE_DATA_DIR / "teambook_data"
TEAMBOOK_PRIVATE_ROOT = TEAMBOOK_ROOT / "_private"

# Create root directories
TEAMBOOK_ROOT.mkdir(parents=True, exist_ok=True)
TEAMBOOK_PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)

# ============= PATH MANAGEMENT =============
def get_data_dir():
    """Get current data directory based on teambook context"""
    if CURRENT_TEAMBOOK:
        team_dir = TEAMBOOK_ROOT / CURRENT_TEAMBOOK
        team_dir.mkdir(parents=True, exist_ok=True)
        return team_dir
    return TEAMBOOK_PRIVATE_ROOT

def get_db_file():
    """Get current database file path"""
    return get_data_dir() / "teambook.duckdb"

def get_outputs_dir():
    """Get outputs directory for evolution results"""
    outputs = get_data_dir() / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    return outputs

def get_vault_key_file():
    """Get vault key file path"""
    return get_data_dir() / ".vault_key"

def get_last_op_file():
    """Get last operation file path"""
    return get_data_dir() / ".last_operation"

def get_vector_dir():
    """Get vector database directory"""
    return get_data_dir() / "vectors"

# ============= TEXT UTILITIES =============
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
    
    # Try to break at sentence boundaries
    for sep in ['. ', '! ', '? ', '; ']:
        idx = clean.rfind(sep, 0, max_len)
        if idx > max_len * 0.5:
            return clean[:idx + 1]
    
    # Fall back to word boundary
    idx = clean.rfind(' ', 0, max_len - 3)
    if idx == -1 or idx < max_len * 0.7:
        idx = max_len - 3
    return clean[:idx] + "..."

# ============= TIME UTILITIES =============
def parse_time_query(when: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse natural language time queries"""
    if not when:
        return None, None
    
    when_lower = when.lower().strip()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Common time queries
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

# ============= CONTENT ANALYSIS =============
def extract_references(content: str) -> List[int]:
    """Extract note references from content"""
    refs = set()
    patterns = [
        r'note\s+(\d+)',
        r'\bn(\d+)\b',
        r'#(\d+)\b',
        r'\[(\d+)\]'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        refs.update(int(m) for m in matches if m.isdigit())
    
    return list(refs)

def extract_entities(content: str) -> List[Tuple[str, str]]:
    """Extract entities from content"""
    global ENTITY_PATTERN, ENTITY_PATTERN_SIZE
    entities = []
    content_lower = content.lower()
    
    # Extract mentions
    mentions = re.findall(r'@([\w-]+)', content, re.IGNORECASE)
    entities.extend((m.lower(), 'mention') for m in mentions)
    
    # Extract known entities
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

# ============= OPERATION TRACKING =============
def save_last_operation(op_type: str, result: Any):
    """Save last operation for chaining"""
    global LAST_OPERATION
    LAST_OPERATION = {
        'type': op_type,
        'result': result,
        'time': datetime.now(timezone.utc)
    }
    
    try:
        with open(get_last_op_file(), 'w') as f:
            json.dump({
                'type': op_type,
                'time': LAST_OPERATION['time'].isoformat()
            }, f)
    except:
        pass

def get_last_operation() -> Optional[Dict]:
    """Get last operation for context"""
    global LAST_OPERATION
    if LAST_OPERATION:
        return LAST_OPERATION
    
    try:
        last_op_file = get_last_op_file()
        if last_op_file.exists():
            with open(last_op_file, 'r') as f:
                data = json.load(f)
                return {
                    'type': data['type'],
                    'time': datetime.fromisoformat(data['time'])
                }
    except:
        pass
    
    return None

def get_note_id(id_param: Any) -> Optional[int]:
    """Resolve 'last' or string IDs to integer"""
    if id_param == "last":
        last_op = get_last_operation()
        if last_op and last_op['type'] in ['remember', 'write']:
            return last_op['result'].get('id')
        return None
    
    if isinstance(id_param, str):
        clean_id = re.sub(r'[^\d]', '', id_param)
        return int(clean_id) if clean_id else None
    
    return int(id_param) if id_param is not None else None
