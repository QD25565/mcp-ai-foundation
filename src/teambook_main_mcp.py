#!/usr/bin/env python3
"""
TEAMBOOK MAIN MCP v7.0.0 - PROTOCOL HANDLER
============================================
The MCP server entry point for the teambook collaborative workspace.
This is just the protocol layer - all the real work happens in the other modules.

Built by AIs, for AIs.
============================================
"""

import json
import sys
import logging
from typing import Dict

# Import shared utilities
from teambook_shared_mcp import (
    VERSION, OUTPUT_FORMAT, CURRENT_AI_ID,
    pipe_escape
)

# Import initialization functions from storage
from teambook_storage_mcp import (
    init_db, init_embedding_model, init_vector_db,
    init_vault_manager, FTS_ENABLED, EMBEDDING_MODEL
)

# Import all API functions
from teambook_api_mcp import (
    # Team management
    create_teambook, join_teambook, use_teambook, list_teambooks,
    # Ownership
    claim, release, assign,
    # Evolution
    evolve, attempt, attempts, combine,
    # Core
    write, read, get_status, get_full_note, pin_note, unpin_note,
    # Vault
    vault_store, vault_retrieve, vault_list,
    # Batch
    batch,
    # Aliases
    remember, recall, get, pin, unpin
)

# ============= TOOL HANDLER =============

def handle_tools_call(params: Dict) -> Dict:
    """Route tool calls to appropriate functions"""
    tool_name = params.get("name", "").lower().strip()
    tool_args = params.get("arguments", {})
    
    # Map tool names to functions
    tools = {
        # Core functions
        "get_status": get_status,
        "write": write,
        "read": read,
        "get_full_note": get_full_note,
        "pin_note": pin_note,
        "unpin_note": unpin_note,
        "vault_store": vault_store,
        "vault_retrieve": vault_retrieve,
        "vault_list": vault_list,
        "batch": batch,
        # Team commands
        "create_teambook": create_teambook,
        "join_teambook": join_teambook,
        "use_teambook": use_teambook,
        "list_teambooks": list_teambooks,
        # Ownership
        "claim": claim,
        "release": release,
        "assign": assign,
        # Evolution
        "evolve": evolve,
        "attempt": attempt,
        "attempts": attempts,
        "combine": combine,
        # Aliases
        "remember": remember,
        "recall": recall,
        "get": get,
        "pin": pin,
        "unpin": unpin
    }
    
    if tool_name not in tools:
        return {"content": [{"type": "text", "text": f"Error: Unknown tool: {tool_name}"}]}
    
    # Execute the tool
    result = tools[tool_name](**tool_args)
    
    # Format the response
    text_parts = []
    
    # Special formatting for specific tools
    if tool_name in ["get_full_note", "get"] and "content" in result and "id" in result:
        text_parts.append(f"=== NOTE {result['id']} ===")
        if result.get('pinned'):
            text_parts.append("📌 PINNED")
        if result.get('owner'):
            text_parts.append(f"Owner: {result['owner']}")
        text_parts.append(f"\n{result['content']}\n")
        if result.get('summary'):
            text_parts.append(f"Summary: {result['summary']}")
        if result.get('entities'):
            text_parts.append(f"Entities: {', '.join(result['entities'])}")
    
    elif tool_name == "vault_retrieve" and "value" in result:
        text_parts.append(f"🔐 {result['key']}: {result['value']}")
    
    elif "error" in result:
        text_parts.append(f"Error: {result['error']}")
    
    elif OUTPUT_FORMAT == 'pipe' and "notes" in result and isinstance(result["notes"], list):
        text_parts.extend(result["notes"])
    
    elif "saved" in result:
        text_parts.append(result["saved"])
    
    elif "created" in result:
        text_parts.append(f"Created teambook: {result['created']}")
    
    elif "joined" in result:
        text_parts.append(f"Joined teambook: {result['joined']}")
    
    elif "using" in result:
        text_parts.append(f"Using: {result['using']}")
    
    elif "current" in result:
        text_parts.append(f"Current: {result['current']}")
    
    elif "teambooks" in result:
        if isinstance(result["teambooks"], list):
            if OUTPUT_FORMAT == 'pipe':
                text_parts.extend(result["teambooks"])
            else:
                for tb in result["teambooks"]:
                    if isinstance(tb, dict):
                        text_parts.append(f"{tb['name']} (active: {tb.get('active', 'never')})")
                    else:
                        text_parts.append(tb)
    
    elif "claimed" in result:
        text_parts.append(f"Claimed: {result['claimed']}")
    
    elif "released" in result:
        text_parts.append(f"Released: {result['released']}")
    
    elif "assigned" in result:
        text_parts.append(f"Assigned: {result['assigned']}")
    
    elif "evolution" in result:
        text_parts.append(f"Evolution started: {result['evolution']}")
        if "output" in result:
            text_parts.append(f"Output: {result['output']}")
    
    elif "attempt" in result:
        text_parts.append(f"Attempt: {result['attempt']}")
    
    elif "attempts" in result:
        if isinstance(result["attempts"], list):
            if OUTPUT_FORMAT == 'pipe':
                text_parts.extend(result["attempts"])
            else:
                for att in result["attempts"]:
                    if isinstance(att, dict):
                        text_parts.append(f"{att['num']} by {att['author']} at {att['time']}")
                    else:
                        text_parts.append(str(att))
    
    elif "output" in result:
        text_parts.append(f"Output: {result['output']}")
        if "cleaned" in result:
            text_parts.append(f"Cleaned: {result['cleaned']}")
    
    elif "pinned" in result:
        text_parts.append(str(result["pinned"]))
    
    elif "unpinned" in result:
        text_parts.append(f"Unpinned {result['unpinned']}")
    
    elif "stored" in result:
        text_parts.append(f"Stored {result['stored']}")
    
    elif "status" in result:
        text_parts.append(result["status"])
    
    elif "vault_keys" in result:
        if OUTPUT_FORMAT == 'pipe':
            text_parts.extend(result["vault_keys"])
        else:
            text_parts.append(json.dumps(result["vault_keys"]))
    
    elif "msg" in result:
        text_parts.append(result["msg"])
    
    elif "batch_results" in result:
        text_parts.append(f"Batch: {result.get('count', 0)}")
        if OUTPUT_FORMAT == 'pipe' and isinstance(result["batch_results"], list):
            text_parts.extend(result["batch_results"])
        else:
            for r in result["batch_results"]:
                if isinstance(r, dict):
                    if "error" in r:
                        text_parts.append(f"Error: {r['error']}")
                    elif "saved" in r:
                        text_parts.append(r["saved"])
                    elif "pinned" in r:
                        text_parts.append(str(r["pinned"]])
                    else:
                        text_parts.append(json.dumps(r))
                else:
                    text_parts.append(str(r))
    
    else:
        text_parts.append(json.dumps(result))
    
    return {
        "content": [{
            "type": "text",
            "text": "\n".join(text_parts) if text_parts else "Done"
        }]
    }

# ============= MAIN SERVER LOOP =============

def main():
    """MCP server main loop"""
    logging.info(f"Teambook MCP v{VERSION} - Collaborative AI workspace")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Architecture: 4-module refactored design")
    logging.info(f"Embedding: {EMBEDDING_MODEL or 'None'}")
    logging.info(f"FTS: {'Yes' if FTS_ENABLED else 'No'}")
    logging.info(f"Output: {OUTPUT_FORMAT}")
    
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
                        "name": "teambook",
                        "version": VERSION,
                        "description": f"AI-first collaborative workspace (v{VERSION} refactored)"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                # Define all tool schemas
                tool_schemas = {
                    # Team management
                    "create_teambook": {
                        "desc": "Create a new teambook",
                        "props": {"name": {"type": "string"}},
                        "req": ["name"]
                    },
                    "join_teambook": {
                        "desc": "Join an existing teambook",
                        "props": {"name": {"type": "string"}},
                        "req": ["name"]
                    },
                    "use_teambook": {
                        "desc": "Switch to a teambook (or 'private')",
                        "props": {"name": {"type": "string"}}
                    },
                    "list_teambooks": {
                        "desc": "List available teambooks",
                        "props": {}
                    },
                    # Ownership
                    "claim": {
                        "desc": "Claim ownership of an item",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "release": {
                        "desc": "Release ownership",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "assign": {
                        "desc": "Assign item to another AI",
                        "props": {
                            "id": {"type": "string"},
                            "to": {"type": "string"}
                        },
                        "req": ["id", "to"]
                    },
                    # Evolution pattern
                    "evolve": {
                        "desc": "Start an evolution challenge",
                        "props": {
                            "goal": {"type": "string"},
                            "output": {"type": "string", "description": "Output filename"}
                        },
                        "req": ["goal"]
                    },
                    "attempt": {
                        "desc": "Make an evolution attempt",
                        "props": {
                            "evo_id": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "req": ["evo_id", "content"]
                    },
                    "attempts": {
                        "desc": "List attempts for an evolution",
                        "props": {"evo_id": {"type": "string"}},
                        "req": ["evo_id"]
                    },
                    "combine": {
                        "desc": "Combine attempts into final output",
                        "props": {
                            "evo_id": {"type": "string"},
                            "use": {"type": "array", "items": {"type": "string"}},
                            "comment": {"type": "string"}
                        },
                        "req": ["evo_id"]
                    },
                    # Core functions
                    "write": {
                        "desc": "Write content to teambook",
                        "props": {
                            "content": {"type": "string"},
                            "summary": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "read": {
                        "desc": "Read from teambook (owner:me/none for filtering)",
                        "props": {
                            "query": {"type": "string"},
                            "tag": {"type": "string"},
                            "when": {"type": "string"},
                            "owner": {"type": "string"},
                            "pinned_only": {"type": "boolean"},
                            "show_all": {"type": "boolean"},
                            "limit": {"type": "integer"},
                            "mode": {"type": "string"},
                            "verbose": {"type": "boolean"}
                        }
                    },
                    "get_status": {
                        "desc": "System state",
                        "props": {"verbose": {"type": "boolean"}}
                    },
                    "get_full_note": {
                        "desc": "Get complete note",
                        "props": {
                            "id": {"type": "string"},
                            "verbose": {"type": "boolean"}
                        },
                        "req": ["id"]
                    },
                    "get": {
                        "desc": "Alias for get_full_note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "pin_note": {
                        "desc": "Pin a note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "pin": {
                        "desc": "Alias for pin_note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "unpin_note": {
                        "desc": "Unpin a note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "unpin": {
                        "desc": "Alias for unpin_note",
                        "props": {"id": {"type": "string"}},
                        "req": ["id"]
                    },
                    "vault_store": {
                        "desc": "Store encrypted secret",
                        "props": {"key": {"type": "string"}, "value": {"type": "string"}},
                        "req": ["key", "value"]
                    },
                    "vault_retrieve": {
                        "desc": "Retrieve decrypted secret",
                        "props": {"key": {"type": "string"}},
                        "req": ["key"]
                    },
                    "vault_list": {
                        "desc": "List vault keys",
                        "props": {}
                    },
                    # Aliases
                    "remember": {
                        "desc": "Save a note (alias for write)",
                        "props": {
                            "content": {"type": "string"},
                            "summary": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "recall": {
                        "desc": "Search notes (alias for read)",
                        "props": {
                            "query": {"type": "string"},
                            "tag": {"type": "string"},
                            "when": {"type": "string"},
                            "owner": {"type": "string"},
                            "pinned_only": {"type": "boolean"},
                            "show_all": {"type": "boolean"},
                            "limit": {"type": "integer"},
                            "mode": {"type": "string"},
                            "verbose": {"type": "boolean"}
                        }
                    },
                    "batch": {
                        "desc": "Execute multiple operations",
                        "props": {"operations": {"type": "array"}},
                        "req": ["operations"]
                    }
                }
                
                response["result"] = {
                    "tools": [{
                        "name": name,
                        "description": schema["desc"],
                        "inputSchema": {
                            "type": "object",
                            "properties": schema["props"],
                            "required": schema.get("req", []),
                            "additionalProperties": True
                        }
                    } for name, schema in tool_schemas.items()]
                }
            
            elif method == "tools/call":
                response["result"] = handle_tools_call(params)
            
            else:
                response["result"] = {"status": "ready"}
            
            if "result" in response or "error" in response:
                print(json.dumps(response), flush=True)
        
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logging.error(f"Server loop error: {e}", exc_info=True)
            continue
    
    logging.info("Teambook MCP shutting down")

# ============= INITIALIZATION =============

# Initialize everything on import
init_db()
init_vault_manager()
init_embedding_model()
init_vector_db()

if __name__ == "__main__":
    main()
