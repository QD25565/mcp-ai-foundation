#!/usr/bin/env python3
"""
MCP Shared Utilities v1.0.0
============================
Common utilities for all MCP tools to reduce boilerplate and ensure consistency.
Provides: identity management, logging, data paths, formatting, and server helpers.
"""

import os
import sys
import json
import random
import re
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# ============= VERSION & CONFIGURATION =============
MCP_SHARED_VERSION = "1.0.0"

# ============= CROSS-PLATFORM DATA DIRECTORY =============
def get_base_data_dir() -> Path:
    """Get cross-platform base directory for all MCP tools"""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "Claude" / "tools"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Claude" / "tools"
    else:
        base = Path.home() / ".claude" / "tools"
    
    # Allow override via environment
    if 'MCP_DATA_DIR' in os.environ:
        base = Path(os.environ['MCP_DATA_DIR'])
    
    base.mkdir(parents=True, exist_ok=True)
    return base

BASE_DATA_DIR = get_base_data_dir()

def _get_tool_data_dir(tool_name: str) -> Path:
    """Get data directory for specific tool (internal)"""
    tool_dir = BASE_DATA_DIR / f"{tool_name}_data"
    tool_dir.mkdir(parents=True, exist_ok=True)
    return tool_dir

# Keep public alias for backwards compatibility
def get_tool_data_dir(tool_name: str) -> Path:
    """Get data directory for specific tool"""
    return _get_tool_data_dir(tool_name)

# ============= LOGGING SETUP =============
def setup_logging(tool_name: str, level=logging.WARNING):
    """Configure logging to stderr only (MCP requirement)

    Default level is WARNING to reduce noise in normal operation.
    Set level=logging.INFO or logging.DEBUG for verbose output.
    """
    logging.basicConfig(
        level=level,
        format=f'%(asctime)s - [{tool_name}] - %(message)s',
        stream=sys.stderr
    )
    return logging.getLogger(tool_name)

# ============= AI IDENTITY MANAGEMENT =============
def get_persistent_id() -> str:
    """
    Get or create persistent AI identity across all tools

    SECURITY NOTE: This ID is for organization/logging, not authentication.
    If an attacker modifies the identity file, they can only change the displayed name,
    not gain elevated privileges. For authentication, use environment variables or
    proper authentication tokens.
    """
    # Check multiple locations for existing ID
    search_locations = [
        Path(__file__).parent / "ai_identity.txt",
        BASE_DATA_DIR / "ai_identity.txt",
        Path.home() / "ai_identity.txt"
    ]

    # SECURITY FIX: Avoid TOCTOU race condition - try to open directly instead of checking exists first
    for id_file in search_locations:
        try:
            with open(id_file, 'r') as f:
                stored_id = f.read().strip()

                # SECURITY: Validate identity format to detect tampering
                # Expected format: Word-Word-Number (e.g., "Swift-Mind-123")
                if stored_id and re.match(r'^[A-Za-z]+-[A-Za-z]+-\d{3}$', stored_id):
                    return stored_id
                elif stored_id:
                    # Invalid format detected - possible tampering
                    logging.warning(f"AI identity file has invalid format: {id_file}")
        except FileNotFoundError:
            pass  # File doesn't exist, try next location
        except Exception as e:
            logging.warning(f"Error reading identity file {id_file}: {e}")
            pass  # Other errors, try next location

    # Generate new ID
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep', 'Keen', 'Pure']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node', 'Wave', 'Link']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"

    # Save to script directory with restrictive permissions
    # SECURITY: Use secure file creation with permissions set atomically
    try:
        id_file = Path(__file__).parent / "ai_identity.txt"

        # SECURITY: Open file with 0o600 permissions from the start
        # This prevents race conditions where file is created with default
        # permissions and then chmod'd later
        fd = os.open(id_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, new_id.encode('utf-8'))
        finally:
            os.close(fd)

        # Verify permissions (belt and suspenders)
        import stat
        file_stat = os.stat(id_file)
        if file_stat.st_mode & 0o777 != (stat.S_IRUSR | stat.S_IWUSR):
            logging.warning(f"AI identity file permissions may be incorrect")
    except Exception as e:
        logging.warning(f"Could not save AI identity: {e}")
        pass

    return new_id

# Get AI ID from environment or persistent storage
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

# ============= PARAMETER NORMALIZATION =============
def _normalize_param(value: Any) -> Any:
    """Normalize parameter values - convert string 'null' to None for forgiving tool calls (internal)"""
    if value == 'null' or value == 'None':
        return None
    return value

# Keep public alias for backwards compatibility
def normalize_param(value: Any) -> Any:
    """Normalize parameter values - convert string 'null' to None for forgiving tool calls"""
    return _normalize_param(value)

# ============= OUTPUT FORMATTING =============
def pipe_escape(text: str) -> str:
    """Escape pipes in text for pipe format"""
    return str(text).replace('|', '\\|')

def format_output(data: Dict[str, Any], format_type: str = 'pipe') -> str:
    """Format output data according to specified format"""
    if format_type == 'json':
        return json.dumps(data)
    elif format_type == 'pipe':
        # Simple pipe format for single values
        if len(data) == 1:
            return pipe_escape(str(list(data.values())[0]))
        # Multiple values
        parts = [f"{k}:{pipe_escape(str(v))}" for k, v in data.items()]
        return '|'.join(parts)
    else:
        # Text format
        return ' | '.join(f"{k}: {v}" for k, v in data.items())

# ============= MCP SERVER HELPERS =============
def create_mcp_response(request_id: Any, result: Any = None, error: Any = None) -> Dict:
    """Create standard MCP JSON-RPC response"""
    response = {"jsonrpc": "2.0", "id": request_id}
    if error:
        response["error"] = error
    else:
        response["result"] = result
    return response

def _create_tool_response(content: str) -> Dict:
    """Create standard tool response format (internal)"""
    return {
        "content": [{
            "type": "text",
            "text": content
        }]
    }

# Keep public alias for backwards compatibility
def create_tool_response(content: str) -> Dict:
    """Create standard tool response format"""
    return _create_tool_response(content)

def send_response(response: Dict):
    """Send JSON-RPC response to stdout"""
    print(json.dumps(response), flush=True)

def create_server_info(name: str, version: str, description: str) -> Dict:
    """Create standard server info for initialization"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {
            "name": name,
            "version": version,
            "description": description
        }
    }

def create_tool_schema(name: str, description: str, properties: Dict, required: list = None) -> Dict:
    """Create standard tool schema"""
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": True
        }
    }

# ============= SERVER LOOP HELPER =============
class MCPServer:
    """Base MCP server class with standard loop handling"""
    
    def __init__(self, name: str, version: str, description: str):
        self.name = name
        self.version = version
        self.description = description
        self.logger = setup_logging(name)
        self.tools = {}
        self.running = True
    
    def register_tool(self, tool_func, name: str, description: str, 
                     properties: Dict, required: list = None):
        """Register a tool handler"""
        self.tools[name] = {
            'func': tool_func,
            'schema': create_tool_schema(name, description, properties, required)
        }
    
    def handle_initialize(self, params: Dict) -> Dict:
        """Handle initialization request"""
        return create_server_info(self.name, self.version, self.description)
    
    def handle_tools_list(self, params: Dict) -> Dict:
        """Handle tools list request"""
        return {
            "tools": [tool['schema'] for tool in self.tools.values()]
        }
    
    def handle_tools_call(self, params: Dict) -> Dict:
        """Handle tool call request"""
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return create_tool_response(f"Error: Unknown tool '{tool_name}'")
        
        try:
            result = self.tools[tool_name]['func'](**tool_args)
            # Format result as text
            if isinstance(result, dict):
                if "error" in result:
                    text = f"Error: {result['error']}"
                else:
                    # Tool-specific formatting
                    text = self.format_tool_result(tool_name, result)
            else:
                text = str(result)
            
            return create_tool_response(text)
        except Exception as e:
            self.logger.error(f"Tool error: {e}", exc_info=True)
            return create_tool_response(f"Error: {str(e)}")
    
    def format_tool_result(self, tool_name: str, result: Dict) -> str:
        """Format tool result - override in subclass for custom formatting"""
        # Default formatting
        if len(result) == 1:
            return str(list(result.values())[0])
        return json.dumps(result)
    
    def run(self):
        """Main server loop"""
        self.logger.info(f"{self.name} v{self.version} starting...")
        self.logger.info(f"Identity: {CURRENT_AI_ID}")
        
        while self.running:
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
                
                # Route method
                if method == "initialize":
                    result = self.handle_initialize(params)
                    send_response(create_mcp_response(request_id, result))
                
                elif method == "notifications/initialized":
                    continue
                
                elif method == "tools/list":
                    result = self.handle_tools_list(params)
                    send_response(create_mcp_response(request_id, result))
                
                elif method == "tools/call":
                    result = self.handle_tools_call(params)
                    send_response(create_mcp_response(request_id, result))
                
                else:
                    send_response(create_mcp_response(request_id, {}))
            
            except KeyboardInterrupt:
                self.logger.info("Shutdown requested")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}", exc_info=True)
                if 'request_id' in locals():
                    send_response(create_mcp_response(
                        request_id, 
                        error={"code": -32603, "message": str(e)}
                    ))
        
        self.logger.info(f"{self.name} shutting down")

# ============= TIME UTILITIES =============
def format_time_compact(dt: datetime) -> str:
    """Format datetime compactly for display"""
    if not dt:
        return "unknown"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt[:10]
    
    now = datetime.now(timezone.utc)
    # Ensure dt is timezone-aware for comparison
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    
    if delta.total_seconds() < 60:
        return "now"
    elif delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds()/60)}m"
    elif dt.date() == now.date():
        return dt.strftime("%H:%M")
    elif delta.days == 1:
        return f"yesterday {dt.strftime('%H:%M')}"
    elif delta.days < 7:
        return f"{delta.days}d ago"
    else:
        return dt.strftime("%Y-%m-%d")

# ============= AI-FOCUSED RATE LIMITING =============
class AIRateLimiter:
    """
    Rate limiter designed for AI behavior patterns.
    Prevents: runaway loops, error cascades, infinite retries.
    NOT designed for human abuse prevention - these are AI-only tools.
    """

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.data_dir = get_tool_data_dir(tool_name)
        self.state_file = self.data_dir / ".rate_limit_state"

        # Limits tuned for AI usage
        self.max_calls_per_second = 10    # Prevent tight loops
        self.max_calls_per_minute = 100   # Prevent runaway operations
        self.max_errors_per_minute = 20   # Detect error cascades

        # State
        self.recent_calls = []    # [(timestamp, success)]
        self.load_state()

    def load_state(self):
        """Load rate limit state"""
        # SECURITY FIX: Avoid TOCTOU - try to open directly
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                # Only keep recent data (last 5 minutes)
                cutoff = datetime.now().timestamp() - 300
                self.recent_calls = [(ts, success) for ts, success in data.get('calls', [])
                                    if ts > cutoff]
        except FileNotFoundError:
            self.recent_calls = []  # File doesn't exist yet
        except Exception:
            self.recent_calls = []  # Corrupted or other error

    def save_state(self):
        """Save rate limit state"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({'calls': self.recent_calls}, f)
        except:
            pass

    def check_and_record(self, success: bool = True) -> tuple[bool, Optional[str]]:
        """
        Check rate limits and record call.
        Returns: (allowed: bool, reason: Optional[str])
        """
        now = datetime.now().timestamp()

        # Clean old calls (older than 1 minute)
        cutoff_minute = now - 60
        cutoff_second = now - 1
        self.recent_calls = [(ts, s) for ts, s in self.recent_calls if ts > cutoff_minute]

        # Check per-second limit
        calls_last_second = sum(1 for ts, _ in self.recent_calls if ts > cutoff_second)
        if calls_last_second >= self.max_calls_per_second:
            return False, f"Rate limit: {self.max_calls_per_second} calls/sec (runaway loop?)"

        # Check per-minute limit
        calls_last_minute = len(self.recent_calls)
        if calls_last_minute >= self.max_calls_per_minute:
            return False, f"Rate limit: {self.max_calls_per_minute} calls/min (excessive usage)"

        # Check error rate
        errors_last_minute = sum(1 for _, s in self.recent_calls if not s)
        if errors_last_minute >= self.max_errors_per_minute:
            return False, f"Error cascade detected: {errors_last_minute} errors/min"

        # Record this call
        self.recent_calls.append((now, success))
        self.save_state()

        return True, None

    def get_stats(self) -> Dict:
        """Get current rate limit statistics"""
        now = datetime.now().timestamp()
        cutoff_minute = now - 60
        cutoff_second = now - 1

        recent = [(ts, s) for ts, s in self.recent_calls if ts > cutoff_minute]
        calls_per_second = sum(1 for ts, _ in recent if ts > cutoff_second)
        calls_per_minute = len(recent)
        errors_per_minute = sum(1 for _, s in recent if not s)

        return {
            'calls_per_second': calls_per_second,
            'calls_per_minute': calls_per_minute,
            'errors_per_minute': errors_per_minute,
            'limits': {
                'max_per_second': self.max_calls_per_second,
                'max_per_minute': self.max_calls_per_minute,
                'max_errors': self.max_errors_per_minute
            }
        }

# ============= OPERATION TRACKING =============
class OperationTracker:
    """Track last operation for tool chaining"""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.data_dir = get_tool_data_dir(tool_name)
        self.op_file = self.data_dir / ".last_operation"
        self.last_op = None

    def save(self, op_type: str, result: Any):
        """Save operation"""
        self.last_op = {
            'type': op_type,
            'result': result,
            'time': datetime.now()
        }
        try:
            with open(self.op_file, 'w') as f:
                json.dump({
                    'type': op_type,
                    'time': self.last_op['time'].isoformat()
                }, f)
        except:
            pass

    def get(self) -> Optional[Dict]:
        """Get last operation"""
        if self.last_op:
            return self.last_op

        # SECURITY FIX: Avoid TOCTOU - try to open directly
        try:
            with open(self.op_file, 'r') as f:
                data = json.load(f)
                return {
                    'type': data['type'],
                    'time': datetime.fromisoformat(data['time'])
                }
        except FileNotFoundError:
            return None  # File doesn't exist
        except Exception:
            return None  # Corrupted or other error
