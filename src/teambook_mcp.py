#!/usr/bin/env python3
"""
TEAMBOOK MCP COMPATIBILITY LAYER
=================================
Maps the expected MCP interface to Teambook v6.0 primitives.
This allows existing tools to work with the new architecture.
"""

import sys
from pathlib import Path

# Add teambook directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import from the teambook package
try:
    from teambook import TeamBook
    from teambook import put, get, query, note, claim, drop, done, link, sign, dm, share
    TB_AVAILABLE = True
    
    # Create a default TeamBook instance
    _tb = TeamBook()
    
except ImportError as e:
    print(f"Warning: Could not import teambook: {e}")
    TB_AVAILABLE = False
    _tb = None


# ============ COMPATIBILITY MAPPINGS ============

def write(content: str, type: str = None, priority: str = None, linked_items: list = None, **kwargs):
    """Share content with team (maps to put)"""
    if not TB_AVAILABLE:
        return {"error": "Teambook not available"}
    
    # v6.0 put is simpler - just content and optional meta
    meta = {}
    if type:
        meta['type'] = type
    if priority:
        meta['priority'] = priority
    if linked_items:
        meta['linked_items'] = linked_items
    
    try:
        result = _tb.put(content, meta=meta if meta else None)
        # Format response for compatibility
        if isinstance(result, dict) and 'id' in result:
            return {"created": f"[{result['id']}] {content[:50]}..."}
        return result
    except Exception as e:
        return {"error": str(e)}


def read(full: bool = False, type: str = None, status: str = None, **kwargs):
    """View team activity (maps to query)"""
    if not TB_AVAILABLE:
        return {"error": "Teambook not available"}
    
    # Build filter for v6.0 query
    filter_dict = {}
    if type:
        filter_dict['type'] = type
    if status:
        filter_dict['status'] = status
    if full:
        filter_dict['mode'] = 'full'
    
    try:
        result = _tb.query(filter=filter_dict if filter_dict else None)
        
        if not result:
            return {"msg": "No entries found"}
        
        if not full:
            # Summary mode
            tasks = sum(1 for e in result if e.get('type') == 'task')
            notes = sum(1 for e in result if e.get('type') == 'note')
            decisions = sum(1 for e in result if e.get('type') == 'decision')
            
            summary_parts = []
            if tasks > 0:
                summary_parts.append(f"{tasks} tasks")
            if notes > 0:
                summary_parts.append(f"{notes} notes")
            if decisions > 0:
                summary_parts.append(f"{decisions} decisions")
            
            return {"summary": " | ".join(summary_parts) if summary_parts else "Empty"}
        else:
            # Full mode - format entries
            entries = []
            for e in result[:20]:
                entry_str = f"[{e.get('id', '?')}] {e.get('formatted', '')[:80]}"
                entries.append(entry_str)
            return {"entries": entries}
            
    except Exception as e:
        return {"error": str(e)}


def comment(id: int, content: str, **kwargs):
    """Add comment to entry (maps to note)"""
    if not TB_AVAILABLE:
        return {"error": "Teambook not available"}
    
    try:
        # Handle string IDs
        if isinstance(id, str):
            id = id.strip('[]')
            if id.startswith('tb_'):
                pass  # Use as-is
            else:
                id = int(id) if id.isdigit() else id
        
        result = _tb.note(id, content)
        
        if isinstance(result, dict) and 'id' in result:
            return {"commented": f"[{id}] +comment: {content[:50]}"}
        return result
        
    except Exception as e:
        return {"error": str(e)}


def complete(id: int, evidence: str = None, **kwargs):
    """Complete a task (maps to done)"""
    if not TB_AVAILABLE:
        return {"error": "Teambook not available"}
    
    try:
        # Handle string IDs
        if isinstance(id, str):
            id = id.strip('[]')
            if id.startswith('tb_'):
                pass  # Use as-is
            else:
                id = int(id) if id.isdigit() else id
        
        result = _tb.done(id, result=evidence)
        
        if isinstance(result, dict):
            if 'done' in result and result['done']:
                msg = f"[{result.get('id', id)}]✓"
                if 'duration' in result:
                    msg += f" in {result['duration']}"
                if evidence:
                    msg += f" - {evidence[:50]}"
                return {"completed": msg}
            return result
        return result
        
    except Exception as e:
        return {"error": str(e)}


def status(full: bool = False, **kwargs):
    """Get team status (uses query)"""
    if not TB_AVAILABLE:
        return {"error": "Teambook not available"}
    
    try:
        # Get all entries for status calculation
        all_entries = _tb.query(limit=100)
        
        if not all_entries:
            return {"status": "Teambook empty"}
        
        # Calculate stats
        tasks_pending = sum(1 for e in all_entries 
                          if e.get('type') == 'task' and not e.get('done_at'))
        tasks_done = sum(1 for e in all_entries 
                        if e.get('type') == 'task' and e.get('done_at'))
        tasks_claimed = sum(1 for e in all_entries 
                          if e.get('type') == 'task' and e.get('claimed_by') and not e.get('done_at'))
        notes = sum(1 for e in all_entries if e.get('type') == 'note')
        decisions = sum(1 for e in all_entries if e.get('type') == 'decision')
        
        status_parts = []
        if tasks_pending > 0:
            status_parts.append(f"{tasks_pending} tasks ({tasks_claimed} claimed)")
        if tasks_done > 0:
            status_parts.append(f"{tasks_done} done")
        if notes > 0:
            status_parts.append(f"{notes} notes")
        if decisions > 0:
            status_parts.append(f"{decisions} decisions")
        
        return {"status": " | ".join(status_parts) if status_parts else "Empty"}
        
    except Exception as e:
        return {"error": str(e)}


def projects(**kwargs):
    """List available projects (stub for v6.0)"""
    return {"projects": ["default"], "default": "default"}


def batch(operations: list, **kwargs):
    """Execute multiple operations"""
    if not TB_AVAILABLE:
        return {"error": "Teambook not available"}
    
    results = []
    for op in operations:
        op_type = op.get('type')
        op_args = op.get('args', {})
        
        op_map = {
            'write': write,
            'read': read,
            'comment': comment,
            'claim': claim,
            'complete': complete,
            'status': status
        }
        
        if op_type in op_map:
            result = op_map[op_type](**op_args)
            results.append(result)
        else:
            results.append({"error": f"Unknown operation: {op_type}"})
    
    return {"batch_results": results, "count": len(results)}


def update(id: int, **kwargs):
    """Update entry (not in v6.0, returns error)"""
    return {"error": "Update not supported in Teambook v6.0 (immutable design)"}


def archive(id: int, **kwargs):
    """Archive entry (not in v6.0, returns error)"""
    return {"error": "Archive not supported in Teambook v6.0 (use done instead)"}


# For backward compatibility with expected names
def view_conflicts(**kwargs):
    """No conflicts in v6.0 local mode"""
    return {"msg": "No conflicts (local mode)"}


def resolve_conflict(**kwargs):
    """No conflicts in v6.0 local mode"""
    return {"error": "No conflicts to resolve (local mode)"}


def get_my_key(**kwargs):
    """Get crypto key (if available)"""
    if not TB_AVAILABLE:
        return {"error": "Teambook not available"}
    
    # v6.0 doesn't expose keys directly in local mode
    return {
        "public_key": "Local-Mode-No-Key",
        "identity": _tb.author if _tb else "Unknown",
        "tip": "Teambook v6.0 in local mode - no crypto needed"
    }


# Also export the raw v6.0 primitives for direct use
__all__ = [
    'write', 'read', 'get', 'comment', 'claim', 'complete',
    'update', 'archive', 'status', 'projects', 'batch',
    'view_conflicts', 'resolve_conflict', 'get_my_key',
    # v6.0 primitives
    'put', 'query', 'note', 'done', 'drop', 'link', 'sign', 'dm', 'share',
    'TeamBook'
]


# Quick test when run directly
if __name__ == "__main__":
    print("Teambook MCP Compatibility Layer")
    print("-" * 40)
    
    if TB_AVAILABLE:
        print("✓ Teambook v6.0 loaded successfully")
        print(f"  AI ID: {_tb.ai_id if _tb and hasattr(_tb, 'ai_id') else 'Unknown'}")
        print(f"  Database: {_tb.db.db_path if _tb and hasattr(_tb, 'db') else 'default.db'}")
        
        # Test basic operations
        print("\nTesting compatibility functions:")
        
        # Test write
        result = write("TEST: Compatibility layer test")
        print(f"  write: {result}")
        
        # Test read
        result = read()
        print(f"  read: {result}")
        
        # Test status
        result = status()
        print(f"  status: {result}")
        
    else:
        print("✗ Teambook not available")
        print("  Check that teambook package is properly installed")
