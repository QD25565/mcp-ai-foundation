#!/usr/bin/env python3
"""
Teambook Bridge - Universal interface for MCP/CLI/HTTP
=======================================================
Bridge between teambook core and various interfaces.
Pipe-delimited output for maximum context efficiency.
"""

import sys
import os
from pathlib import Path

# Add current directory to path so imports work from anywhere
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the existing teambook modules
try:
    from teambook_storage_mcp import init_db, init_vault_manager, init_vector_db
    from teambook_shared_mcp import CURRENT_AI_ID
    import teambook_api_mcp as api
except ImportError as e:
    print(f"Error: Make sure all 4 teambook files are in the same directory: {e}")
    print("Required files: teambook_api_mcp.py, teambook_main_mcp.py, teambook_shared_mcp.py, teambook_storage_mcp.py")
    sys.exit(1)

class TeambookBridge:
    """Bridge interface that wraps teambook functionality"""
    
    def __init__(self, teambook_name="nexus-dev", ai_name=None):
        self.teambook = teambook_name
        self.ai_name = ai_name or os.environ.get('AI_NAME', CURRENT_AI_ID)
        
        # Initialize and join teambook
        api.use_teambook(teambook_name)
        init_db()
        init_vault_manager()
        init_vector_db()
    
    def write(self, message: str, tags=None) -> str:
        """Write a message - returns pipe format"""
        full_message = f"[{self.ai_name}] {message}"
        result = api.write(full_message, tags=tags or ["message"])
        # Return the pipe-formatted result directly
        return result.get("saved", f"error|{result.get('error', 'unknown')}")
    
    def read(self, limit=10) -> list:
        """Read recent messages - returns list of pipe strings"""
        result = api.read(limit=limit)
        return result.get("notes", [])
    
    def status(self) -> str:
        """Get status - returns pipe format"""
        result = api.get_status(verbose=True)
        return result.get("status", "error|no status")

# =============================================================================
# CLI MODE - Pipe-delimited output only
# =============================================================================
def cli_mode():
    """Command line interface - pipe format only"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Teambook Bridge - Multi-AI collaboration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python teambook_bridge.py write "Hello from Gemini!"
  python teambook_bridge.py read
  python teambook_bridge.py status
  python teambook_bridge.py chat
        """
    )
    
    parser.add_argument('command', 
                       choices=['write', 'read', 'status', 'chat'],
                       help='Command to execute')
    parser.add_argument('message', nargs='?', help='Message for write command')
    parser.add_argument('--name', default=None, help='Your AI name')
    parser.add_argument('--teambook', default='nexus-dev', help='Teambook to use')
    parser.add_argument('--limit', type=int, default=10, help='Messages to read')
    
    args = parser.parse_args()
    
    # Create bridge
    tb = TeambookBridge(args.teambook, args.name)
    
    if args.command == 'write':
        if not args.message:
            message = input("Message: ")
        else:
            message = args.message
        
        result = tb.write(message)
        print(result)
    
    elif args.command == 'read':
        notes = tb.read(args.limit)
        for note in notes:
            print(note)
    
    elif args.command == 'status':
        print(tb.status())
    
    elif args.command == 'chat':
        interactive_chat(tb)

def interactive_chat(tb):
    """Interactive chat mode - minimal output"""
    print(f"{tb.ai_name}|connected|{tb.teambook}")
    print("Commands: message/read/status/quit")
    
    while True:
        try:
            cmd = input(f"{tb.ai_name}> ").strip()
            
            if not cmd:
                continue
            elif cmd.lower() == 'quit':
                print("disconnected")
                break
            elif cmd.lower() == 'read':
                for note in tb.read(5):
                    print(f"  {note}")
            elif cmd.lower() == 'status':
                print(tb.status())
            else:
                # Treat as message
                result = tb.write(cmd)
                print(result)
        
        except KeyboardInterrupt:
            print("\ndisconnected")
            break
        except Exception as e:
            print(f"error|{e}")

# =============================================================================
# HTTP MODE - Minimal JSON only where absolutely necessary
# =============================================================================
def http_server(port=8080):
    """HTTP API server - returns pipe format in JSON wrapper"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    import json
    
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            """Handle GET requests"""
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            teambook = params.get('teambook', ['nexus-dev'])[0]
            ai_name = params.get('name', ['HTTP-Client'])[0]
            
            tb = TeambookBridge(teambook, ai_name)
            
            if parsed.path == '/read':
                limit = int(params.get('limit', ['10'])[0])
                notes = tb.read(limit)
                # Return pipe strings in a simple array
                self.send_text('\n'.join(notes))
            elif parsed.path == '/status':
                self.send_text(tb.status())
            else:
                self.send_text("endpoints|/read|/write|/status")
        
        def do_POST(self):
            """Handle POST requests"""
            if self.path.startswith('/write'):
                length = int(self.headers['Content-Length'])
                data = self.rfile.read(length).decode('utf-8')
                
                # Try to parse as JSON, fall back to plain text
                try:
                    import json
                    parsed = json.loads(data)
                    message = parsed.get('message', '')
                    tags = parsed.get('tags', [])
                    ai_name = parsed.get('name', 'HTTP-Client')
                    teambook = parsed.get('teambook', 'nexus-dev')
                except:
                    # Treat as plain text message
                    message = data.strip()
                    tags = []
                    ai_name = 'HTTP-Client'
                    teambook = 'nexus-dev'
                
                tb = TeambookBridge(teambook, ai_name)
                result = tb.write(message, tags)
                self.send_text(result)
            else:
                self.send_text("error|unknown endpoint")
        
        def send_text(self, text):
            """Send plain text response"""
            response = text.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', len(response))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response)
        
        def log_message(self, format, *args):
            """Suppress logs"""
            pass
    
    print(f"HTTP|listening|localhost:{port}")
    print(f"GET|localhost:{port}/read")
    print(f"GET|localhost:{port}/status")
    print(f"POST|localhost:{port}/write")
    
    server = HTTPServer(('', port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("HTTP|stopped")

# =============================================================================
# MAIN - Auto-detect mode
# =============================================================================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # No arguments - show help in pipe format
        print("Teambook Bridge|v7.0")
        print("CLI|python teambook_bridge.py write MESSAGE")
        print("CLI|python teambook_bridge.py read")
        print("CLI|python teambook_bridge.py chat")
        print("HTTP|python teambook_bridge.py http [PORT]")
        print("MCP|python teambook_main_mcp.py")
    
    elif sys.argv[1] == 'http':
        # Start HTTP server
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        http_server(port)
    
    else:
        # CLI mode
        cli_mode()
