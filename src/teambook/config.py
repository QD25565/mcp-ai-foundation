#!/usr/bin/env python3
"""
Teambook v6.0 Configuration - Multi-Project Support
====================================================
Supports three modes:
1. Central: All AIs share one teambook (default)
2. Project: Each project has its own teambook  
3. Hybrid: Both central and project teambooks

Set TEAMBOOK_MODE environment variable to choose.
"""

import os
import sys
import random
from pathlib import Path
from typing import Optional

# Version
VERSION = "6.0.0"

def get_persistent_id():
    """Get or create persistent AI identity"""
    for location in [Path(__file__).parent.parent, Path.home()]:
        id_file = location / "ai_identity.txt"
        if id_file.exists():
            try:
                with open(id_file, 'r') as f:
                    stored_id = f.read().strip()
                    if stored_id:
                        return stored_id
            except:
                pass
    
    # Generate new ID
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    try:
        id_file = Path(__file__).parent.parent / "ai_identity.txt"
        with open(id_file, 'w') as f:
            f.write(new_id)
    except:
        pass
    
    return new_id

# Global AI identity
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

class Config:
    """Central configuration for Teambook"""
    
    # === MODE SELECTION ===
    MODE = os.getenv("TEAMBOOK_MODE", "central").lower()
    
    # === DATABASE LOCATION ===
    if MODE == "central":
        # All AIs share one central teambook
        if os.getenv("TEAMBOOK_DB_PATH"):
            DB_FILE = Path(os.getenv("TEAMBOOK_DB_PATH"))
        else:
            if sys.platform == 'win32':
                BASE_DIR = Path(r"C:\TeamBookCentral")
            else:
                BASE_DIR = Path.home() / ".teambook_central"
            BASE_DIR.mkdir(parents=True, exist_ok=True)
            DB_FILE = BASE_DIR / "teambook.db"
            
    elif MODE == "project":
        # Each project gets its own teambook
        PROJECT = os.getenv("TEAMBOOK_PROJECT", "default")
        if sys.platform == 'win32':
            BASE_DIR = Path.home() / "AppData" / "Roaming" / "Teambook" / f"project_{PROJECT}"
        else:
            BASE_DIR = Path.home() / f".teambook/project_{PROJECT}"
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        DB_FILE = BASE_DIR / "teambook.db"
        
    elif MODE == "hybrid":
        # Both central and project teambooks
        # This mode requires special handling in core.py
        PROJECT = os.getenv("TEAMBOOK_PROJECT", "default")
        
        # Central database
        if os.getenv("TEAMBOOK_CENTRAL_PATH"):
            CENTRAL_DB = Path(os.getenv("TEAMBOOK_CENTRAL_PATH"))
        else:
            CENTRAL_DB = Path(r"C:\TeamBookCentral\teambook.db") if sys.platform == 'win32' else Path.home() / ".teambook_central/teambook.db"
        
        # Project database  
        if sys.platform == 'win32':
            PROJECT_DIR = Path.home() / "AppData" / "Roaming" / "Teambook" / f"project_{PROJECT}"
        else:
            PROJECT_DIR = Path.home() / f".teambook/project_{PROJECT}"
        PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        PROJECT_DB = PROJECT_DIR / "teambook.db"
        
        # Default to project DB for compatibility
        DB_FILE = PROJECT_DB
        BASE_DIR = PROJECT_DIR
        
    else:
        # Unknown mode - fallback to central
        print(f"Warning: Unknown TEAMBOOK_MODE '{MODE}', using central mode")
        MODE = "central"
        if sys.platform == 'win32':
            BASE_DIR = Path(r"C:\TeamBookCentral")
        else:
            BASE_DIR = Path.home() / ".teambook_central"
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        DB_FILE = BASE_DIR / "teambook.db"
    
    # Make sure directory exists if defined
    try:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    except (AttributeError, NameError):
        pass  # DB_FILE might not be defined yet in some modes
    
    # Project info
    PROJECT = os.getenv("TEAMBOOK_PROJECT", "default")
    PROJECT_DIR = DB_FILE.parent
    
    # Keys (if using crypto)
    KEY_FILE = PROJECT_DIR / "identity.key"
    PUBLIC_KEY_FILE = PROJECT_DIR / "identity.pub"
    
    # === Network Configuration (unused in local mode) ===
    NETWORK_MODE = os.getenv("TEAMBOOK_NETWORK", "local")
    PORT = int(os.getenv("TEAMBOOK_PORT", "7860"))
    HUB_URL = os.getenv("TEAMBOOK_HUB", "")
    PEERS = []
    
    # === Limits ===
    MAX_CONTENT_LENGTH = 10000
    MAX_QUERY_RESULTS = 100
    DB_TIMEOUT = 30000  # Database timeout in milliseconds
    
    # === Crypto ===
    KEY_ALGORITHM = "Ed25519"
    SIGNATURE_PREFIX = "sig:"
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        # Make sure the DB directory exists
        if hasattr(cls, 'DB_FILE'):
            cls.DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # For hybrid mode, ensure both directories
        if cls.MODE == "hybrid":
            if hasattr(cls, 'CENTRAL_DB'):
                cls.CENTRAL_DB.parent.mkdir(parents=True, exist_ok=True)
            if hasattr(cls, 'PROJECT_DB'):
                cls.PROJECT_DB.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure project directory exists
        if hasattr(cls, 'PROJECT_DIR'):
            cls.PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        
        return True
    
    @classmethod
    def get_project_list(cls):
        """List all available teambook projects"""
        projects = []
        
        # Check for central teambook
        if cls.MODE in ["central", "hybrid"]:
            central_db = Path(r"C:\TeamBookCentral\teambook.db") if sys.platform == 'win32' else Path.home() / ".teambook_central/teambook.db"
            if central_db.exists():
                projects.append(("central", central_db))
        
        # Check for project teambooks
        if sys.platform == 'win32':
            teambook_dir = Path.home() / "AppData" / "Roaming" / "Teambook"
        else:
            teambook_dir = Path.home() / ".teambook"
            
        if teambook_dir.exists():
            for project_dir in teambook_dir.glob("project_*"):
                if (project_dir / "teambook.db").exists():
                    project_name = project_dir.name.replace("project_", "")
                    projects.append((project_name, project_dir / "teambook.db"))
        
        return projects

# Initialize directories when module loads
try:
    Config.ensure_directories()
except Exception:
    pass  # Ignore errors during initial import
