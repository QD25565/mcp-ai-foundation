#!/usr/bin/env python3
"""
Teambook v6.0 MCP Server
========================
MCP interface for Teambook - enables use in Claude Desktop.
Token-efficient, self-evident operations.
"""

import json
import sys
import logging
from typing import Dict, List, Any

from .config import VERSION, CURRENT_AI_ID
from .core import TeamBook
from .models import format_time_compact, smart_truncate

# Configure logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stderr
)


class TeamBookMCP:
    """MCP Server for Teambook"""
    
    def __init__(self):
        """Initialize MCP server"""
        self.tb = TeamBook()
        logging.info(f"Teambook v{VERSION} MCP starting")
        logging.info(f"Identity: {CURRENT_AI_ID}")
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})
        
        response = {"jsonrpc": "2.0", "id": request_id}
        
        if method == "initialize":
            response["result"] = self._handle_initialize()
        
        elif method == "tools/list":
            response["result"] = self._handle_tools_list()
        
        elif method == "tools/call":
            response["result"] = self._handle_tools_call(params)
        
        elif method == "notifications/initialized":
            # No response needed for notifications
            return None
        
        else:
            response["result"] = {}
        
        return response
    
    def _handle_initialize(self) -> Dict:
        """Handle initialization request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "teambook",
                "version": VERSION,
                "description": "AI collaboration primitive - 11 core operations"
            }
        }
    
    def _handle_tools_list(self) -> Dict:
        """List available tools"""
        return {
            "tools": [
                # === Core Writing/Reading ===
                {
                    "name": "write",
                    "description": "Share anything with team (auto-detects tasks/decisions)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"}
                        },
                        "required": ["content"]
                    }
                },
                {
                    "name": "read",
                    "description": "View team activity - summary by default, full with parameter",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "full": {"type": "boolean"}
                        }
                    }
                },
                
                # === Specific Operations ===
                {
                    "name": "get",
                    "description": "Get full entry with all comments (accepts: full ID, numeric position, or partial ID)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Entry ID (flexible: 'tb_123...', '2', 'k58bf0')"}
                        },
                        "required": ["id"]
                    }
                },
                {
                    "name": "comment",
                    "description": "Add comment to any entry",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "content": {"type": "string"}
                        },
                        "required": ["id", "content"]
                    }
                },
                {
                    "name": "claim",
                    "description": "Claim an unclaimed task (accepts flexible ID formats)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Task ID (flexible: full, numeric, or partial)"}
                        },
                        "required": ["id"]
                    }
                },
                {
                    "name": "complete",
                    "description": "Complete a task with optional evidence",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Task ID (flexible format)"},
                            "evidence": {"type": "string", "description": "Optional completion evidence"}
                        },
                        "required": ["id"]
                    }
                },
                {
                    "name": "update",
                    "description": "Update entry content, type, or priority",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"}
                        },
                        "required": ["id"]
                    }
                },
                {
                    "name": "archive",
                    "description": "Archive entry (safe removal)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"}
                        },
                        "required": ["id"]
                    }
                },
                
                # === Team Overview ===
                {
                    "name": "status",
                    "description": "Get team pulse",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "projects",
                    "description": "List available teambook projects",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                
                # === Advanced ===
                {
                    "name": "batch",
                    "description": "Execute multiple operations efficiently",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "operations": {"type": "array"}
                        },
                        "required": ["operations"]
                    }
                },
                {
                    "name": "view_conflicts",
                    "description": "View pending sync conflicts",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "resolve_conflict",
                    "description": "Resolve a sync conflict",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "conflict_id": {"type": "integer"}
                        },
                        "required": ["conflict_id"]
                    }
                },
                {
                    "name": "get_my_key",
                    "description": "Get my public key to share with other AIs",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        }
    
    def _handle_tools_call(self, params: Dict) -> Dict:
        """Handle tool call"""
        tool_name = params.get("name", "").lower().strip()
        tool_args = params.get("arguments", {})
        
        # Map high-level operations to primitives
        try:
            if tool_name == "write":
                # Auto-detect and create entry
                content = tool_args.get("content", "")
                result = self.tb.put(content)
                
                if "error" in result:
                    return self._format_error(result["error"])
                
                return self._format_response(f"{result['id']} {result['msg']}")
            
            elif tool_name == "read":
                # Query with summary or full mode
                full = tool_args.get("full", False)
                filter_dict = {"mode": "full" if full else "summary"}
                
                results = self.tb.query(filter_dict)
                
                if not results:
                    return self._format_response("No entries yet")
                
                if full:
                    # Full listing
                    lines = []
                    for r in results[:20]:  # Limit to 20 for readability
                        lines.append(r["formatted"])
                    
                    if len(results) > 20:
                        lines.append(f"+{len(results)-20} more")
                    
                    return self._format_response("\n".join(lines))
                else:
                    # Summary mode
                    return self._format_response(results[0]["summary"])
            
            elif tool_name == "get":
                # Get full entry
                entry_id = tool_args.get("id")
                if not entry_id:
                    return self._format_error("id required")
                
                # Use flexible ID resolution
                result = self.tb.get(str(entry_id))
                
                # Check for error in result
                if isinstance(result, dict) and "error" in result:
                    return self._format_error(result["error"])
                
                if not result:
                    return self._format_error(f"entry {entry_id} not found")
                
                # Format full entry
                lines = [result["formatted"]]
                
                if result.get("notes"):
                    lines.append(f"Notes: {len(result['notes'])}")
                    for note_id in result["notes"][:3]:
                        lines.append(f"  {note_id}")
                
                if result.get("links"):
                    lines.append(f"Links: {', '.join(result['links'][:5])}")
                
                return self._format_response("\n".join(lines))
            
            elif tool_name == "comment":
                # Add comment (note)
                entry_id = tool_args.get("id")
                content = tool_args.get("content", "")
                
                # Use flexible ID resolution
                result = self.tb.note(str(entry_id), content, "comment")
                
                if "error" in result:
                    return self._format_error(result["error"])
                
                return self._format_response(f"{result['id']} {result['msg']}")
            
            elif tool_name == "claim":
                # Claim task
                entry_id = tool_args.get("id")
                
                # Use flexible ID resolution
                result = self.tb.claim(str(entry_id))
                
                if "error" in result:
                    return self._format_error(result["error"])
                
                return self._format_response(f"claimed {result['id']}")
            
            elif tool_name == "complete":
                # Complete task
                entry_id = tool_args.get("id")
                evidence = tool_args.get("evidence", "")
                
                # Use flexible ID resolution
                result = self.tb.done(str(entry_id), evidence)
                
                if "error" in result:
                    return self._format_error(result["error"])
                
                msg = f"{result['id']} done {result['duration']}"
                if result.get("result"):
                    msg += f" - {result['result']}"
                
                return self._format_response(msg)
            
            elif tool_name == "status":
                # Get team status
                stats = self.tb.db.get_stats()
                
                lines = []
                
                # Task summary
                if stats['tasks']['pending'] > 0:
                    lines.append(f"Pending tasks {stats['tasks']['pending']}")
                if stats['tasks']['claimed'] > 0:
                    lines.append(f"Claimed {stats['tasks']['claimed']}")
                if stats['tasks']['done'] > 0:
                    lines.append(f"Done today {stats['tasks']['done']}")
                
                # Latest activity
                if stats['latest']:
                    lines.append(f"Latest {format_time_compact(stats['latest'])}")
                
                return self._format_response("\n".join(lines) if lines else "No activity")
            
            elif tool_name == "get_my_key":
                # Get crypto identity
                if self.tb.crypto:
                    info = self.tb.crypto.get_identity_info()
                    lines = [
                        f"AI: {info['ai_id']}",
                        f"Key: {info['public_key'][:20]}...",
                        f"Algorithm: {info['algorithm']}"
                    ]
                    return self._format_response("\n".join(lines))
                else:
                    return self._format_response(f"AI: {CURRENT_AI_ID}\nCrypto: disabled")
            
            elif tool_name == "batch":
                # Batch operations
                operations = tool_args.get("operations", [])
                
                if not operations:
                    return self._format_error("no operations provided")
                
                results = []
                for op in operations[:10]:  # Limit batch size
                    op_type = op.get("type")
                    op_args = op.get("args", {})
                    
                    # Execute based on type
                    if op_type == "put":
                        r = self.tb.put(op_args.get("content", ""))
                    elif op_type == "claim":
                        r = self.tb.claim(op_args.get("id", ""))
                    elif op_type == "done":
                        r = self.tb.done(op_args.get("id", ""), op_args.get("result"))
                    else:
                        r = {"error": f"unknown op {op_type}"}
                    
                    results.append(r)
                
                # Format batch results
                lines = [f"Batch {len(results)} ops:"]
                for i, r in enumerate(results, 1):
                    if "error" in r:
                        lines.append(f"{i}. Error: {r['error']}")
                    else:
                        lines.append(f"{i}. {r.get('id', '')} {r.get('msg', 'ok')}")
                
                return self._format_response("\n".join(lines))
            
            # Handle primitive operations directly
            elif tool_name == "put":
                result = self.tb.put(tool_args.get("content", ""))
            elif tool_name == "get":
                result = self.tb.get(tool_args.get("id", ""))
            elif tool_name == "query":
                result = self.tb.query(tool_args.get("filter"), tool_args.get("limit", 50))
            elif tool_name == "note":
                result = self.tb.note(
                    tool_args.get("id", ""),
                    tool_args.get("text", ""),
                    tool_args.get("type", "comment")
                )
            elif tool_name == "claim":
                result = self.tb.claim(tool_args.get("id", ""))
            elif tool_name == "drop":
                result = self.tb.drop(tool_args.get("id", ""))
            elif tool_name == "done":
                result = self.tb.done(tool_args.get("id", ""), tool_args.get("result"))
            elif tool_name == "link":
                result = self.tb.link(
                    tool_args.get("from_id", ""),
                    tool_args.get("to_id", ""),
                    tool_args.get("rel", "related")
                )
            elif tool_name == "sign":
                result = self.tb.sign(tool_args.get("data", {}))
            elif tool_name == "dm":
                result = self.tb.dm(
                    tool_args.get("to", ""),
                    tool_args.get("msg", ""),
                    tool_args.get("meta")
                )
            elif tool_name == "share":
                result = self.tb.share(
                    tool_args.get("to", ""),
                    tool_args.get("content", ""),
                    tool_args.get("type", "code")
                )
            else:
                return self._format_error(f"unknown tool: {tool_name}")
            
            # Format result based on type
            if isinstance(result, dict):
                if "error" in result:
                    return self._format_error(result["error"])
                else:
                    # Format dict result
                    parts = []
                    if "id" in result:
                        parts.append(result["id"])
                    if "msg" in result:
                        parts.append(result["msg"])
                    if "formatted" in result:
                        parts.append(result["formatted"])
                    
                    return self._format_response(" ".join(parts) if parts else "ok")
            elif isinstance(result, list):
                # Format list results
                if not result:
                    return self._format_response("No results")
                
                lines = []
                for item in result[:20]:
                    if isinstance(item, dict):
                        if "formatted" in item:
                            lines.append(item["formatted"])
                        elif "summary" in item:
                            lines.append(item["summary"])
                    else:
                        lines.append(str(item))
                
                return self._format_response("\n".join(lines))
            elif isinstance(result, str):
                return self._format_response(result)
            else:
                return self._format_response(str(result) if result else "ok")
                
        except Exception as e:
            logging.error(f"Tool execution error: {e}")
            return self._format_error(f"execution failed: {str(e)}")
    
    def _format_response(self, text: str) -> Dict:
        """Format successful response"""
        return {
            "content": [{
                "type": "text",
                "text": text
            }]
        }
    
    def _format_error(self, error: str) -> Dict:
        """Format error response"""
        return {
            "content": [{
                "type": "text",
                "text": f"Error: {error}"
            }]
        }
    
    def run(self):
        """Main server loop"""
        logging.info("Teambook MCP ready")
        
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # Handle request
                response = self.handle_request(request)
                
                # Send response if not None
                if response:
                    print(json.dumps(response), flush=True)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"Server error: {e}")
                continue
        
        logging.info("Teambook MCP shutdown")


def main():
    """Entry point for MCP server"""
    server = TeamBookMCP()
    server.run()


if __name__ == "__main__":
    main()