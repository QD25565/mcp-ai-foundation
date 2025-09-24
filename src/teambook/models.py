#!/usr/bin/env python3
"""
Teambook v6.0 Data Models
=========================
Core data structures for entries, notes, links, DMs, and shares.
Immutable, token-efficient, self-documenting.
"""

import json
import random
import string
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


def generate_id(prefix: str = "tb") -> str:
    """Generate time-sortable unique ID
    Format: prefix_YYYYMMDD_HHMMSS_random
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{timestamp}_{random_suffix}"


@dataclass
class Entry:
    """Core entry model - immutable once created"""
    
    # Required fields
    id: str
    content: str
    type: str  # task|note|decision|message|dm|share
    author: str
    created: str  # ISO format
    
    # Optional fields
    signature: Optional[str] = None
    meta: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    # Task state (only for type='task')
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    done_at: Optional[str] = None
    result: Optional[str] = None
    
    # Relations (populated from other tables)
    notes: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Entry':
        """Create Entry from dictionary"""
        # Parse meta if it's a string
        if isinstance(data.get('meta'), str):
            try:
                data['meta'] = json.loads(data['meta'])
            except:
                data['meta'] = {}
        
        # Parse notes/links if strings
        if isinstance(data.get('notes'), str):
            try:
                data['notes'] = json.loads(data['notes'])
            except:
                data['notes'] = []
                
        if isinstance(data.get('links'), str):
            try:
                data['links'] = json.loads(data['links'])
            except:
                data['links'] = []
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        # Just return the raw data - database layer will handle JSON serialization
        return asdict(self)
    
    def format_compact(self) -> str:
        """Token-efficient string representation"""
        parts = [self.id, self.type.title()]
        
        # Truncate content if needed
        content = self.content[:50]
        if len(self.content) > 50:
            content += "..."
        parts.append(content)
        
        # Add state for tasks
        if self.type == "task":
            if self.done_at:
                parts.append("done")
                if self.result:
                    parts.append(self.result[:30])
            elif self.claimed_by:
                parts.append("claimed")
                parts.append(f"@{self.claimed_by}")
            else:
                parts.append("pending")
        
        # Add time
        parts.append(format_time_compact(self.created))
        
        # Add author if not current AI
        from .config import CURRENT_AI_ID
        if self.author != CURRENT_AI_ID:
            parts.append(f"@{self.author}")
        
        return " ".join(parts)


@dataclass
class Note:
    """Note/annotation on an entry"""
    id: str
    entry_id: str
    content: str
    type: str  # comment|annotation|update
    author: str
    created: str
    signature: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Note':
        """Create Note from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def format_compact(self) -> str:
        """Token-efficient string representation"""
        content = self.content[:80]
        if len(self.content) > 80:
            content += "..."
        return f"{self.id} on {self.entry_id} {content} {format_time_compact(self.created)}"


@dataclass
class Link:
    """Relationship between entries"""
    from_id: str
    to_id: str
    rel: str  # related|blocks|requires|references
    created: str
    created_by: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Link':
        """Create Link from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DM:
    """Direct message between AIs"""
    id: str
    from_ai: str
    to_ai: str
    msg: str
    created: str
    signature: Optional[str] = None
    meta: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DM':
        """Create DM from dictionary"""
        if isinstance(data.get('meta'), str):
            try:
                data['meta'] = json.loads(data['meta'])
            except:
                data['meta'] = {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def format_compact(self) -> str:
        """Token-efficient string representation"""
        msg = self.msg[:50]
        if len(self.msg) > 50:
            msg += "..."
        return f"{self.id} {self.from_ai} > {self.to_ai} {msg}"


@dataclass
class Share:
    """Shared content (code/data/config/doc)"""
    id: str
    from_ai: str
    to_ai: Optional[str]  # None means broadcast
    content: str
    type: str  # code|data|config|doc
    created: str
    signature: Optional[str] = None
    meta: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Share':
        """Create Share from dictionary"""
        if isinstance(data.get('meta'), str):
            try:
                data['meta'] = json.loads(data['meta'])
            except:
                data['meta'] = {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def format_compact(self) -> str:
        """Token-efficient string representation"""
        recipient = self.to_ai or "*"
        # For code/data, show filename if in meta
        label = self.meta.get('filename', self.type) if self.meta else self.type
        return f"{self.id} {self.type} {label} to {recipient} {format_time_compact(self.created)}"


class EntryType:
    """Entry type constants and detection"""
    TASK = "task"
    NOTE = "note"
    DECISION = "decision"
    MESSAGE = "message"
    DM = "dm"
    SHARE = "share"
    
    # Detection patterns
    PATTERNS = {
        TASK: ["TODO:", "TASK:", "[ ]", "FIX:", "IMPLEMENT:", "BUILD:", "CREATE:"],
        DECISION: ["DECIDED:", "DECISION:", "RESOLVED:", "AGREED:"],
        MESSAGE: ["@", "MESSAGE:", "MSG:"],
        NOTE: ["NOTE:", "INFO:", "UPDATE:", "FYI:"],
    }
    
    @classmethod
    def detect(cls, content: str) -> str:
        """Auto-detect type from content"""
        content_upper = content.upper()
        
        # Check patterns
        for entry_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if pattern in content_upper:
                    return entry_type
        
        # Default to note
        return cls.NOTE


def format_time_compact(timestamp: str) -> str:
    """Ultra-compact contextual time format
    now, 5m, 3h, 14:30, y14:30, 3d, 12/25, 2024/12/25
    """
    if not timestamp:
        return ""
    
    try:
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp
            
        now = datetime.now()
        delta = now - dt
        
        if delta.total_seconds() < 60:
            return "now"
        elif delta.total_seconds() < 3600:
            return f"{int(delta.total_seconds()/60)}m"
        elif delta.total_seconds() < 86400:
            if dt.date() == now.date():
                return dt.strftime("%H:%M")
            else:
                return f"y{dt.strftime('%H:%M')}"
        elif delta.days < 7:
            return f"{delta.days}d"
        elif dt.year == now.year:
            return dt.strftime("%m/%d")
        else:
            return dt.strftime("%Y/%m/%d")
    except:
        return ""


def smart_truncate(text: str, max_length: int) -> str:
    """Truncate text intelligently at word boundaries"""
    if len(text) <= max_length:
        return text
    
    # Try to break at word boundary
    cutoff = text.rfind(' ', 0, max_length - 3)
    if cutoff == -1 or cutoff < max_length * 0.7:
        cutoff = max_length - 3
    
    return text[:cutoff] + "..."