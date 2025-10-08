#!/usr/bin/env python3
"""
UNIVERSAL ADAPTER v1.0.0 - PRODUCTION-GRADE MULTI-PROTOCOL BRIDGE
===================================================================
Enables any tool to work across MCP, CLI, and HTTP with platform-aware output.

Features:
- Command aliases (multiple names for same function)
- Fuzzy matching for error suggestions
- Better error messages with "Did you mean?" suggestions

Key Features:
- Platform detection (Windows/macOS/Linux)
- Terminal capability detection
- Emoji fallback for limited environments
- Connection pooling for HTTP
- Request/response logging
- Forgiving input handling
- Security-first design
"""

import sys
import json
import inspect
import importlib
import argparse
import os
import platform
import re
from typing import Dict, List, Any, Callable, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime
import logging
from collections import defaultdict
import time
from difflib import get_close_matches

# ============= COMMAND ALIASES =============

COMMAND_ALIASES = {
    'notebook': {
        'recall': ['read', 'search', 'find'],
        'remember': ['write', 'save', 'note'],
        'get_status': ['status'],
        'pin_note': ['pin'],
        'unpin_note': ['unpin'],
        'get_full_note': ['get'],
        'recent_dirs': ['dirs', 'directories'],
        'compact': ['vacuum', 'optimize'],
        'reindex_embeddings': ['reindex']
    },
    'teambook': {
        'read_dms': ['inbox', 'messages', 'dms', 'get_messages'],
        'send_dm': ['dm', 'message', 'msg'],
        'broadcast': ['announce', 'shout', 'post'],
        'read_channel': ['channel', 'broadcasts', 'broadcast_history'],
        'subscribe': ['sub', 'follow'],
        'unsubscribe': ['unsub', 'unfollow'],
        'watch': ['monitor'],
        'unwatch': ['unmonitor'],
        'get_status': ['status'],
        'who_is_here': ['online', 'active'],
        'what_are_they_doing': ['activity', 'recent']
    },
    'task_manager': {
        'list_tasks': ['tasks', 'todo', 'list', 'show'],
        'add_task': ['add', 'new', 'create'],
        'complete_task': ['complete', 'done', 'finish'],
        'delete_task': ['delete', 'remove', 'del'],
        'task_stats': ['stats', 'statistics']
    },
    'world': {
        'world_command': ['status', 'context', 'info'],
        'datetime_command': ['time', 'date', 'when'],
        'weather_command': ['weather', 'forecast'],
        'context_command': ['context', 'all']
    },
    'session': {
        'start_session': ['context', 'status', 'begin', 'start']
    }
}

# ============= PLATFORM DETECTION =============

def detect_platform() -> Dict[str, Any]:
    """Detect platform and terminal capabilities."""
    os_name = sys.platform
    env = os.environ

    terminal = env.get('TERM', 'unknown')
    shell = env.get('SHELL', '')

    emoji_support = True
    if os_name == 'win32':
        wt_session = env.get('WT_SESSION')
        ps_version = env.get('PSModulePath')
        if not wt_session and 'WindowsPowerShell' in (ps_version or ''):
            emoji_support = False
        if 'cmd' in shell.lower() or terminal == 'unknown':
            emoji_support = False

    unicode_support = True
    encoding = sys.stdout.encoding or 'utf-8'
    encoding_lower = encoding.lower()

    if 'ascii' in encoding_lower or 'cp' in encoding_lower or 'windows-' in encoding_lower:
        unicode_support = False
        emoji_support = False

    if os_name == 'win32' and 'utf-8' not in encoding_lower:
        emoji_support = False

    ansi_colors = terminal != 'dumb' and os_name != 'win32' or env.get('ANSICON') is not None

    return {
        'os': os_name,
        'terminal': terminal,
        'emoji_support': emoji_support,
        'unicode_support': unicode_support,
        'ansi_colors': ansi_colors,
        'encoding': encoding
    }

PLATFORM_INFO = detect_platform()

# ============= OUTPUT SANITIZATION =============

def sanitize_for_platform(text: str, platform_info: Dict = None) -> str:
    """Sanitize text for current platform."""
    if platform_info is None:
        platform_info = PLATFORM_INFO

    if not isinstance(text, str):
        text = str(text)

    if not platform_info['emoji_support']:
        emoji_map = {
            '🟢': '[*]', '📌': '[PIN]', '✓': '[OK]', '✗': '[X]',
            '🔐': '[VAULT]', '⚠️': '[WARN]', '❌': '[ERR]', '📝': '[NOTE]',
            '🔒': '[LOCK]', '📬': '[MSG]', '⏰': '[TIME]', '📍': '[LOC]',
            '★': '[STAR]', '💡': '[TIP]'
        }
        for emoji, replacement in emoji_map.items():
            text = text.replace(emoji, replacement)

    if not platform_info['unicode_support']:
        # Replace box-drawing characters with ASCII equivalents
        box_drawing_map = {
            '─': '-',  # Horizontal line
            '│': '|',  # Vertical line
            '┌': '+',  # Top-left corner
            '┐': '+',  # Top-right corner
            '└': '+',  # Bottom-left corner
            '┘': '+',  # Bottom-right corner
            '├': '+',  # Left T-junction
            '┤': '+',  # Right T-junction
            '┬': '+',  # Top T-junction
            '┴': '+',  # Bottom T-junction
            '┼': '+',  # Cross
            '═': '=',  # Double horizontal line
            '║': '|',  # Double vertical line
        }
        for box_char, replacement in box_drawing_map.items():
            text = text.replace(box_char, replacement)
        
        # Fallback: replace any remaining non-ASCII with ?
        text = text.encode('ascii', 'replace').decode('ascii')

    return text

def format_output(data: Any, format_type: str = 'pipe', platform_info: Dict = None) -> str:
    """Format output with platform awareness."""
    if format_type == 'json':
        return json.dumps(data, indent=2, ensure_ascii=not (platform_info or PLATFORM_INFO)['unicode_support'])

    elif format_type == 'pipe':
        if isinstance(data, dict):
            if len(data) == 1:
                value = str(list(data.values())[0])
                return sanitize_for_platform(value, platform_info)
            parts = []
            for k, v in data.items():
                if isinstance(v, (list, dict)):
                    v = json.dumps(v)
                parts.append(f"{k}:{v}")
            return sanitize_for_platform('|'.join(parts), platform_info)
        return sanitize_for_platform(str(data), platform_info)

    else:  # text
        if isinstance(data, dict):
            parts = []
            for k, v in data.items():
                parts.append(f"{k}: {v}")
            return sanitize_for_platform('\n'.join(parts), platform_info)
        return sanitize_for_platform(str(data), platform_info)

# ============= ENHANCED TOOL INTROSPECTION =============

class ToolIntrospector:
    """Automatically discover and document tool functions with alias support"""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.module = importlib.import_module(module_name)
        self.functions = {}
        self.aliases = {}  # alias -> primary_name mapping
        self.all_command_names = set()  # For fuzzy matching
        self._discover_functions()
        self._setup_aliases()

    def _discover_functions(self):
        """Find all public functions that look like tool functions

        Functions are automatically excluded if they:
        - Start with underscore (_) - Python convention for private functions
        - Are named 'main' - typically entry points, not API functions
        """
        for name, obj in inspect.getmembers(self.module):
            if not inspect.isfunction(obj):
                continue

            # Skip private functions (Python convention: starts with _)
            if name.startswith('_'):
                continue

            # Skip main function (typically entry point, not an API function)
            if name == 'main':
                continue

            try:
                sig = inspect.signature(obj)
            except:
                continue

            params = {}
            required = []

            for param_name, param in sig.parameters.items():
                if param_name in ['kwargs', 'args']:
                    continue

                param_type = self._infer_type(param)
                param_desc = f"{param_name} parameter"

                params[param_name] = {
                    "type": param_type,
                    "description": param_desc
                }

                if param.default == inspect.Parameter.empty and param_name != 'kwargs':
                    required.append(param_name)

            doc = inspect.getdoc(obj) or f"Execute {name} operation"
            doc_lines = doc.split('\n')
            description = doc_lines[0].strip()

            self.functions[name] = {
                'callable': obj,
                'description': description,
                'params': params,
                'required': required
            }
            self.all_command_names.add(name)

    def _setup_aliases(self):
        """Setup command aliases based on tool and predefined mappings"""
        # Extract tool base name (e.g., 'notebook' from 'notebook_main')
        tool_base = self.module_name.split('_')[0].split('.')[-1]
        
        if tool_base in COMMAND_ALIASES:
            alias_map = COMMAND_ALIASES[tool_base]
            
            for primary_cmd, aliases in alias_map.items():
                if primary_cmd in self.functions:
                    for alias in aliases:
                        self.aliases[alias] = primary_cmd
                        self.all_command_names.add(alias)

    def _infer_type(self, param) -> str:
        """Infer parameter type from annotation or default"""
        if param.annotation != inspect.Parameter.empty:
            ann = param.annotation
            ann_str = str(ann)

            if ann == str or 'str' in ann_str:
                return "string"
            elif ann == int or 'int' in ann_str:
                return "integer"
            elif ann == bool or 'bool' in ann_str:
                return "boolean"
            elif ann == float or 'float' in ann_str:
                return "number"
            elif 'List' in ann_str or 'list' in ann_str:
                return "array"
            elif 'Dict' in ann_str or 'dict' in ann_str:
                return "object"

        if param.default != inspect.Parameter.empty and param.default is not None:
            if isinstance(param.default, str):
                return "string"
            elif isinstance(param.default, int):
                return "integer"
            elif isinstance(param.default, bool):
                return "boolean"
            elif isinstance(param.default, float):
                return "number"
            elif isinstance(param.default, list):
                return "array"
            elif isinstance(param.default, dict):
                return "object"

        return "string"

    def resolve_command(self, name: str) -> Optional[str]:
        """Resolve command name (handle aliases)"""
        if name in self.functions:
            return name
        if name in self.aliases:
            return self.aliases[name]
        return None

    def suggest_commands(self, attempted: str, max_suggestions: int = 3) -> List[Tuple[str, str]]:
        """Suggest similar commands using fuzzy matching."""
        matches = get_close_matches(attempted, self.all_command_names, n=max_suggestions, cutoff=0.6)
        
        suggestions = []
        for match in matches:
            primary = self.resolve_command(match) or match
            if primary in self.functions:
                desc = self.functions[primary]['description']
                suggestions.append((match, desc))
        
        return suggestions

    def get_mcp_schema(self) -> List[Dict]:
        """Generate MCP tool schemas with alias information"""
        schemas = []
        for name, info in self.functions.items():
            aliases = [alias for alias, primary in self.aliases.items() if primary == name]
            
            description = info['description']
            if aliases:
                description += f" (Aliases: {', '.join(aliases)})"
            
            schemas.append({
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": info['params'],
                    "required": info['required'],
                    "additionalProperties": True
                }
            })
        return schemas

    def call(self, function_name: str, **kwargs) -> Any:
        """Call a function by name (resolves aliases) with forgiving input handling"""
        resolved_name = self.resolve_command(function_name)
        
        if not resolved_name:
            suggestions = self.suggest_commands(function_name)
            error_msg = f"Unknown function: '{function_name}'"
            
            if suggestions:
                error_msg += "\n\n💡 Did you mean:"
                for cmd, desc in suggestions:
                    error_msg += f"\n   - {cmd}() - {desc}"
            
            raise ValueError(error_msg)

        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if value == 'null' or value == 'None':
                value = None
            sanitized_kwargs[key] = value

        return self.functions[resolved_name]['callable'](**sanitized_kwargs)

# ============= MCP ADAPTER =============

class MCPAdapter:
    """MCP protocol adapter with logging and enhanced error messages"""

    def __init__(self, tool_module: str, log_file: Optional[str] = None):
        self.introspector = ToolIntrospector(tool_module)
        self.logger = logging.getLogger('mcp_adapter')

        handlers = [logging.StreamHandler(sys.stderr)]
        if log_file:
            handlers.append(logging.FileHandler(log_file))

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [MCP] - %(message)s',
            handlers=handlers
        )

    def run(self):
        """Run MCP server loop"""
        self.logger.info(f"MCP Adapter v1.0.0 starting for {self.introspector.module_name}")
        self.logger.info(f"Platform: {PLATFORM_INFO['os']}, Emoji: {PLATFORM_INFO['emoji_support']}")
        self.logger.info(f"Aliases enabled - {len(self.introspector.aliases)} aliases configured")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                request = json.loads(line)
                request_id = request.get("id")
                method = request.get("method", "")
                params = request.get("params", {})

                response = {"jsonrpc": "2.0", "id": request_id}

                if method == "initialize":
                    response["result"] = {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": self.introspector.module_name,
                            "version": "1.0.0",
                            "description": f"Universal adapter for {self.introspector.module_name}"
                        }
                    }
                    self.logger.info("Initialized MCP connection")

                elif method == "notifications/initialized":
                    continue

                elif method == "tools/list":
                    response["result"] = {
                        "tools": self.introspector.get_mcp_schema()
                    }
                    self.logger.info(f"Listed {len(self.introspector.functions)} tools")

                elif method == "tools/call":
                    tool_name = params.get("name", "")
                    tool_args = params.get("arguments", {})

                    self.logger.info(f"Calling tool: {tool_name}")

                    try:
                        result = self.introspector.call(tool_name, **tool_args)

                        if isinstance(result, dict):
                            text = self._format_result(result)
                        else:
                            text = str(result)

                        text = sanitize_for_platform(text)

                        response["result"] = {
                            "content": [{
                                "type": "text",
                                "text": text
                            }]
                        }
                        self.logger.info(f"Tool {tool_name} succeeded")
                    except Exception as e:
                        self.logger.error(f"Tool {tool_name} error: {e}", exc_info=True)
                        response["result"] = {
                            "content": [{
                                "type": "text",
                                "text": sanitize_for_platform(str(e))
                            }]
                        }

                else:
                    response["result"] = {}

                print(json.dumps(response), flush=True)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}", exc_info=True)
                continue

        self.logger.info("MCP Adapter shutting down")

    def _format_result(self, result: Dict) -> str:
        """Format result dict as readable text"""
        if "error" in result:
            return f"Error: {result['error']}"
        elif len(result) == 1:
            key, value = list(result.items())[0]
            if isinstance(value, list):
                return '\n'.join(str(v) for v in value)
            return str(value)
        else:
            return format_output(result, 'text')

# ============= CLI ADAPTER =============

class CLIAdapter:
    """CLI interface adapter with alias support and enhanced errors"""

    def __init__(self, tool_module: str):
        self.introspector = ToolIntrospector(tool_module)

    def run(self, command: str, args: Dict[str, Any]):
        """Execute CLI command"""
        try:
            result = self.introspector.call(command, **args)

            if isinstance(result, dict):
                if "error" in result:
                    error_msg = sanitize_for_platform(f"Error: {result['error']}")
                    print(error_msg, file=sys.stderr)
                    sys.exit(1)
                else:
                    output = format_output(result, 'json' if args.get('json') else 'text')
                    print(output)
            else:
                print(sanitize_for_platform(str(result)))

        except Exception as e:
            error_msg = sanitize_for_platform(str(e))
            print(error_msg, file=sys.stderr)
            sys.exit(1)

    def list_commands(self):
        """List available commands with aliases"""
        print(f"Available commands for {self.introspector.module_name}:\n")

        for name, info in sorted(self.introspector.functions.items()):
            # Find aliases for this command
            aliases = [alias for alias, primary in self.introspector.aliases.items() if primary == name]
            
            print(f"  {name}")
            if aliases:
                print(f"    Aliases: {', '.join(aliases)}")
            desc = sanitize_for_platform(f"    {info['description']}")
            print(desc)

            if info['params']:
                print("    Parameters:")
                for param_name, param_info in info['params'].items():
                    required = " (required)" if param_name in info['required'] else ""
                    param_line = f"      --{param_name} ({param_info['type']}){required}"
                    print(sanitize_for_platform(param_line))
            print()

# ============= HTTP ADAPTER =============

class HTTPAdapter:
    """HTTP REST API adapter with rate limiting"""

    def __init__(self, tool_module: str, port: int = 8080, log_file: Optional[str] = None):
        self.introspector = ToolIntrospector(tool_module)
        self.port = port
        self.rate_limit = defaultdict(list)
        self.max_requests_per_minute = 60

        self.logger = logging.getLogger('http_adapter')
        handlers = [logging.StreamHandler()]
        if log_file:
            handlers.append(logging.FileHandler(log_file))

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [HTTP] - %(message)s',
            handlers=handlers
        )

    def check_rate_limit(self, client_ip: str) -> bool:
        """Check if client is within rate limits"""
        now = time.time()
        minute_ago = now - 60

        self.rate_limit[client_ip] = [t for t in self.rate_limit[client_ip] if t > minute_ago]

        if len(self.rate_limit[client_ip]) >= self.max_requests_per_minute:
            return False

        self.rate_limit[client_ip].append(now)
        return True

    def run(self):
        """Run HTTP server"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler

            introspector = self.introspector
            adapter = self

            class ToolHandler(BaseHTTPRequestHandler):
                def do_OPTIONS(self):
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()

                def do_GET(self):
                    self.send_header('Access-Control-Allow-Origin', '*')

                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()

                        response = {
                            'name': introspector.module_name,
                            'version': '1.0.0',
                            'platform': PLATFORM_INFO['os'],
                            'aliases_enabled': len(introspector.aliases),
                            'tools': list(introspector.functions.keys()),
                            'endpoints': {
                                'GET /': 'API info',
                                'GET /tools': 'Tool schemas',
                                'POST /call/{tool_name}': 'Execute tool',
                                'GET /health': 'Health check'
                            }
                        }
                        self.wfile.write(json.dumps(response, indent=2).encode())

                    elif self.path == '/tools':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()

                        schemas = introspector.get_mcp_schema()
                        self.wfile.write(json.dumps(schemas, indent=2).encode())

                    elif self.path == '/health':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()

                        health = {
                            'status': 'healthy',
                            'timestamp': datetime.now().isoformat(),
                            'tools_loaded': len(introspector.functions)
                        }
                        self.wfile.write(json.dumps(health).encode())

                    else:
                        self.send_error(404, "Endpoint not found")

                def do_POST(self):
                    client_ip = self.client_address[0]
                    if not adapter.check_rate_limit(client_ip):
                        self.send_response(429)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        error = {'error': 'Rate limit exceeded'}
                        self.wfile.write(json.dumps(error).encode())
                        return

                    if not self.path.startswith('/call/'):
                        self.send_error(404, "Endpoint not found")
                        return

                    tool_name = self.path[6:]

                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)

                    try:
                        args = json.loads(body) if body else {}
                    except json.JSONDecodeError:
                        self.send_error(400, "Invalid JSON")
                        return

                    try:
                        adapter.logger.info(f"HTTP call: {tool_name} from {client_ip}")
                        result = introspector.call(tool_name, **args)

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()

                        response = {
                            'tool': tool_name,
                            'timestamp': datetime.now().isoformat(),
                            'result': result
                        }
                        self.wfile.write(json.dumps(response, indent=2).encode())

                    except Exception as e:
                        adapter.logger.error(f"Tool error: {e}")
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()

                        error_response = {
                            'error': str(e),
                            'tool': tool_name,
                            'timestamp': datetime.now().isoformat()
                        }
                        self.wfile.write(json.dumps(error_response).encode())

                def log_message(self, format, *args):
                    adapter.logger.info(f"{self.address_string()} - {format % args}")

            print(f"HTTP Adapter v1.0.0 starting for {self.introspector.module_name}")
            print(f"Platform: {PLATFORM_INFO['os']}, Aliases: {len(self.introspector.aliases)}")
            print(f"Listening on http://0.0.0.0:{self.port}")
            print(f"\nEndpoints:")
            print(f"  GET  http://localhost:{self.port}/")
            print(f"  GET  http://localhost:{self.port}/tools")
            print(f"  POST http://localhost:{self.port}/call/{{tool_name}}")

            server = HTTPServer(('0.0.0.0', self.port), ToolHandler)
            server.serve_forever()

        except Exception as e:
            print(f"HTTP server error: {e}", file=sys.stderr)
            sys.exit(1)

# ============= MAIN ENTRY POINT =============

def main():
    parser = argparse.ArgumentParser(
        description='Universal Adapter v1.0.0 - Production-grade multi-protocol bridge',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('mode', choices=['mcp', 'cli', 'http'],
                       help='Adapter mode')
    parser.add_argument('--tool', required=True,
                       help='Tool module name')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port for HTTP mode')
    parser.add_argument('--log', type=str,
                       help='Log file path')
    parser.add_argument('--list', action='store_true',
                       help='List available commands')
    parser.add_argument('--json', action='store_true',
                       help='JSON output')

    args, remaining = parser.parse_known_args()

    if args.mode == 'mcp':
        adapter = MCPAdapter(args.tool, args.log)
        adapter.run()

    elif args.mode == 'cli':
        adapter = CLIAdapter(args.tool)

        if args.list:
            adapter.list_commands()
        elif remaining:
            command = remaining[0]
            cmd_args = {'json': args.json}
            i = 1
            while i < len(remaining):
                if remaining[i].startswith('--'):
                    key = remaining[i][2:]
                    if i + 1 < len(remaining) and not remaining[i + 1].startswith('--'):
                        value = remaining[i + 1]
                        i += 2
                    else:
                        value = True
                        i += 1
                    cmd_args[key] = value
                else:
                    i += 1

            adapter.run(command, cmd_args)
        else:
            print("Error: No command specified", file=sys.stderr)
            print("Use --list to see available commands", file=sys.stderr)
            sys.exit(1)

    elif args.mode == 'http':
        adapter = HTTPAdapter(args.tool, args.port, args.log)
        adapter.run()

if __name__ == '__main__':
    main()
