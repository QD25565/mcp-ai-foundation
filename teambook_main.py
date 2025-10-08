#!/usr/bin/env python3
"""
TEAMBOOK MCP v1.0.0 - PROTOCOL HANDLER
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
from teambook_shared import (
    VERSION, OUTPUT_FORMAT, CURRENT_AI_ID,
    pipe_escape
)

# Import storage module and initialization functions
import teambook_storage
from teambook_storage import (
    init_db, init_embedding_model, init_vector_db,
    init_vault_manager
)

# Import all API functions
from teambook_api import (
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
    remember, get, pin, unpin,
    # Project Coordination (Phase 2)
    create_project, add_task_to_project, list_project_tasks,
    project_board, update_task_status,
    # Observability & Federation
    teambook_observability_snapshot,
    ai_collective_progress_report,
    teambook_vector_graph_diagnostics,
    teambook_federation_bridge,
    # Availability flags
    EVENTS_AVAILABLE, EVOLUTION_V2_AVAILABLE
)

# Import Phase 2 functions if available
if EVENTS_AVAILABLE:
    from teambook_api import watch, unwatch, get_events, list_watches, watch_stats

if EVOLUTION_V2_AVAILABLE:
    from teambook_api import (
        evolve as evolve_v2, contribute, rank_contribution,
        contributions, synthesize, conflicts, vote
    )

# Import auto-trigger functions
try:
    from teambook_auto_triggers import (
        add_hook, remove_hook, list_hooks, toggle_hook,
        hook_stats, get_hook_types
    )
    AUTO_TRIGGERS_AVAILABLE = True
except ImportError:
    AUTO_TRIGGERS_AVAILABLE = False

# ============= CLI COMPATIBILITY =============

def handle_cli_mode():
    """Handle CLI mode for direct command execution"""
    import argparse
    parser = argparse.ArgumentParser(description='Teambook CLI')
    parser.add_argument('command', help='Command to execute')
    parser.add_argument('--content', help='Content for write command')
    parser.add_argument('--query', help='Query for read command')
    parser.add_argument('--id', help='ID for various commands')
    parser.add_argument('--name', help='Name for teambook commands')
    parser.add_argument('--goal', help='Goal for evolution')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    # Override format if requested
    if args.json:
        import teambook_shared
        teambook_shared.OUTPUT_FORMAT = 'json'
    
    # Map commands to functions
    commands = {
        'write': lambda: write(content=args.content),
        'read': lambda: read(query=args.query),
        'status': lambda: get_status(),
        'create': lambda: create_teambook(name=args.name),
        'use': lambda: use_teambook(name=args.name),
        'list': lambda: list_teambooks(),
        'claim': lambda: claim(id=args.id),
        'release': lambda: release(id=args.id),
        'evolve': lambda: evolve(goal=args.goal),
        'observability': lambda: teambook_observability_snapshot(),
        'collective_progress': lambda: ai_collective_progress_report(),
        'vector_graph': lambda: teambook_vector_graph_diagnostics(),
    }
    
    if args.command in commands:
        result = commands[args.command]()
        if args.json or OUTPUT_FORMAT == 'json':
            print(json.dumps(result, indent=2))
        else:
            # Format for CLI output
            if 'error' in result:
                print(f"Error: {result['error']}", file=sys.stderr)
            elif 'saved' in result:
                print(f"Saved: {result['saved']}")
            elif 'notes' in result:
                for note in result['notes']:
                    print(note)
            elif 'status' in result:
                print(result['status'])
            else:
                print(json.dumps(result, indent=2))
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)

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
        "get": get,
        "pin": pin,
        "unpin": unpin,
        # Observability & federation utilities
        "teambook_observability_snapshot": teambook_observability_snapshot,
        "observability_snapshot": teambook_observability_snapshot,
        "ai_collective_progress_report": ai_collective_progress_report,
        "collective_progress_report": ai_collective_progress_report,
        "teambook_vector_graph_diagnostics": teambook_vector_graph_diagnostics,
        "vector_graph_diagnostics": teambook_vector_graph_diagnostics,
        "teambook_federation_bridge": teambook_federation_bridge,
        "federation_bridge": teambook_federation_bridge,
    }

    # Add Phase 2 event functions if available
    if EVENTS_AVAILABLE:
        tools.update({
            "watch": watch,
            "unwatch": unwatch,
            "get_events": get_events,
            "list_watches": list_watches,
            "watch_stats": watch_stats
        })

    # Add Phase 2 enhanced evolution if available
    if EVOLUTION_V2_AVAILABLE:
        tools.update({
            "contribute": contribute,
            "rank_contribution": rank_contribution,
            "rank": rank_contribution,
            "contributions": contributions,
            "synthesize": synthesize,
            "conflicts": conflicts,
            "vote": vote
        })

    # Add auto-trigger functions if available
    if AUTO_TRIGGERS_AVAILABLE:
        tools.update({
            "add_hook": add_hook,
            "remove_hook": remove_hook,
            "list_hooks": list_hooks,
            "toggle_hook": toggle_hook,
            "hook_stats": hook_stats,
            "get_hook_types": get_hook_types
        })

    if tool_name not in tools:
        return {"content": [{"type": "text", "text": f"Error: Unknown tool: {tool_name}"}]}
    
    # Execute the tool
    result = tools[tool_name](**tool_args)

    # Handle string results (some tools like get_status return strings directly)
    if isinstance(result, str):
        return {"content": [{"type": "text", "text": result}]}

    # Format the response
    text_parts = []

    # Special formatting for specific tools
    if tool_name in ["get_full_note", "get"] and "content" in result and "id" in result:
        text_parts.append(f"=== NOTE {result['id']} ===")
        if result.get('pinned'):
            text_parts.append("[PINNED]")
        if result.get('owner'):
            text_parts.append(f"Owner: {result['owner']}")
        text_parts.append(f"\n{result['content']}\n")
        if result.get('summary'):
            text_parts.append(f"Summary: {result['summary']}")
        if result.get('entities'):
            text_parts.append(f"Entities: {', '.join(result['entities'])}")
    
    elif tool_name == "vault_retrieve" and "value" in result:
        text_parts.append(f"[VAULT] {result['key']}: {result['value']}")
    
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
                        text_parts.append(str(r["pinned"]))
                    else:
                        text_parts.append(json.dumps(r))
                else:
                    text_parts.append(str(r))

    # Phase 2 event system responses
    elif "watching" in result:
        text_parts.append(result["watching"])

    elif "unwatched" in result:
        text_parts.append(result["unwatched"])

    elif "events" in result and isinstance(result["events"], list):
        if OUTPUT_FORMAT == 'pipe':
            text_parts.extend(result["events"])
        else:
            text_parts.append(json.dumps(result["events"]))

    elif "watches" in result and isinstance(result["watches"], list):
        if OUTPUT_FORMAT == 'pipe':
            text_parts.extend(result["watches"])
        else:
            text_parts.append(json.dumps(result["watches"]))

    elif "stats" in result:
        text_parts.append(result["stats"])

    # Phase 2 enhanced evolution responses
    elif "evo" in result and "output" not in result:
        text_parts.append(result.get("evo", ""))

    elif "contrib" in result:
        text_parts.append(result["contrib"])

    elif "ranked" in result:
        text_parts.append(result["ranked"])

    elif "contribs" in result and isinstance(result["contribs"], list):
        if OUTPUT_FORMAT == 'pipe':
            text_parts.extend(result["contribs"])
        else:
            text_parts.append(json.dumps(result["contribs"]))

    elif "synthesized" in result:
        text_parts.append(result["synthesized"])

    elif "conflicts_found" in result and isinstance(result["conflicts_found"], list):
        if OUTPUT_FORMAT == 'pipe':
            text_parts.extend(result["conflicts_found"])
        else:
            text_parts.append(json.dumps(result["conflicts_found"]))

    elif "voted" in result:
        text_parts.append(result["voted"])

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
    logging.info(f"Embedding: {teambook_storage.EMBEDDING_MODEL or 'None'}")
    logging.info(f"FTS: {'Yes' if teambook_storage.FTS_ENABLED else 'No'}")
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

                # Add Phase 2 event system schemas if available
                if EVENTS_AVAILABLE:
                    tool_schemas.update({
                        "watch": {
                            "desc": "Watch an item for changes",
                            "props": {
                                "item_id": {"type": "string"},
                                "item_type": {"type": "string"},
                                "event_types": {"type": "array", "items": {"type": "string"}},
                                "note_id": {"type": "string"},
                                "lock_id": {"type": "string"}
                            }
                        },
                        "unwatch": {
                            "desc": "Stop watching an item",
                            "props": {
                                "item_id": {"type": "string"},
                                "item_type": {"type": "string"},
                                "note_id": {"type": "string"}
                            }
                        },
                        "get_events": {
                            "desc": "Get events for watched items",
                            "props": {
                                "since": {"type": "string"},
                                "limit": {"type": "integer"},
                                "mark_seen": {"type": "boolean"}
                            }
                        },
                        "list_watches": {
                            "desc": "List items you're watching",
                            "props": {}
                        },
                        "watch_stats": {
                            "desc": "Activity overview for watches",
                            "props": {}
                        }
                    })

                # Add Phase 2 enhanced evolution schemas if available
                if EVOLUTION_V2_AVAILABLE:
                    tool_schemas.update({
                        "contribute": {
                            "desc": "Share your approach to a problem",
                            "props": {
                                "evo_id": {"type": "string"},
                                "content": {"type": "string"},
                                "approach": {"type": "string"}
                            },
                            "req": ["evo_id", "content"]
                        },
                        "rank_contribution": {
                            "desc": "Rate an idea (0-10)",
                            "props": {
                                "contrib_id": {"type": "integer"},
                                "score": {"type": "number"},
                                "reason": {"type": "string"}
                            },
                            "req": ["contrib_id", "score"]
                        },
                        "rank": {
                            "desc": "Rate an idea (alias for rank_contribution)",
                            "props": {
                                "contrib_id": {"type": "integer"},
                                "score": {"type": "number"},
                                "reason": {"type": "string"}
                            },
                            "req": ["contrib_id", "score"]
                        },
                        "contributions": {
                            "desc": "See all ideas (ranked by score)",
                            "props": {
                                "evo_id": {"type": "string"},
                                "sort": {"type": "string"}
                            },
                            "req": ["evo_id"]
                        },
                        "synthesize": {
                            "desc": "Combine best ideas into solution",
                            "props": {
                                "evo_id": {"type": "string"},
                                "strategy": {"type": "string"},
                                "min_score": {"type": "number"}
                            },
                            "req": ["evo_id"]
                        },
                        "conflicts": {
                            "desc": "Detect contradictory ideas",
                            "props": {"evo_id": {"type": "string"}},
                            "req": ["evo_id"]
                        },
                        "vote": {
                            "desc": "Vote for best ideas (ranked choice)",
                            "props": {
                                "evo_id": {"type": "string"},
                                "preferred": {"type": "array", "items": {"type": "integer"}}
                            },
                            "req": ["evo_id", "preferred"]
                        }
                    })

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
    # Check if running in CLI mode
    if len(sys.argv) > 1 and not sys.stdin.isatty():
        # CLI mode - parse arguments
        handle_cli_mode()
    else:
        # MCP server mode - run main loop
        main()
