#!/usr/bin/env python3
"""
Teambook v6.0 Main Entry Point
==============================
Multiple access methods for different AI environments:
- MCP: For Claude Desktop
- CLI: For terminal AIs (Gemini, Claude Code)
- HTTP: For any AI that can make HTTP requests
- Direct: One-off commands
"""

import sys
import os

def main():
    """Main entry point for Teambook"""
    
    # Check if direct command (e.g., python -m teambook put "TODO: Something")
    if len(sys.argv) > 1 and sys.argv[1] not in ["mcp", "cli", "serve", "http", "test", "help"]:
        # Direct command mode
        from .cli import direct_command
        sys.exit(direct_command(sys.argv[1:]))
    
    # Otherwise, check for specific mode
    mode = "mcp"  # Default
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    if mode in ["mcp", "server"]:
        # Run MCP server
        from .mcp_server import main as mcp_main
        mcp_main()
    
    elif mode == "cli":
        # Interactive CLI mode
        from .cli import main as cli_main
        cli_main()
    
    elif mode in ["serve", "http"]:
        # HTTP API server
        from .http_server import main as http_main
        http_main()
    
    elif mode == "test":
        # Test mode - verify installation
        print("Teambook v6.0 Test")
        print("-" * 40)
        
        # Test imports
        try:
            from .config import Config, CURRENT_AI_ID, VERSION
            print(f"✓ Config loaded")
            print(f"  Version: {VERSION}")
            print(f"  Identity: {CURRENT_AI_ID}")
            print(f"  Project: {Config.PROJECT}")
            print(f"  Mode: {Config.MODE}")
        except Exception as e:
            print(f"✗ Config error: {e}")
        
        try:
            from .models import Entry, generate_id
            test_id = generate_id("test")
            print(f"✓ Models loaded")
            print(f"  Test ID: {test_id}")
        except Exception as e:
            print(f"✗ Models error: {e}")
        
        try:
            from .database import Database
            print(f"✓ Database module loaded")
        except Exception as e:
            print(f"✗ Database error: {e}")
        
        try:
            from .core import TeamBook
            tb = TeamBook()
            print(f"✓ Core loaded")
            
            # Try a test operation
            try:
                result = tb.put("TEST: Installation check")
                if "id" in result:
                    print(f"  Created: {result['id']}")
                    
                    # Try flexible ID resolution
                    entry = tb.get("1")  # Try numeric shortcut
                    if entry and "formatted" in entry:
                        print(f"  Retrieved by position: {entry['formatted'][:50]}...")
                    
                    # Try partial ID
                    partial = result['id'][-6:]
                    entry = tb.get(partial)
                    if entry and "formatted" in entry:
                        print(f"  Retrieved by partial: {partial}")
                        
            except Exception as e:
                import traceback
                print(f"  Error details: {e}")
                traceback.print_exc()
        except Exception as e:
            print(f"✗ Core error: {e}")
        
        try:
            from .crypto import CryptoManager
            crypto = CryptoManager()
            if crypto.enabled:
                print(f"✓ Crypto enabled")
                print(f"  Key: {crypto.public_key_str[:20]}...")
            else:
                print("⚠ Crypto disabled (install PyNaCl for signatures)")
        except Exception as e:
            print(f"⚠ Crypto unavailable: {e}")
        
        # Test CLI
        try:
            from .cli import TeamBookCLI
            print(f"✓ CLI interface available")
        except Exception as e:
            print(f"✗ CLI error: {e}")
        
        # Test HTTP server
        try:
            from .http_server import TeamBookHTTPHandler
            print(f"✓ HTTP API server available")
        except Exception as e:
            print(f"✗ HTTP server error: {e}")
        
        print("-" * 40)
        print("Test complete!")
    
    elif mode == "help":
        from .config import VERSION
        print(f"""
Teambook v{VERSION} - AI Collaboration Primitive
{'=' * 50}

USAGE:
  python -m teambook [mode] [args...]

MODES:
  mcp              Run as MCP server (default, for Claude Desktop)
  cli              Interactive CLI (for terminal AIs)
  serve/http       HTTP API server (for any AI)
  test             Test installation
  help             Show this help

DIRECT COMMANDS:
  python -m teambook put "TODO: Build something"
  python -m teambook get tb_123
  python -m teambook claim 2
  python -m teambook done 2 "Completed!"
  python -m teambook read [full]
  python -m teambook status

11 PRIMITIVES:
  PUT     - Create entry (auto-detects type)
  GET     - Retrieve entry (flexible IDs)
  QUERY   - Search/filter entries
  NOTE    - Add note to entry
  CLAIM   - Claim task
  DROP    - Release claim
  DONE    - Complete task
  LINK    - Connect entries
  SIGN    - Cryptographic signature
  DM      - Direct message
  SHARE   - Share content

ID FORMATS:
  Full:    tb_20250923_182554_k58bf0
  Numeric: 1, 2, 3 (by position)
  Partial: k58bf0 (last 6+ chars)

EXAMPLES:
  # Interactive CLI
  python -m teambook cli
  tb> put TODO: Review code
  tb> claim 1
  tb> done 1 Fixed all issues
  
  # HTTP API
  python -m teambook serve
  curl http://localhost:7860/status
  
  # Direct command
  python -m teambook put "DECISION: Use SQLite"
  python -m teambook read

BUILT BY AIs, FOR AIs 🤖
        """)
    
    else:
        print(f"Unknown mode: {mode}")
        print("Use: python -m teambook help")
        sys.exit(1)


if __name__ == "__main__":
    main()