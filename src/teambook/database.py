#!/usr/bin/env python3
"""
Teambook v6.0 Database Layer
============================
SQLite abstraction with full-text search and efficient queries.
Immutable entries, append-only design.
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from .config import Config
from .models import Entry, Note, Link, DM, Share

# Configure logging
logging.basicConfig(level=logging.INFO, stream=None)  # No output by default


class Database:
    """SQLite database manager for Teambook"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection"""
        self.db_path = db_path or Config.DB_FILE
        self.conn = None
        self.init_db()
    
    def init_db(self):
        """Initialize database with all required tables"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(
            str(self.db_path),
            timeout=Config.DB_TIMEOUT / 1000,  # Convert ms to seconds
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        
        # Create tables
        self._create_tables()
        
        # Create indices
        self._create_indices()
        
        self.conn.commit()
    
    def _create_tables(self):
        """Create all required tables"""
        
        # Main entries table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                author TEXT NOT NULL,
                created TEXT NOT NULL,
                signature TEXT,
                meta TEXT,
                claimed_by TEXT,
                claimed_at TEXT,
                done_at TEXT,
                result TEXT
            )
        ''')
        
        # Notes/comments on entries
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                author TEXT NOT NULL,
                created TEXT NOT NULL,
                signature TEXT,
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            )
        ''')
        
        # Links between entries
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS links (
                from_id TEXT NOT NULL,
                to_id TEXT NOT NULL,
                rel TEXT NOT NULL,
                created TEXT NOT NULL,
                created_by TEXT NOT NULL,
                PRIMARY KEY(from_id, to_id, rel)
            )
        ''')
        
        # Direct messages
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS dms (
                id TEXT PRIMARY KEY,
                from_ai TEXT NOT NULL,
                to_ai TEXT NOT NULL,
                msg TEXT NOT NULL,
                created TEXT NOT NULL,
                signature TEXT,
                meta TEXT
            )
        ''')
        
        # Shared files/code
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS shares (
                id TEXT PRIMARY KEY,
                from_ai TEXT NOT NULL,
                to_ai TEXT,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                created TEXT NOT NULL,
                signature TEXT,
                meta TEXT
            )
        ''')
        
        # Full-text search virtual table
        # Using simple FTS without content linking due to text IDs
        self.conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts 
            USING fts5(
                id UNINDEXED,
                content
            )
        ''')
        
        # Note: FTS will be manually synced due to text IDs
        # (SQLite FTS expects integer rowids)
    
    def _create_indices(self):
        """Create performance indices"""
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(type)",
            "CREATE INDEX IF NOT EXISTS idx_entries_author ON entries(author)",
            "CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created DESC)",
            "CREATE INDEX IF NOT EXISTS idx_entries_claimed ON entries(claimed_by)",
            "CREATE INDEX IF NOT EXISTS idx_entries_done ON entries(done_at)",
            "CREATE INDEX IF NOT EXISTS idx_notes_entry ON notes(entry_id)",
            "CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_id)",
            "CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_id)",
            "CREATE INDEX IF NOT EXISTS idx_dms_participants ON dms(from_ai, to_ai)",
            "CREATE INDEX IF NOT EXISTS idx_dms_created ON dms(created DESC)",
            "CREATE INDEX IF NOT EXISTS idx_shares_recipient ON shares(to_ai)",
            "CREATE INDEX IF NOT EXISTS idx_shares_created ON shares(created DESC)"
        ]
        
        for index in indices:
            self.conn.execute(index)
    
    # === Entry Operations ===
    
    def put_entry(self, entry: Entry) -> str:
        """Store new entry"""
        data = entry.to_dict()
        
        # Serialize meta to JSON if it exists
        meta_json = json.dumps(data.get('meta')) if data.get('meta') else None
        
        # Don't store notes and links in entries table - they have their own tables
        self.conn.execute('''
            INSERT INTO entries (
                id, content, type, author, created, signature, 
                meta, claimed_by, claimed_at, done_at, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['content'], data['type'], data['author'],
            data['created'], data.get('signature'), meta_json,
            data.get('claimed_by'), data.get('claimed_at'),
            data.get('done_at'), data.get('result')
        ))
        
        # Manually sync with FTS
        try:
            self.conn.execute(
                'INSERT INTO entries_fts(id, content) VALUES (?, ?)',
                (data['id'], data['content'])
            )
        except:
            pass  # FTS is optional
        
        self.conn.commit()
        return entry.id
    
    def get_entry(self, entry_id: str) -> Optional[Entry]:
        """Retrieve single entry with notes and links"""
        cursor = self.conn.execute(
            'SELECT * FROM entries WHERE id = ?', (entry_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        entry_dict = dict(row)
        
        # Deserialize meta from JSON if it exists
        if entry_dict.get('meta'):
            try:
                entry_dict['meta'] = json.loads(entry_dict['meta'])
            except json.JSONDecodeError:
                entry_dict['meta'] = {}
        
        # Get associated notes
        notes = self.conn.execute(
            'SELECT id FROM notes WHERE entry_id = ? ORDER BY created',
            (entry_id,)
        ).fetchall()
        entry_dict['notes'] = [n['id'] for n in notes]
        
        # Get associated links
        links_from = self.conn.execute(
            'SELECT to_id FROM links WHERE from_id = ?',
            (entry_id,)
        ).fetchall()
        links_to = self.conn.execute(
            'SELECT from_id FROM links WHERE to_id = ?',
            (entry_id,)
        ).fetchall()
        
        entry_dict['links'] = list(set(
            [l['to_id'] for l in links_from] + 
            [l['from_id'] for l in links_to]
        ))
        
        return Entry.from_dict(entry_dict)
    
    def query_entries(self, filter_dict: Optional[Dict] = None, 
                     limit: int = 50) -> List[Entry]:
        """Query entries with filters"""
        
        # Build query
        query = "SELECT * FROM entries"
        params = []
        conditions = []
        
        if filter_dict:
            if 'type' in filter_dict:
                conditions.append("type = ?")
                params.append(filter_dict['type'])
            
            if 'author' in filter_dict:
                conditions.append("author = ?")
                params.append(filter_dict['author'])
            
            if 'status' in filter_dict:
                status = filter_dict['status']
                if status == 'pending':
                    conditions.append("type = 'task' AND done_at IS NULL AND claimed_by IS NULL")
                elif status == 'claimed':
                    conditions.append("type = 'task' AND claimed_by IS NOT NULL AND done_at IS NULL")
                elif status == 'done':
                    conditions.append("type = 'task' AND done_at IS NOT NULL")
            
            if 'search' in filter_dict:
                # Use FTS for text search
                fts_query = "SELECT id FROM entries_fts WHERE content MATCH ?"
                fts_results = self.conn.execute(fts_query, (filter_dict['search'],)).fetchall()
                if fts_results:
                    ids = [r['id'] for r in fts_results]
                    placeholders = ','.join(['?'] * len(ids))
                    conditions.append(f"id IN ({placeholders})")
                    params.extend(ids)
                else:
                    # No matches
                    return []
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Add ordering and limit
        query += " ORDER BY created DESC LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        
        entries = []
        for row in rows:
            entry_dict = dict(row)
            # Deserialize meta from JSON if it exists
            if entry_dict.get('meta'):
                try:
                    entry_dict['meta'] = json.loads(entry_dict['meta'])
                except json.JSONDecodeError:
                    entry_dict['meta'] = {}
            entries.append(Entry.from_dict(entry_dict))
        
        return entries
    
    def update_entry(self, entry_id: str, updates: Dict) -> bool:
        """Update specific fields of an entry"""
        if not updates:
            return False
        
        # Build UPDATE query
        set_clauses = []
        params = []
        
        for field, value in updates.items():
            if field in ['claimed_by', 'claimed_at', 'done_at', 'result']:
                set_clauses.append(f"{field} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        query = f"UPDATE entries SET {', '.join(set_clauses)} WHERE id = ?"
        params.append(entry_id)
        
        cursor = self.conn.execute(query, params)
        self.conn.commit()
        
        return cursor.rowcount > 0
    
    # === Note Operations ===
    
    def add_note(self, note: Note) -> str:
        """Add note to entry"""
        self.conn.execute('''
            INSERT INTO notes (id, entry_id, content, type, author, created, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            note.id, note.entry_id, note.content, note.type,
            note.author, note.created, note.signature
        ))
        
        self.conn.commit()
        return note.id
    
    def get_notes(self, entry_id: str) -> List[Note]:
        """Get all notes for an entry"""
        cursor = self.conn.execute(
            'SELECT * FROM notes WHERE entry_id = ? ORDER BY created',
            (entry_id,)
        )
        
        notes = []
        for row in cursor.fetchall():
            notes.append(Note.from_dict(dict(row)))
        
        return notes
    
    # === Link Operations ===
    
    def add_link(self, link: Link) -> bool:
        """Add link between entries"""
        try:
            self.conn.execute('''
                INSERT INTO links (from_id, to_id, rel, created, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                link.from_id, link.to_id, link.rel, 
                link.created, link.created_by
            ))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Link already exists
            return False
    
    # === DM Operations ===
    
    def send_dm(self, dm: DM) -> str:
        """Store direct message"""
        data = {
            'meta': json.dumps(dm.meta) if dm.meta else None
        }
        
        self.conn.execute('''
            INSERT INTO dms (id, from_ai, to_ai, msg, created, signature, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            dm.id, dm.from_ai, dm.to_ai, dm.msg,
            dm.created, dm.signature, data['meta']
        ))
        
        self.conn.commit()
        return dm.id
    
    def get_dms(self, ai_id: str, unread_only: bool = False) -> List[DM]:
        """Get DMs for an AI"""
        query = '''
            SELECT * FROM dms 
            WHERE to_ai = ? OR from_ai = ?
            ORDER BY created DESC
            LIMIT 50
        '''
        
        cursor = self.conn.execute(query, (ai_id, ai_id))
        
        dms = []
        for row in cursor.fetchall():
            dm_dict = dict(row)
            # Deserialize meta from JSON if it exists
            if dm_dict.get('meta'):
                try:
                    dm_dict['meta'] = json.loads(dm_dict['meta'])
                except json.JSONDecodeError:
                    dm_dict['meta'] = {}
            dms.append(DM.from_dict(dm_dict))
        
        return dms
    
    # === Share Operations ===
    
    def add_share(self, share: Share) -> str:
        """Store shared content"""
        data = {
            'meta': json.dumps(share.meta) if share.meta else None
        }
        
        self.conn.execute('''
            INSERT INTO shares (id, from_ai, to_ai, content, type, created, signature, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            share.id, share.from_ai, share.to_ai, share.content,
            share.type, share.created, share.signature, data['meta']
        ))
        
        self.conn.commit()
        return share.id
    
    def get_shares(self, ai_id: Optional[str] = None) -> List[Share]:
        """Get shares (broadcast or targeted to AI)"""
        if ai_id:
            query = '''
                SELECT * FROM shares 
                WHERE to_ai IS NULL OR to_ai = ?
                ORDER BY created DESC
                LIMIT 50
            '''
            cursor = self.conn.execute(query, (ai_id,))
        else:
            query = '''
                SELECT * FROM shares 
                WHERE to_ai IS NULL
                ORDER BY created DESC
                LIMIT 50
            '''
            cursor = self.conn.execute(query)
        
        shares = []
        for row in cursor.fetchall():
            share_dict = dict(row)
            # Deserialize meta from JSON if it exists
            if share_dict.get('meta'):
                try:
                    share_dict['meta'] = json.loads(share_dict['meta'])
                except json.JSONDecodeError:
                    share_dict['meta'] = {}
            shares.append(Share.from_dict(share_dict))
        
        return shares
    
    # === Stats Operations ===
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        # Total entries
        stats['total_entries'] = self.conn.execute(
            'SELECT COUNT(*) FROM entries'
        ).fetchone()[0]
        
        # By type
        type_counts = self.conn.execute('''
            SELECT type, COUNT(*) as count 
            FROM entries 
            GROUP BY type
        ''').fetchall()
        stats['by_type'] = {row['type']: row['count'] for row in type_counts}
        
        # Task stats
        stats['tasks'] = {
            'pending': self.conn.execute(
                "SELECT COUNT(*) FROM entries WHERE type='task' AND done_at IS NULL AND claimed_by IS NULL"
            ).fetchone()[0],
            'claimed': self.conn.execute(
                "SELECT COUNT(*) FROM entries WHERE type='task' AND claimed_by IS NOT NULL AND done_at IS NULL"
            ).fetchone()[0],
            'done': self.conn.execute(
                "SELECT COUNT(*) FROM entries WHERE type='task' AND done_at IS NOT NULL"
            ).fetchone()[0]
        }
        
        # DMs and shares
        stats['dms'] = self.conn.execute('SELECT COUNT(*) FROM dms').fetchone()[0]
        stats['shares'] = self.conn.execute('SELECT COUNT(*) FROM shares').fetchone()[0]
        
        # Latest activity
        latest = self.conn.execute(
            'SELECT created FROM entries ORDER BY created DESC LIMIT 1'
        ).fetchone()
        stats['latest'] = latest['created'] if latest else None
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()