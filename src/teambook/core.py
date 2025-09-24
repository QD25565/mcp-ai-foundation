#!/usr/bin/env python3
"""
Teambook v6.0 Core Operations
==============================
The 11 primitive operations that form the foundation of Teambook.
Simple, self-evident, token-efficient.

PUT, GET, QUERY, NOTE, CLAIM, DROP, DONE, LINK, SIGN, DM, SHARE
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from .config import Config, CURRENT_AI_ID
from .database import Database
from .models import (
    Entry, Note, Link, DM, Share,
    EntryType, generate_id, format_time_compact, smart_truncate
)


class TeamBook:
    """Core Teambook operations - the 11 primitives"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize TeamBook with database"""
        self.db = Database(db_path)
        self.ai_id = CURRENT_AI_ID
        
        # Crypto manager (will be initialized if crypto.py exists)
        self.crypto = None
        try:
            from .crypto import CryptoManager
            self.crypto = CryptoManager()
        except ImportError:
            pass  # Crypto is optional
        
        # Cache for recent entries (for short ID resolution)
        self._recent_entries = []  # List of recent entry IDs for numeric shortcuts
    
    def _resolve_id(self, id_input: str) -> Optional[str]:
        """Resolve flexible ID input to full ID.
        
        Accepts:
        - Full ID: tb_20250923_182554_k58bf0
        - Short numeric: 2 (based on query order)
        - Partial suffix: k58bf0
        - With/without prefix: tb_2
        """
        if not id_input:
            return None
        
        id_str = str(id_input).strip()
        
        # If it's already a full ID (starts with tb_ and has full format)
        if id_str.startswith('tb_') and len(id_str) > 20:
            return id_str
        
        # If it's a numeric shortcut
        if id_str.isdigit():
            idx = int(id_str) - 1  # 1-based index for user-friendliness
            if 0 <= idx < len(self._recent_entries):
                return self._recent_entries[idx]
            # Otherwise, try to find by position in database
            entries = self.db.query_entries({}, limit=100)
            if 0 <= idx < len(entries):
                self._recent_entries = [e.id for e in entries[:20]]  # Cache first 20
                return entries[idx].id
            return None
        
        # Try partial match (suffix)
        if len(id_str) >= 6:  # Reasonable suffix length
            # Query database for partial match
            entries = self.db.query_entries({}, limit=100)
            for entry in entries:
                if entry.id.endswith(id_str) or id_str in entry.id:
                    return entry.id
        
        # Try with tb_ prefix if not present
        if not id_str.startswith('tb_'):
            return self._resolve_id(f'tb_{id_str}')
        
        # Not found
        return None
    
    # === PRIMITIVE 1: PUT ===
    def put(self, content: str, meta: Optional[Dict] = None) -> Dict:
        """Create new entry
        Returns: {"id": "tb_123", "msg": "created"}
        Output: "tb_123 created"
        """
        if not content or not content.strip():
            return {"error": "empty content"}
        
        content = content.strip()[:Config.MAX_CONTENT_LENGTH]
        
        # Auto-detect type
        entry_type = EntryType.detect(content)
        
        # Create entry
        entry = Entry(
            id=generate_id("tb"),
            content=content,
            type=entry_type,
            author=self.ai_id,
            created=datetime.now().isoformat(),
            meta=meta or {}
        )
        
        # Sign if crypto available
        if self.crypto:
            entry.signature = self._sign_data(entry.to_dict())
        
        # Store
        self.db.put_entry(entry)
        
        return {"id": entry.id, "msg": "created"}
    
    # === PRIMITIVE 2: GET ===
    def get(self, id: str) -> Optional[Dict]:
        """Retrieve single entry with notes/links
        Output: "tb_123 Task Review code pending 3d @Swift-Spark"
        """
        # Resolve flexible ID
        resolved_id = self._resolve_id(id)
        if not resolved_id:
            return {"error": f"entry {id} not found"}
        
        entry = self.db.get_entry(resolved_id)
        if not entry:
            return None
        
        # Build response
        result = {
            "id": entry.id,
            "content": entry.content,
            "type": entry.type,
            "author": entry.author,
            "created": entry.created,
            "formatted": entry.format_compact()
        }
        
        # Add task state if applicable
        if entry.type == "task":
            if entry.done_at:
                result["status"] = "done"
                result["duration"] = self._calculate_duration(entry.created, entry.done_at)
            elif entry.claimed_by:
                result["status"] = "claimed"
                result["claimed_by"] = entry.claimed_by
            else:
                result["status"] = "pending"
        
        # Add relations
        if entry.notes:
            result["notes"] = entry.notes
        if entry.links:
            result["links"] = entry.links
        
        return result
    
    # === PRIMITIVE 3: QUERY ===
    def query(self, filter: Optional[Dict] = None, limit: int = 50) -> List[Dict]:
        """Search/filter entries
        Output: "5 tasks 2 claimed | 3 notes | latest 2h"
        """
        entries = self.db.query_entries(filter, limit)
        
        if not entries:
            return []
        
        # Default summary mode
        if not filter or filter.get('mode') != 'full':
            # Summary statistics
            stats = self.db.get_stats()
            
            summary_parts = []
            
            # Task counts
            if stats['tasks']['pending'] > 0:
                parts = [f"{stats['tasks']['pending']} pending"]
                if stats['tasks']['claimed'] > 0:
                    parts.append(f"{stats['tasks']['claimed']} claimed")
                if stats['tasks']['done'] > 0:
                    parts.append(f"{stats['tasks']['done']} done")
                summary_parts.append(" ".join(parts))
            
            # Other types
            for entry_type, count in stats['by_type'].items():
                if entry_type != 'task' and count > 0:
                    summary_parts.append(f"{count} {entry_type}s")
            
            # Latest activity
            if stats['latest']:
                summary_parts.append(f"latest {format_time_compact(stats['latest'])}")
            
            return [{
                "summary": " | ".join(summary_parts),
                "count": len(entries)
            }]
        
        # Full mode - return formatted entries
        return [
            {
                "id": e.id,
                "formatted": e.format_compact(),
                "type": e.type,
                "status": self._get_status(e)
            }
            for e in entries
        ]
    
    # === PRIMITIVE 4: NOTE ===
    def note(self, id: str, text: str, type: str = "comment") -> Dict:
        """Add note to entry
        Returns: {"id": "nt_456", "msg": "added"}
        Output: "nt_456 added to tb_123"
        """
        # Resolve flexible ID
        resolved_id = self._resolve_id(id)
        if not resolved_id:
            return {"error": f"entry {id} not found"}
        
        # Check entry exists
        entry = self.db.get_entry(resolved_id)
        if not entry:
            return {"error": f"entry {id} not found"}
        
        text = text.strip()[:Config.MAX_CONTENT_LENGTH]
        if not text:
            return {"error": "empty note"}
        
        # Create note
        note_obj = Note(
            id=generate_id("nt"),
            entry_id=id,
            content=text,
            type=type,
            author=self.ai_id,
            created=datetime.now().isoformat()
        )
        
        # Sign if crypto available
        if self.crypto:
            note_obj.signature = self._sign_data({
                "content": text,
                "entry_id": id,
                "type": type
            })
        
        # Store
        self.db.add_note(note_obj)
        
        return {"id": note_obj.id, "msg": f"added to {resolved_id}"}
    
    # === PRIMITIVE 5: CLAIM ===
    def claim(self, id: str) -> Dict:
        """Claim a task
        Returns: {"claimed": True, "id": "tb_123"}
        Output: "claimed tb_123"
        """
        # Resolve flexible ID
        resolved_id = self._resolve_id(id)
        if not resolved_id:
            return {"error": f"entry {id} not found"}
        
        entry = self.db.get_entry(resolved_id)
        if not entry:
            return {"error": f"entry {id} not found"}
        
        if entry.type != "task":
            return {"error": f"{id} not a task"}
        
        if entry.claimed_by:
            return {"error": f"{id} already claimed by {entry.claimed_by}"}
        
        if entry.done_at:
            return {"error": f"{id} already done"}
        
        # Claim it
        self.db.update_entry(resolved_id, {
            "claimed_by": self.ai_id,
            "claimed_at": datetime.now().isoformat()
        })
        
        return {"claimed": True, "id": resolved_id}
    
    # === PRIMITIVE 6: DROP ===
    def drop(self, id: str) -> Dict:
        """Release claim on task
        Returns: {"dropped": True, "id": "tb_123"}
        Output: "dropped tb_123"
        """
        # Resolve flexible ID
        resolved_id = self._resolve_id(id)
        if not resolved_id:
            return {"error": f"entry {id} not found"}
        
        entry = self.db.get_entry(resolved_id)
        if not entry:
            return {"error": f"entry {id} not found"}
        
        if entry.type != "task":
            return {"error": f"{id} not a task"}
        
        if not entry.claimed_by:
            return {"error": f"{id} not claimed"}
        
        if entry.claimed_by != self.ai_id:
            return {"error": f"{id} claimed by {entry.claimed_by}, not you"}
        
        # Drop it
        self.db.update_entry(resolved_id, {
            "claimed_by": None,
            "claimed_at": None
        })
        
        return {"dropped": True, "id": resolved_id}
    
    # === PRIMITIVE 7: DONE ===
    def done(self, id: str, result: Optional[str] = None) -> Dict:
        """Mark task complete
        Returns: {"done": True, "id": "tb_123", "duration": "45m"}
        Output: "tb_123 done 45m"
        """
        # Resolve flexible ID
        resolved_id = self._resolve_id(id)
        if not resolved_id:
            return {"error": f"entry {id} not found"}
        
        entry = self.db.get_entry(resolved_id)
        if not entry:
            return {"error": f"entry {id} not found"}
        
        if entry.type != "task":
            return {"error": f"{id} not a task"}
        
        if entry.done_at:
            return {"error": f"{id} already done"}
        
        # Truncate result if needed
        if result:
            result = result.strip()[:Config.MAX_EVIDENCE_LENGTH]
        
        # Mark done
        now = datetime.now().isoformat()
        self.db.update_entry(resolved_id, {
            "done_at": now,
            "result": result
        })
        
        # Calculate duration
        duration = self._calculate_duration(entry.created, now)
        
        response = {"done": True, "id": resolved_id, "duration": duration}
        if result:
            response["result"] = smart_truncate(result, 50)
        
        return response
    
    # === PRIMITIVE 8: LINK ===
    def link(self, from_id: str, to_id: str, rel: str = "related") -> Dict:
        """Connect two entries
        Returns: {"linked": True, "from": "tb_123", "to": "tb_456"}
        Output: "linked tb_123 -> tb_456"
        """
        # Resolve both IDs
        resolved_from = self._resolve_id(from_id)
        resolved_to = self._resolve_id(to_id)
        
        if not resolved_from:
            return {"error": f"entry {from_id} not found"}
        if not resolved_to:
            return {"error": f"entry {to_id} not found"}
        
        # Check both entries exist
        from_entry = self.db.get_entry(resolved_from)
        to_entry = self.db.get_entry(resolved_to)
        
        if not from_entry:
            return {"error": f"entry {from_id} not found"}
        if not to_entry:
            return {"error": f"entry {to_id} not found"}
        
        # Create link
        link_obj = Link(
            from_id=from_id,
            to_id=to_id,
            rel=rel,
            created=datetime.now().isoformat(),
            created_by=self.ai_id
        )
        
        success = self.db.add_link(link_obj)
        
        if success:
            return {"linked": True, "from": from_id, "to": to_id}
        else:
            return {"error": "link already exists"}
    
    # === PRIMITIVE 9: SIGN ===
    def sign(self, data: Dict) -> str:
        """Sign data with Ed25519
        Returns: Signature string
        Output: "Ed25519:abc123..." (only when explicitly requested)
        """
        if not self.crypto:
            return ""
        
        return self._sign_data(data)
    
    # === PRIMITIVE 10: DM ===
    def dm(self, to: str, msg: str, meta: Optional[Dict] = None) -> Dict:
        """Send direct message
        Returns: {"sent": True, "id": "dm_789"}
        Output: "dm_789 to Gemini-AI"
        """
        msg = msg.strip()[:Config.MAX_MESSAGE_LENGTH]
        if not msg:
            return {"error": "empty message"}
        
        # Create DM
        dm_obj = DM(
            id=generate_id("dm"),
            from_ai=self.ai_id,
            to_ai=to,
            msg=msg,
            created=datetime.now().isoformat(),
            meta=meta or {}
        )
        
        # Sign if crypto available
        if self.crypto:
            dm_obj.signature = self._sign_data({
                "from": self.ai_id,
                "to": to,
                "msg": msg
            })
        
        # Store
        self.db.send_dm(dm_obj)
        
        return {"sent": True, "id": dm_obj.id, "to": to}
    
    # === PRIMITIVE 11: SHARE ===
    def share(self, to: str, content: str, type: str = "code") -> Dict:
        """Share content with AI(s)
        to: AI name or "*" for broadcast
        Returns: {"shared": True, "id": "sh_012"}
        Output: "sh_012 code to Gemini-AI"
        """
        content = content.strip()
        if not content:
            return {"error": "empty content"}
        
        # Handle broadcast
        recipient = None if to == "*" else to
        
        # Create share
        share_obj = Share(
            id=generate_id("sh"),
            from_ai=self.ai_id,
            to_ai=recipient,
            content=content,
            type=type,
            created=datetime.now().isoformat()
        )
        
        # Sign if crypto available
        if self.crypto:
            share_obj.signature = self._sign_data({
                "from": self.ai_id,
                "to": recipient,
                "content": content,
                "type": type
            })
        
        # Store
        self.db.add_share(share_obj)
        
        recipient_str = to if to != "*" else "all"
        return {"shared": True, "id": share_obj.id, "type": type, "to": recipient_str}
    
    # === Helper Methods ===
    
    def _sign_data(self, data: Dict) -> str:
        """Sign data with crypto manager if available"""
        if not self.crypto:
            return ""
        
        # Canonical JSON for consistent signatures
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return Config.SIGNATURE_PREFIX + self.crypto.sign(canonical)
    
    def _get_status(self, entry: Entry) -> str:
        """Get task status"""
        if entry.type != "task":
            return ""
        
        if entry.done_at:
            return "done"
        elif entry.claimed_by:
            return "claimed"
        else:
            return "pending"
    
    def _calculate_duration(self, start: str, end: str) -> str:
        """Calculate duration between timestamps"""
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            delta = end_dt - start_dt
            
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


# === Module-level convenience functions ===
# These allow: from teambook import put, get, query, etc.

_default_tb = None

def _get_default_teambook():
    """Get or create default TeamBook instance"""
    global _default_tb
    if _default_tb is None:
        _default_tb = TeamBook()
    return _default_tb

def put(content: str, meta: Optional[Dict] = None) -> Dict:
    """Create new entry"""
    return _get_default_teambook().put(content, meta)

def get(id: str) -> Optional[Dict]:
    """Retrieve entry"""
    return _get_default_teambook().get(id)

def query(filter: Optional[Dict] = None, limit: int = 50) -> List[Dict]:
    """Query entries"""
    return _get_default_teambook().query(filter, limit)

def note(id: str, text: str, type: str = "comment") -> Dict:
    """Add note to entry"""
    return _get_default_teambook().note(id, text, type)

def claim(id: str) -> Dict:
    """Claim task"""
    return _get_default_teambook().claim(id)

def drop(id: str) -> Dict:
    """Drop claim"""
    return _get_default_teambook().drop(id)

def done(id: str, result: Optional[str] = None) -> Dict:
    """Mark done"""
    return _get_default_teambook().done(id, result)

def link(from_id: str, to_id: str, rel: str = "related") -> Dict:
    """Link entries"""
    return _get_default_teambook().link(from_id, to_id, rel)

def sign(data: Dict) -> str:
    """Sign data"""
    return _get_default_teambook().sign(data)

def dm(to: str, msg: str, meta: Optional[Dict] = None) -> Dict:
    """Send DM"""
    return _get_default_teambook().dm(to, msg, meta)

def share(to: str, content: str, type: str = "code") -> Dict:
    """Share content"""
    return _get_default_teambook().share(to, content, type)