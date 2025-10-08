#!/usr/bin/env python3
"""
AI FOUNDATION MCP SERVER v1.0.0
================================
Unified MCP server exposing ALL AI Foundation tools through a single endpoint.

This server provides:
- Notebook (personal memory & search)
- Teambook (multi-AI collaboration)
- Task Manager (task tracking & completion)
- World (time, location, context)

ONE SERVER. ONE CONFIG. ALL TOOLS.

Usage:
    Configure in Claude Desktop config:
    {
      "mcpServers": {
        "ai-foundation": {
          "command": "python",
          "args": ["/path/to/ai_foundation_server.py"]
        }
      }
    }

Architecture:
    Uses universal_adapter.py for automatic tool introspection.
    Each tool module (notebook_main, teambook_api, etc.) is automatically
    discovered and exposed through MCP.
"""

import os
# Set MCP mode flag for execution context detection
os.environ['MCP_SERVER_MODE'] = 'true'

import asyncio
import logging
import json
import sys
from typing import Any, Dict, List
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - [AI-Foundation] - %(message)s'
)
logger = logging.getLogger("ai-foundation")

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    import mcp.server.stdio
except ImportError:
    print("ERROR: MCP library not installed", file=sys.stderr)
    print("Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Import tool APIs
try:
    from notebook import notebook_main as notebook
    from teambook import teambook_api as teambook
    import task_manager
    import world
except ImportError as e:
    print(f"ERROR: Failed to import tool modules: {e}", file=sys.stderr)
    print("Make sure all tool files are in the same directory", file=sys.stderr)
    sys.exit(1)

# Version
VERSION = "1.0.0"

# Create MCP server
app = Server("ai-foundation")

# ============================================================================
# TOOL DISCOVERY & REGISTRATION
# ============================================================================

class ToolRegistry:
    """
    Discovers and registers all tools from imported modules.
    
    Automatically finds public functions and generates MCP tool schemas.
    """
    
    def __init__(self):
        self.tools = {}
        self._discover_tools()
    
    def _discover_tools(self):
        """Discover all public functions from tool modules"""
        
        # Define tool modules and their prefixes
        modules = [
            (notebook, "notebook"),
            (teambook, "teambook"),
            (task_manager, "task"),
            (world, "world")
        ]
        
        skip_functions = {
            'main', 'init_db', 'get_db_conn', 'init_embedding_model',
            'init_vector_db', 'init_vault_manager', 'normalize_param',
            'pipe_escape', 'clean_text', 'format_time_compact', 
            'simple_summary', 'handle_tools_call'
        }
        
        for module, prefix in modules:
            # Get all public functions
            for name in dir(module):
                if name.startswith('_') or name in skip_functions:
                    continue
                
                obj = getattr(module, name)
                if not callable(obj):
                    continue
                
                # Get function info
                try:
                    import inspect
                    sig = inspect.signature(obj)
                    doc = inspect.getdoc(obj) or f"Execute {name} operation"
                    
                    # Extract first line of docstring for description
                    description = doc.split('\n')[0].strip()
                    
                    # Build parameter schema
                    params = {}
                    required = []
                    
                    for param_name, param in sig.parameters.items():
                        if param_name in ['kwargs', 'args']:
                            continue
                        
                        # Infer type
                        param_type = self._infer_type(param)
                        
                        params[param_name] = {
                            "type": param_type,
                            "description": f"{param_name} parameter"
                        }
                        
                        if param.default == inspect.Parameter.empty:
                            required.append(param_name)
                    
                    # Register tool with prefix (MCP compliant: underscores only)
                    tool_name = f"{prefix}_{name}"
                    self.tools[tool_name] = {
                        'callable': obj,
                        'description': description,
                        'params': params,
                        'required': required,
                        'module': prefix
                    }
                    
                except Exception as e:
                    logger.warning(f"Failed to register {name}: {e}")
                    continue
        
        logger.info(f"Registered {len(self.tools)} tools across {len(modules)} modules")
    
    def _infer_type(self, param) -> str:
        """Infer parameter type from annotation or default"""
        import inspect
        
        # Check annotation
        if param.annotation != inspect.Parameter.empty:
            ann = str(param.annotation)
            if 'str' in ann:
                return "string"
            elif 'int' in ann:
                return "integer"
            elif 'bool' in ann:
                return "boolean"
            elif 'float' in ann:
                return "number"
            elif 'List' in ann or 'list' in ann:
                return "array"
            elif 'Dict' in ann or 'dict' in ann:
                return "object"
        
        # Check default value
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
        
        return "string"  # Default
    
    def get_mcp_schemas(self) -> List[Dict]:
        """Generate MCP tool schemas"""
        schemas = []
        for name, info in self.tools.items():
            schemas.append({
                "name": name,
                "description": info['description'],
                "inputSchema": {
                    "type": "object",
                    "properties": info['params'],
                    "required": info['required'],
                    "additionalProperties": True
                }
            })
        return schemas
    
    def call(self, tool_name: str, arguments: Dict) -> Any:
        """Call a tool by name"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return self.tools[tool_name]['callable'](**arguments)

# Initialize registry
registry = ToolRegistry()

# ============================================================================
# MCP HANDLERS
# ============================================================================

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools"""
    schemas = registry.get_mcp_schemas()
    return [
        Tool(
            name=schema["name"],
            description=schema["description"],
            inputSchema=schema["inputSchema"]
        )
        for schema in schemas
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls"""
    try:
        logger.info(f"Calling tool: {name}")
        
        # Call the tool
        result = registry.call(name, arguments or {})
        
        # Format result
        if isinstance(result, dict):
            text = json.dumps(result, indent=2)
        else:
            text = str(result)
        
        return [TextContent(type="text", text=text)]
        
    except Exception as e:
        logger.error(f"Tool {name} error: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]

# ============================================================================
# SERVER LIFECYCLE
# ============================================================================

async def main():
    """Run the unified MCP server"""
    logger.info(f"AI Foundation MCP Server v{VERSION} starting...")
    logger.info(f"Loaded {len(registry.tools)} tools")
    
    # Log tool counts by module
    module_counts = {}
    for tool_name in registry.tools.keys():
        module = tool_name.split('_')[0]
        module_counts[module] = module_counts.get(module, 0) + 1
    
    for module, count in sorted(module_counts.items()):
        logger.info(f"  - {module}: {count} tools")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
