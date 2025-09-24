#!/usr/bin/env python3
"""
Teambook v6.0 HTTP API Server
=============================
Simple HTTP API for AI integration.
Lightweight, no external dependencies beyond standard library.
"""

import json
import sys
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any
import traceback

from .config import VERSION, CURRENT_AI_ID
from .core import TeamBook


class TeamBookHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Teambook API"""
    
    def __init__(self, *args, **kwargs):
        self.tb = TeamBook()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        try:
            if path == "/":
                # Root - show API info
                self.send_json({
                    "service": "Teambook",
                    "version": VERSION,
                    "identity": CURRENT_AI_ID,
                    "endpoints": {
                        "/status": "GET - Team status",
                        "/read": "GET - Read entries (?full=true for full)",
                        "/get": "GET - Get entry (?id=...)",
                        "/write": "POST - Create entry",
                        "/claim": "POST - Claim task",
                        "/complete": "POST - Complete task",
                        "/note": "POST - Add note",
                        "/whoami": "GET - Identity info"
                    }
                })
            
            elif path == "/status":
                stats = self.tb.db.get_stats()
                self.send_json({
                    "total": stats['total_entries'],
                    "tasks": stats['tasks'],
                    "types": stats['by_type'],
                    "latest": stats.get('latest')
                })
            
            elif path == "/read":
                full = params.get('full', ['false'])[0] == 'true'
                filter_dict = {"mode": "full" if full else "summary"}
                
                # Add type filter if provided
                if 'type' in params:
                    filter_dict['type'] = params['type'][0]
                
                results = self.tb.query(filter_dict)
                
                if results and "summary" in results[0]:
                    self.send_json({"summary": results[0]["summary"]})
                else:
                    entries = []
                    for r in results[:50]:
                        if isinstance(r, dict):
                            entries.append({
                                "id": r.get("id"),
                                "formatted": r.get("formatted"),
                                "type": r.get("type"),
                                "status": r.get("status")
                            })
                    self.send_json({"entries": entries, "count": len(entries)})
            
            elif path == "/get":
                entry_id = params.get('id', [''])[0]
                if not entry_id:
                    self.send_error_json(400, "Missing id parameter")
                    return
                
                result = self.tb.get(entry_id)
                if isinstance(result, dict) and "error" in result:
                    self.send_error_json(404, result["error"])
                elif result:
                    self.send_json(result)
                else:
                    self.send_error_json(404, "Entry not found")
            
            elif path == "/whoami":
                info = {
                    "identity": CURRENT_AI_ID,
                    "version": VERSION
                }
                
                if self.tb.crypto and self.tb.crypto.enabled:
                    crypto_info = self.tb.crypto.get_identity_info()
                    info.update({
                        "public_key": crypto_info['public_key'],
                        "algorithm": crypto_info['algorithm']
                    })
                
                self.send_json(info)
            
            else:
                self.send_error_json(404, f"Unknown endpoint: {path}")
                
        except Exception as e:
            self.send_error_json(500, str(e))
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_error_json(400, "Invalid JSON")
                return
        else:
            data = {}
        
        try:
            if path == "/write":
                content = data.get('content', '')
                if not content:
                    self.send_error_json(400, "Missing content")
                    return
                
                result = self.tb.put(content, data.get('meta'))
                self.send_json(result)
            
            elif path == "/claim":
                entry_id = data.get('id', '')
                if not entry_id:
                    self.send_error_json(400, "Missing id")
                    return
                
                result = self.tb.claim(str(entry_id))
                self.send_json(result)
            
            elif path == "/complete":
                entry_id = data.get('id', '')
                if not entry_id:
                    self.send_error_json(400, "Missing id")
                    return
                
                evidence = data.get('evidence')
                result = self.tb.done(str(entry_id), evidence)
                self.send_json(result)
            
            elif path == "/drop":
                entry_id = data.get('id', '')
                if not entry_id:
                    self.send_error_json(400, "Missing id")
                    return
                
                result = self.tb.drop(str(entry_id))
                self.send_json(result)
            
            elif path == "/note":
                entry_id = data.get('id', '')
                text = data.get('text', '')
                
                if not entry_id or not text:
                    self.send_error_json(400, "Missing id or text")
                    return
                
                result = self.tb.note(str(entry_id), text)
                self.send_json(result)
            
            elif path == "/link":
                from_id = data.get('from_id', '')
                to_id = data.get('to_id', '')
                
                if not from_id or not to_id:
                    self.send_error_json(400, "Missing from_id or to_id")
                    return
                
                rel = data.get('rel', 'related')
                result = self.tb.link(str(from_id), str(to_id), rel)
                self.send_json(result)
            
            elif path == "/dm":
                to_ai = data.get('to', '')
                msg = data.get('msg', '')
                
                if not to_ai or not msg:
                    self.send_error_json(400, "Missing to or msg")
                    return
                
                result = self.tb.dm(to_ai, msg)
                self.send_json(result)
            
            elif path == "/share":
                to = data.get('to', '*')
                content = data.get('content', '')
                share_type = data.get('type', 'text')
                
                if not content:
                    self.send_error_json(400, "Missing content")
                    return
                
                result = self.tb.share(to, content, share_type)
                self.send_json(result)
            
            elif path == "/sign":
                sign_data = data.get('data', {})
                result = self.tb.sign(sign_data)
                self.send_json({"signature": result})
            
            else:
                self.send_error_json(404, f"Unknown endpoint: {path}")
                
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            logging.error(traceback.format_exc())
            self.send_error_json(500, str(e))
    
    def send_json(self, data: Dict[str, Any], status: int = 200):
        """Send JSON response"""
        response = json.dumps(data, indent=2)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # CORS for browser-based AIs
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def send_error_json(self, status: int, message: str):
        """Send error response"""
        self.send_json({"error": message}, status)
    
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        # Only log errors
        if args[1][0] not in ('2', '3'):
            sys.stderr.write("%s - - [%s] %s\n" %
                           (self.address_string(),
                            self.log_date_time_string(),
                            format % args))


def run_server(host: str = "127.0.0.1", port: int = 7860):
    """Run HTTP API server"""
    logging.basicConfig(level=logging.INFO)
    
    print(f"""
╔══════════════════════════════════════════╗
║       TEAMBOOK v{VERSION} HTTP API       ║
║         AI Collaboration Server          ║
╚══════════════════════════════════════════╝
    """.strip())
    
    print(f"Identity: {CURRENT_AI_ID}")
    print(f"Starting server on http://{host}:{port}")
    print("Press Ctrl+C to stop\n")
    
    # Create custom handler class with TeamBook instance
    class Handler(TeamBookHTTPHandler):
        def __init__(self, *args, **kwargs):
            # Initialize TeamBook for this handler
            super().__init__(*args, **kwargs)
    
    try:
        server = HTTPServer((host, port), Handler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


def main():
    """Main entry point for HTTP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Teambook HTTP API Server")
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=7860, help='Port to listen on')
    
    args = parser.parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
