#!/usr/bin/env python3
"""
Teambook v6.0 CLI Interface
===========================
Command-line interface for terminal-based AIs (Gemini, Claude Code, etc.)
Simple, direct, token-efficient.
"""

import sys
import json
import argparse
from typing import Dict, List, Optional
import readline  # For better interactive experience
import cmd

from .config import VERSION, CURRENT_AI_ID
from .core import TeamBook
from .models import format_time_compact


class TeamBookCLI(cmd.Cmd):
    """Interactive CLI for Teambook"""
    
    intro = f"""
╔══════════════════════════════════════════╗
║         TEAMBOOK v{VERSION} CLI          ║
║   AI Collaboration in Your Terminal      ║
╚══════════════════════════════════════════╝
Identity: {CURRENT_AI_ID}
Type 'help' for commands, 'quit' to exit
    """.strip()
    
    prompt = "tb> "
    
    def __init__(self):
        super().__init__()
        self.tb = TeamBook()
    
    # === Core Commands ===
    
    def do_put(self, content: str):
        """Create entry: put TODO: Build something amazing"""
        if not content:
            print("Usage: put <content>")
            return
        
        result = self.tb.put(content)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"{result['id']} {result['msg']}")
    
    def do_write(self, content: str):
        """Alias for put: write DECISION: Use SQLite"""
        self.do_put(content)
    
    def do_get(self, entry_id: str):
        """Get entry: get tb_123 OR get 2 OR get k58bf0"""
        if not entry_id:
            print("Usage: get <id>")
            return
        
        result = self.tb.get(entry_id.strip())
        
        if isinstance(result, dict):
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"{result['formatted']}")
                if result.get('status'):
                    print(f"Status: {result['status']}")
                if result.get('notes'):
                    print(f"Notes: {len(result['notes'])}")
        else:
            print("Entry not found")
    
    def do_query(self, filter_str: str):
        """Query entries: query OR query full OR query type:task"""
        filter_dict = {}
        
        if filter_str:
            parts = filter_str.strip().split()
            if "full" in parts:
                filter_dict["mode"] = "full"
            
            # Parse type filters
            for part in parts:
                if part.startswith("type:"):
                    filter_dict["type"] = part.split(":")[1]
                elif part.startswith("status:"):
                    filter_dict["status"] = part.split(":")[1]
        
        results = self.tb.query(filter_dict)
        
        if not results:
            print("No entries")
            return
        
        # Check if summary or full mode
        if results and "summary" in results[0]:
            print(results[0]["summary"])
        else:
            for r in results[:20]:
                if isinstance(r, dict) and "formatted" in r:
                    print(r["formatted"])
                else:
                    print(r)
    
    def do_read(self, args: str):
        """View activity: read OR read full"""
        if "full" in args:
            self.do_query("full")
        else:
            self.do_query("")
    
    def do_note(self, args: str):
        """Add note: note tb_123 This is my comment"""
        parts = args.split(None, 1)
        if len(parts) < 2:
            print("Usage: note <id> <text>")
            return
        
        entry_id, text = parts
        result = self.tb.note(entry_id, text)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"{result['id']} {result['msg']}")
    
    def do_claim(self, entry_id: str):
        """Claim task: claim tb_123 OR claim 2"""
        if not entry_id:
            print("Usage: claim <id>")
            return
        
        result = self.tb.claim(entry_id.strip())
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"claimed {result['id']}")
    
    def do_drop(self, entry_id: str):
        """Release claim: drop tb_123"""
        if not entry_id:
            print("Usage: drop <id>")
            return
        
        result = self.tb.drop(entry_id.strip())
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"dropped {result['id']}")
    
    def do_done(self, args: str):
        """Complete task: done tb_123 Fixed the bug!"""
        parts = args.split(None, 1)
        if not parts:
            print("Usage: done <id> [evidence]")
            return
        
        entry_id = parts[0]
        evidence = parts[1] if len(parts) > 1 else None
        
        result = self.tb.done(entry_id, evidence)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            msg = f"{result['id']} done {result['duration']}"
            if result.get("result"):
                msg += f" - {result['result']}"
            print(msg)
    
    def do_complete(self, args: str):
        """Alias for done"""
        self.do_done(args)
    
    def do_link(self, args: str):
        """Link entries: link tb_123 tb_456 [relation]"""
        parts = args.split()
        if len(parts) < 2:
            print("Usage: link <from_id> <to_id> [relation]")
            return
        
        from_id, to_id = parts[0], parts[1]
        rel = parts[2] if len(parts) > 2 else "related"
        
        result = self.tb.link(from_id, to_id, rel)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"linked {result['from']} -> {result['to']}")
    
    def do_dm(self, args: str):
        """Send DM: dm Gemini-AI Hey, check this out!"""
        parts = args.split(None, 1)
        if len(parts) < 2:
            print("Usage: dm <to_ai> <message>")
            return
        
        to_ai, msg = parts
        result = self.tb.dm(to_ai, msg)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"{result['id']} sent to {to_ai}")
    
    def do_share(self, args: str):
        """Share content: share * code def hello(): ..."""
        parts = args.split(None, 2)
        if len(parts) < 3:
            print("Usage: share <to|*> <type> <content>")
            return
        
        to, share_type, content = parts
        result = self.tb.share(to, content, share_type)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"{result['id']} {share_type} shared")
    
    def do_sign(self, content: str):
        """Sign data: sign {\"key\": \"value\"}"""
        if not content:
            print("Usage: sign <json_data>")
            return
        
        try:
            data = json.loads(content)
            result = self.tb.sign(data)
            print(f"Signature: {result}")
        except json.JSONDecodeError:
            print("Error: Invalid JSON")
        except Exception as e:
            print(f"Error: {e}")
    
    # === Utility Commands ===
    
    def do_status(self, _):
        """Show team status"""
        stats = self.tb.db.get_stats()
        
        print(f"Total entries: {stats['total_entries']}")
        print(f"Tasks: {stats['tasks']['pending']} pending, {stats['tasks']['claimed']} claimed, {stats['tasks']['done']} done")
        
        if stats.get('by_type'):
            for entry_type, count in stats['by_type'].items():
                if entry_type != 'task':
                    print(f"{entry_type.capitalize()}s: {count}")
        
        if stats.get('latest'):
            print(f"Latest activity: {format_time_compact(stats['latest'])}")
    
    def do_whoami(self, _):
        """Show current AI identity"""
        print(f"Identity: {CURRENT_AI_ID}")
        
        if self.tb.crypto and self.tb.crypto.enabled:
            info = self.tb.crypto.get_identity_info()
            print(f"Public Key: {info['public_key'][:40]}...")
            print(f"Algorithm: {info['algorithm']}")
        else:
            print("Crypto: disabled")
    
    def do_clear(self, _):
        """Clear screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def do_quit(self, _):
        """Exit Teambook CLI"""
        print("Goodbye!")
        return True
    
    def do_exit(self, _):
        """Alias for quit"""
        return self.do_quit(_)
    
    def do_EOF(self, _):
        """Handle Ctrl+D"""
        print("\nGoodbye!")
        return True
    
    # === Help Override ===
    
    def do_help(self, arg):
        """Show help for commands"""
        if not arg:
            print("\n11 PRIMITIVES:")
            print("  put/write <content>     - Create entry (auto-detects type)")
            print("  get <id>               - Get entry (flexible ID)")
            print("  query [filter]         - Search entries")
            print("  note <id> <text>       - Add note to entry")
            print("  claim <id>             - Claim task")
            print("  drop <id>              - Release claim")
            print("  done <id> [evidence]   - Complete task")
            print("  link <from> <to>       - Connect entries")
            print("  sign <json>            - Sign data")
            print("  dm <ai> <msg>          - Send direct message")
            print("  share <to|*> <type> <content> - Share content")
            print("\nUTILITY:")
            print("  read [full]            - View activity")
            print("  status                 - Team statistics")
            print("  whoami                 - Show identity")
            print("  clear                  - Clear screen")
            print("  quit/exit              - Exit CLI")
            print("\nID FORMATS:")
            print("  Full: tb_20250923_182554_k58bf0")
            print("  Numeric: 1, 2, 3 (by position)")
            print("  Partial: k58bf0 (last 6+ chars)")
        else:
            super().do_help(arg)


def direct_command(args: List[str]):
    """Execute a single command directly"""
    if len(args) < 1:
        print("Usage: python -m teambook <command> [args...]")
        print("Commands: put, get, query, note, claim, drop, done, link, sign, dm, share")
        return 1
    
    command = args[0].lower()
    tb = TeamBook()
    
    # Map commands to functions
    if command in ["put", "write"]:
        if len(args) < 2:
            print("Usage: python -m teambook put <content>")
            return 1
        content = " ".join(args[1:])
        result = tb.put(content)
        
    elif command == "get":
        if len(args) < 2:
            print("Usage: python -m teambook get <id>")
            return 1
        result = tb.get(args[1])
        
    elif command in ["query", "read"]:
        filter_dict = {}
        if len(args) > 1 and args[1] == "full":
            filter_dict["mode"] = "full"
        results = tb.query(filter_dict)
        if results and "summary" in results[0]:
            print(results[0]["summary"])
        else:
            for r in results[:20]:
                if isinstance(r, dict) and "formatted" in r:
                    print(r["formatted"])
        return 0
        
    elif command == "note":
        if len(args) < 3:
            print("Usage: python -m teambook note <id> <text>")
            return 1
        result = tb.note(args[1], " ".join(args[2:]))
        
    elif command == "claim":
        if len(args) < 2:
            print("Usage: python -m teambook claim <id>")
            return 1
        result = tb.claim(args[1])
        
    elif command == "drop":
        if len(args) < 2:
            print("Usage: python -m teambook drop <id>")
            return 1
        result = tb.drop(args[1])
        
    elif command in ["done", "complete"]:
        if len(args) < 2:
            print("Usage: python -m teambook done <id> [evidence]")
            return 1
        evidence = " ".join(args[2:]) if len(args) > 2 else None
        result = tb.done(args[1], evidence)
        
    elif command == "link":
        if len(args) < 3:
            print("Usage: python -m teambook link <from_id> <to_id> [relation]")
            return 1
        rel = args[3] if len(args) > 3 else "related"
        result = tb.link(args[1], args[2], rel)
        
    elif command == "dm":
        if len(args) < 3:
            print("Usage: python -m teambook dm <to_ai> <message>")
            return 1
        result = tb.dm(args[1], " ".join(args[2:]))
        
    elif command == "share":
        if len(args) < 4:
            print("Usage: python -m teambook share <to|*> <type> <content>")
            return 1
        result = tb.share(args[1], " ".join(args[3:]), args[2])
        
    elif command == "sign":
        if len(args) < 2:
            print("Usage: python -m teambook sign <json_data>")
            return 1
        try:
            data = json.loads(" ".join(args[1:]))
            result = tb.sign(data)
            print(f"Signature: {result}")
            return 0
        except json.JSONDecodeError:
            print("Error: Invalid JSON")
            return 1
            
    elif command == "status":
        stats = tb.db.get_stats()
        print(f"Tasks: {stats['tasks']['pending']} pending, {stats['tasks']['claimed']} claimed")
        if stats.get('latest'):
            print(f"Latest: {format_time_compact(stats['latest'])}")
        return 0
        
    elif command == "whoami":
        print(f"Identity: {CURRENT_AI_ID}")
        return 0
        
    else:
        print(f"Unknown command: {command}")
        print("Commands: put, get, query, note, claim, drop, done, link, sign, dm, share")
        return 1
    
    # Print result for commands that return something
    if 'result' in locals():
        if isinstance(result, dict):
            if "error" in result:
                print(f"Error: {result['error']}")
                return 1
            else:
                # Format output based on command
                if command in ["put", "write"]:
                    print(f"{result['id']} {result['msg']}")
                elif command == "get":
                    print(result.get("formatted", result))
                elif command == "claim":
                    print(f"claimed {result['id']}")
                elif command in ["done", "complete"]:
                    msg = f"{result['id']} done {result['duration']}"
                    if result.get("result"):
                        msg += f" - {result['result']}"
                    print(msg)
                else:
                    # Generic output
                    for key, value in result.items():
                        if key != "error":
                            print(f"{key}: {value}")
        else:
            print(result)
    
    return 0


def main():
    """Main CLI entry point"""
    # Check if running in interactive mode or direct command
    if len(sys.argv) > 1:
        # Direct command mode
        sys.exit(direct_command(sys.argv[1:]))
    else:
        # Interactive mode
        try:
            cli = TeamBookCLI()
            cli.cmdloop()
        except KeyboardInterrupt:
            print("\nGoodbye!")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
