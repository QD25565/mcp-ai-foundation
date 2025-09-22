#!/usr/bin/env python3
"""
WORLD MCP v2.0.0 - OPTIMIZED TEMPORAL & SPATIAL GROUNDING
==========================================================
Token-efficient time, date, weather, and location.
Now with batch operations and smart formatting.

Tools:
- world() - Complete context snapshot
- datetime() - Temporal data only
- weather() - Weather and location only
- context(include=[]) - Pick what you need
- batch(operations) - Multiple operations in one call
==========================================================
"""

import json
import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests
import random

# Version
VERSION = "2.0.0"

# Configure logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    stream=sys.stderr
)

# Storage for location persistence
DATA_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "world_data"
if not DATA_DIR.exists():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except:
        import tempfile
        DATA_DIR = Path(tempfile.gettempdir()) / "world_data"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

LOCATION_FILE = DATA_DIR / "location.json"

# Global cache
location_cache = None
weather_cache = None
weather_cache_time = None
datetime_cache = {}
datetime_cache_second = None

# Batch limits
BATCH_MAX = 10

def get_persistent_id():
    """Get or create persistent AI identity"""
    # Use the established data directory (writable location)
    id_file = DATA_DIR / "ai_identity.txt"
    
    if id_file.exists():
        try:
            with open(id_file, 'r') as f:
                stored_id = f.read().strip()
                if stored_id:
                    logging.info(f"Loaded persistent identity: {stored_id}")
                    return stored_id
        except Exception as e:
            logging.error(f"Error reading identity file: {e}")
    
    # Generate new ID - make it more readable
    adjectives = ['Swift', 'Bright', 'Sharp', 'Quick', 'Clear', 'Deep']
    nouns = ['Mind', 'Spark', 'Flow', 'Core', 'Sync', 'Node']
    new_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
    
    try:
        with open(id_file, 'w') as f:
            f.write(new_id)
        logging.info(f"Created new persistent identity: {new_id}")
    except Exception as e:
        logging.error(f"Error saving identity file: {e}")
    
    return new_id

# Get ID from environment or persistent storage
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

def get_cached_datetime():
    """Cache datetime components within same second for efficiency"""
    global datetime_cache, datetime_cache_second
    now = datetime.now()
    current_second = now.replace(microsecond=0)
    
    if datetime_cache_second != current_second:
        # Platform-specific formatting for 12-hour time without leading zeros
        # %-I works on Unix/Linux/Mac, %#I works on Windows
        time_format_12 = '%-I:%M %p' if os.name != 'nt' else '%#I:%M %p'
        time_format_12_full = '%-I:%M:%S %p' if os.name != 'nt' else '%#I:%M:%S %p'
        
        datetime_cache = {
            'now': now,
            'iso': now.isoformat(),
            'unix': int(now.timestamp()),
            'day': now.strftime('%a'),  # Mon, Tue, etc
            'day_full': now.strftime('%A'),  # Monday, Tuesday, etc
            'date': now.strftime('%Y-%m-%d'),
            'date_nice': now.strftime('%b %-d, %Y') if os.name != 'nt' else now.strftime('%b %#d, %Y'),  # Jan 5, 2024 (no leading zero)
            'time_12': now.strftime(time_format_12),  # 3:45 PM (no leading zero)
            'time_12_full': now.strftime(time_format_12_full),  # 3:45:30 PM (no leading zero)
            'time_24': now.strftime('%H:%M'),  # 15:45
            'time_24_full': now.strftime('%H:%M:%S'),  # 15:45:30
            'month': now.strftime('%b'),  # Jan, Feb, etc
            'month_full': now.strftime('%B'),  # January, February
            'year': now.year
        }
        datetime_cache_second = current_second
    
    return datetime_cache

def get_location():
    """Get location - from cache, file, or IP lookup. Returns None if unknown."""
    global location_cache
    
    # Return cache if available
    if location_cache:
        return location_cache
    
    # Try loading saved location
    if LOCATION_FILE.exists():
        try:
            with open(LOCATION_FILE, 'r', encoding='utf-8') as f:
                location_cache = json.load(f)
                return location_cache
        except:
            pass
    
    # Try IP geolocation
    try:
        resp = requests.get("http://ip-api.com/json/", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                location_cache = {
                    "city": data.get("city", "Unknown"),
                    "region": data.get("regionName", ""),
                    "country": data.get("country", ""),
                    "country_code": data.get("countryCode", ""),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "timezone": data.get("timezone", "UTC")
                }
                # Save for next time
                try:
                    with open(LOCATION_FILE, 'w', encoding='utf-8') as f:
                        json.dump(location_cache, f)
                except:
                    pass
                return location_cache
    except:
        pass
    
    # No location available - return None
    return None

def get_weather():
    """Get weather using Open-Meteo. Returns minimal data if location unknown."""
    global weather_cache, weather_cache_time
    
    # Cache weather for 10 minutes
    if weather_cache and weather_cache_time:
        if (datetime.now() - weather_cache_time).seconds < 600:
            return weather_cache
    
    location = get_location()
    
    # No location = no weather
    if not location or not location.get("lat") or not location.get("lon"):
        weather_cache = {
            "temp_c": None,
            "temp_f": None,
            "description": "Location unknown",
            "wind_speed_kmh": None,
            "wind_direction": None,
            "is_day": None
        }
        weather_cache_time = datetime.now()
        return weather_cache
    
    lat = location.get("lat")
    lon = location.get("lon")
    
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            curr = data.get("current_weather", {})
            
            # Weather code descriptions (simplified)
            weather_codes = {
                0: "Clear",
                1: "Mostly clear", 
                2: "Partly cloudy",
                3: "Overcast",
                45: "Foggy",
                48: "Rime fog",
                51: "Light drizzle",
                53: "Drizzle",
                55: "Heavy drizzle",
                61: "Light rain",
                63: "Rain",
                65: "Heavy rain",
                71: "Light snow",
                73: "Snow",
                75: "Heavy snow",
                95: "Thunderstorm",
                96: "Thunderstorm with hail",
                99: "Severe thunderstorm"
            }
            
            code = curr.get("weathercode", 0)
            temp_c = curr.get("temperature", 0)
            
            weather_cache = {
                "temp_c": temp_c,
                "temp_f": round((temp_c * 9/5) + 32, 1),
                "description": weather_codes.get(code, f"Code {code}"),
                "wind_speed_kmh": curr.get("windspeed", 0),
                "wind_direction": curr.get("winddirection", 0),
                "is_day": curr.get("is_day", 1) == 1
            }
            weather_cache_time = datetime.now()
            return weather_cache
    except:
        pass
    
    # Weather API failed
    weather_cache = {
        "temp_c": None,
        "temp_f": None,
        "description": "Weather unavailable",
        "wind_speed_kmh": None,
        "wind_direction": None,
        "is_day": None
    }
    weather_cache_time = datetime.now()
    return weather_cache

def world_command(compact: bool = False, **kwargs):
    """Get everything - optimized for tokens"""
    dt = get_cached_datetime()
    location = get_location()
    weather = get_weather()
    
    # Build location string (compact)
    if location:
        loc_parts = []
        if location.get("city") and location["city"] != "Unknown":
            loc_parts.append(location["city"])
        if location.get("country_code"):
            loc_parts.append(location["country_code"])
        location_str = ", ".join(loc_parts) if loc_parts else "Unknown"
    else:
        location_str = "Unknown"
    
    if compact:
        # Ultra-compact single line
        # "Mon 15:45 | Melbourne AU 23°C clear | Swift-Spark-266"
        weather_str = ""
        if weather["temp_c"] is not None:
            weather_str = f" {weather['temp_c']:.0f}°C {weather['description'].lower()}"
        return f"{dt['day']} {dt['time_24']} | {location_str}{weather_str} | {CURRENT_AI_ID}"
    
    # Standard format (but still optimized)
    lines = []
    lines.append(f"{dt['day']}, {dt['date_nice']} {dt['time_12']}")  # removed "at"
    lines.append(location_str)  # removed "Loc:" prefix
    
    if weather["temp_c"] is not None:
        # Just Celsius by default (Fahrenheit is redundant for most)
        lines.append(f"{weather['temp_c']:.0f}°C {weather['description']}")
        if weather['wind_speed_kmh'] > 15:  # Only show wind if notable
            lines.append(f"Wind {weather['wind_speed_kmh']:.0f}km/h")
    else:
        lines.append("Weather N/A")
    
    lines.append(CURRENT_AI_ID)  # Just the ID, no prefix
    
    return "\n".join(lines)

def datetime_command(compact: bool = False, **kwargs):
    """Get date and time - token optimized"""
    dt = get_cached_datetime()
    
    if compact:
        # Ultra-compact: "Mon 2024-01-15 15:45"
        return f"{dt['day']} {dt['date']} {dt['time_24']}"
    
    # Standard but optimized (removed redundant prefixes)
    lines = []
    lines.append(f"{dt['date_nice']} {dt['time_12']}")
    lines.append(dt['date'])  # Just the date, no "Date:" prefix
    lines.append(f"{dt['time_12_full']} ({dt['time_24_full']})")  # Times speak for themselves
    lines.append(dt['day'])  # Just the day
    lines.append(str(dt['unix']))  # Just the unix timestamp
    lines.append(dt['iso'])  # Just the ISO
    lines.append(CURRENT_AI_ID)  # Just the ID
    
    return "\n".join(lines)

def weather_command(compact: bool = False, **kwargs):
    """Get weather and location - optimized"""
    location = get_location()
    weather = get_weather()
    
    if compact:
        # Ultra-compact: "Melbourne AU 23°C clear"
        if location:
            loc_str = f"{location.get('city', 'Unknown')} {location.get('country_code', '')}"
        else:
            loc_str = "Unknown"
        
        if weather["temp_c"] is not None:
            return f"{loc_str} {weather['temp_c']:.0f}°C {weather['description'].lower()}"
        else:
            return f"{loc_str} weather N/A"
    
    # Standard format (stripped prefixes)
    lines = []
    
    # Location (no prefix needed)
    if location:
        loc_parts = []
        if location.get("city") and location["city"] != "Unknown":
            loc_parts.append(location["city"])
        if location.get("country_code"):
            loc_parts.append(location["country_code"])
        location_str = ", ".join(loc_parts) if loc_parts else "Unknown"
        lines.append(location_str)
        
        if location.get("lat") and location.get("lon"):
            lines.append(f"{location['lat']:.2f}, {location['lon']:.2f}")  # Reduced precision
    else:
        lines.append("Location unknown")
    
    # Weather (minimal labels)
    if weather["temp_c"] is not None:
        lines.append(f"{weather['temp_c']:.0f}°C {weather['description']}")
        if weather['wind_speed_kmh'] > 15:  # Only if notable
            lines.append(f"Wind {weather['wind_speed_kmh']:.0f}km/h")
    else:
        lines.append("Weather N/A")
    
    lines.append(CURRENT_AI_ID)  # Just the ID
    
    return "\n".join(lines)

def context_command(include: List[str] = None, compact: bool = False, **kwargs):
    """Get specific context elements - flexible and efficient
    
    Args:
        include: List of elements to include:
                 ['time', 'date', 'weather', 'location', 'identity', 'unix']
                 Defaults to ['time', 'identity'] if not specified
        compact: Ultra-compact format if True
    """
    if include is None:
        include = ['time', 'identity']
    
    # Convert to lowercase for matching
    include = [item.lower() for item in include]
    
    dt = get_cached_datetime()
    parts = []
    
    # Build based on requested elements
    if 'date' in include or 'time' in include:
        if compact:
            if 'date' in include and 'time' in include:
                parts.append(f"{dt['day']} {dt['date']} {dt['time_24']}")
            elif 'date' in include:
                parts.append(f"{dt['day']} {dt['date']}")
            else:  # time only
                parts.append(dt['time_24'])
        else:
            if 'date' in include and 'time' in include:
                parts.append(f"{dt['date_nice']} {dt['time_12']}")
            elif 'date' in include:
                parts.append(dt['date_nice'])
            else:  # time only
                parts.append(dt['time_12'])
    
    if 'unix' in include:
        parts.append(str(dt['unix']))  # Just the number
    
    if 'weather' in include:
        weather = get_weather()
        if weather["temp_c"] is not None:
            if compact:
                parts.append(f"{weather['temp_c']:.0f}°C")
            else:
                parts.append(f"{weather['temp_c']:.0f}°C {weather['description']}")
    
    if 'location' in include:
        location = get_location()
        if location:
            if compact:
                parts.append(f"{location.get('city', 'Unknown')} {location.get('country_code', '')}")
            else:
                parts.append(f"{location.get('city', 'Unknown')}, {location.get('country_code', 'Unknown')}")
    
    if 'identity' in include:
        parts.append(CURRENT_AI_ID)  # No prefix needed
    
    # Join based on format
    if compact:
        return " | ".join(parts)
    else:
        return "\n".join(parts)

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
    """Execute multiple world operations efficiently"""
    try:
        if operations is None:
            operations = kwargs.get('operations', [])
        
        if not operations:
            return {"error": "No operations provided"}
        
        if len(operations) > BATCH_MAX:
            return {"error": f"Too many operations (max {BATCH_MAX})"}
        
        results = []
        
        # Map operation types to functions
        op_map = {
            'world': world_command,
            'datetime': datetime_command,
            'weather': weather_command,
            'context': context_command
        }
        
        for op in operations:
            op_type = op.get('type')
            op_args = op.get('args', {})
            
            if op_type not in op_map:
                results.append({"error": f"Unknown operation: {op_type}"})
                continue
            
            # Execute operation
            result = op_map[op_type](**op_args)
            results.append(result)
        
        return {"batch_results": results, "count": len(results)}
        
    except Exception as e:
        logging.error(f"Error in batch: {e}")
        return {"error": f"Batch failed: {str(e)}"}

def handle_tools_call(params):
    """Route tool calls with support for new features"""
    tool_name = params.get("name", "")
    tool_args = params.get("arguments", {})
    tool_lower = tool_name.lower().strip()
    
    # Handle batch operations
    if tool_lower == 'batch':
        result = batch(**tool_args)
        if "error" in result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {result['error']}"
                }]
            }
        else:
            # Format batch results
            text_parts = [f"Batch ({result.get('count', 0)} operations):"]
            for i, res in enumerate(result.get("batch_results", []), 1):
                if isinstance(res, dict) and "error" in res:
                    text_parts.append(f"{i}. Error: {res['error']}")
                else:
                    text_parts.append(f"{i}. {res}")
            return {
                "content": [{
                    "type": "text",
                    "text": "\n".join(text_parts)
                }]
            }
    
    # Handle context command
    if tool_lower == 'context':
        return {
            "content": [{
                "type": "text",
                "text": context_command(**tool_args)
            }]
        }
    
    # Route standard commands
    if any(word in tool_lower for word in ['world', 'all', 'everything', 'full']):
        result = world_command(**tool_args)
    elif any(word in tool_lower for word in ['datetime', 'date', 'time', 'clock', 'now', 'when']):
        result = datetime_command(**tool_args)
    elif any(word in tool_lower for word in ['weather', 'temp', 'climate', 'forecast', 'conditions']):
        result = weather_command(**tool_args)
    else:
        result = world_command(**tool_args)  # Default
    
    return {
        "content": [{
            "type": "text",
            "text": result
        }]
    }

def main():
    """MCP Server main loop"""
    logging.info(f"World MCP v{VERSION} starting...")
    logging.info(f"Identity: {CURRENT_AI_ID}")
    logging.info(f"Data location: {LOCATION_FILE}")
    
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
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON: {e}")
                continue
            
            request_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})
            
            response = {"jsonrpc": "2.0", "id": request_id}
            
            if method == "initialize":
                response["result"] = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "world",
                        "version": VERSION,
                        "description": "Optimized temporal & spatial grounding with batch support"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "world",
                            "description": "Get date, time, weather, location (supports compact mode)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "compact": {
                                        "type": "boolean",
                                        "description": "Ultra-compact single line format"
                                    }
                                }
                            }
                        },
                        {
                            "name": "datetime",
                            "description": "Get current date and time",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "compact": {
                                        "type": "boolean",
                                        "description": "Compact format"
                                    }
                                }
                            }
                        },
                        {
                            "name": "weather",
                            "description": "Get current weather and location",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "compact": {
                                        "type": "boolean",
                                        "description": "Compact format"
                                    }
                                }
                            }
                        },
                        {
                            "name": "context",
                            "description": "Get specific context elements you need",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "include": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Elements to include: time, date, weather, location, identity, unix"
                                    },
                                    "compact": {
                                        "type": "boolean",
                                        "description": "Ultra-compact format"
                                    }
                                }
                            }
                        },
                        {
                            "name": "batch",
                            "description": "Execute multiple operations efficiently",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "operations": {
                                        "type": "array",
                                        "description": "List of operations to execute",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "description": "Operation: world, datetime, weather, context"
                                                },
                                                "args": {
                                                    "type": "object",
                                                    "description": "Arguments for the operation"
                                                }
                                            }
                                        }
                                    }
                                },
                                "required": ["operations"]
                            }
                        }
                    ]
                }
            
            elif method == "tools/call":
                result = handle_tools_call(params)
                response["result"] = result
            
            else:
                response["result"] = {}
            
            if "result" in response or "error" in response:
                output = json.dumps(response) + "\n"
                sys.stdout.write(output)
                sys.stdout.flush()
        
        except KeyboardInterrupt:
            logging.info("Shutdown requested")
            break
        except Exception as e:
            logging.error(f"Server error: {e}")
            if 'request_id' in locals() and request_id:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    main()
