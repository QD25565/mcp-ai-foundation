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

def get_tool_data_dir(tool_name: str) -> Path:
    """Get data directory for specific tool"""
    tool_dir = BASE_DATA_DIR / f"{tool_name}_data"
    tool_dir.mkdir(parents=True, exist_ok=True)
    return tool_dir

# ============= LOGGING SETUP =============
def setup_logging(tool_name: str, level=logging.INFO):
    """Configure logging to stderr only (MCP requirement)"""
    logging.basicConfig(
        level=level,
        format=f'%(asctime)s - [{tool_name}] - %(message)s',
        stream=sys.stderr
    )
    return logging.getLogger(tool_name)

# ============= AI IDENTITY MANAGEMENT =============
def get_persistent_id() -> str:
    """Get or create persistent AI identity across all tools"""
    # Check multiple locations for existing ID
    search_locations = [
        Path(__file__).parent / "ai_identity.txt",
        BASE_DATA_DIR / "ai_identity.txt",
        Path.home() / "ai_identity.txt"
    ]
    
    for id_file in search_locations:
        if id_file.exists():
            try:
                with open(id_file, 'r') as f:
                    stored_id = f.read().strip()
                    if stored_id:
                        return stored_id
            except:
                pass
    
    # Generate new ID
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep', 'Keen', 'Pure']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node', 'Wave', 'Link']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    # Save to script directory
    try:
        id_file = Path(__file__).parent / "ai_identity.txt"
        with open(id_file, 'w') as f:
            f.write(new_id)
    except:
        pass
    
    return new_id

# Get AI ID from environment or persistent storage
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

# ============= PARAMETER NORMALIZATION =============
def normalize_param(value: Any) -> Any:
    """Normalize parameter values - convert string 'null' to None for forgiving tool calls"""
    if value == 'null' or value == 'None':
        return None
    return value

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

def create_tool_response(content: str) -> Dict:
    """Create standard tool response format"""
    return {
        "content": [{
            "type": "text",
            "text": content
        }]
    }

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
        
        try:
            if self.op_file.exists():
                with open(self.op_file, 'r') as f:
                    data = json.load(f)
                    return {
                        'type': data['type'],
                        'time': datetime.fromisoformat(data['time'])
                    }
        except:
            pass
        
        return None
