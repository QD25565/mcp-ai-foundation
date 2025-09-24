"""
Teambook v6.0 - Foundational collaboration primitive for AI agents
===================================================================
Simple, efficient, cryptographically secure team coordination.

11 core primitives: PUT, GET, QUERY, NOTE, CLAIM, DROP, DONE, LINK, SIGN, DM, SHARE
"""

__version__ = "6.0.0"
__author__ = "AI Foundation"

# Import the configuration
from .config import Config, CURRENT_AI_ID, VERSION

# Import TeamBook class and create singleton instance
_teambook_instance = None

def _get_teambook():
    """Get or create singleton TeamBook instance"""
    global _teambook_instance
    if _teambook_instance is None:
        from .core import TeamBook
        _teambook_instance = TeamBook()
    return _teambook_instance

# Export primitive functions as standalone
def put(content: str, meta: dict = None):
    """Create new entry"""
    return _get_teambook().put(content, meta)

def get(id: str):
    """Retrieve entry by ID"""
    return _get_teambook().get(id)

def query(filter: dict = None, limit: int = 50):
    """Query entries"""
    return _get_teambook().query(filter, limit)

def note(id: str, text: str, type: str = "comment"):
    """Add note to entry"""
    return _get_teambook().note(id, text, type)

def claim(id: str):
    """Claim a task"""
    return _get_teambook().claim(id)

def drop(id: str):
    """Drop/unclaim a task"""
    return _get_teambook().drop(id)

def done(id: str, result: str = None):
    """Mark task as done"""
    return _get_teambook().done(id, result)

def link(from_id: str, to_id: str, rel: str = "related"):
    """Link two entries"""
    return _get_teambook().link(from_id, to_id, rel)

def sign(data: dict):
    """Sign data cryptographically"""
    return _get_teambook().sign(data)

def dm(to: str, msg: str, meta: dict = None):
    """Send direct message"""
    return _get_teambook().dm(to, msg, meta)

def share(to: str, content: str, type: str = "code"):
    """Share content"""
    return _get_teambook().share(to, content, type)

# Also export TeamBook class for direct use
from .core import TeamBook

# Export all
__all__ = [
    'Config', 'CURRENT_AI_ID', 'VERSION', 'TeamBook',
    'put', 'get', 'query', 'note', 'claim', 'drop', 
    'done', 'link', 'sign', 'dm', 'share'
]
