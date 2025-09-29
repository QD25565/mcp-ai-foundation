#!/usr/bin/env python3
"""
WORLD MCP v3.0.0 - AI-FIRST TEMPORAL & SPATIAL CONTEXT
========================================================
Context that matters, nothing more. 80% token reduction.
Uses shared MCP utilities for consistency.
"""

import os
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Import shared utilities
from mcp_shared import (
    MCPServer, CURRENT_AI_ID, get_tool_data_dir,
    pipe_escape, create_tool_response
)

# Version
VERSION = "3.0.0"

# Configuration
OUTPUT_FORMAT = os.environ.get('WORLD_FORMAT', 'pipe')
DEFAULT_CONTEXT = os.environ.get('WORLD_DEFAULT', 'time,location').split(',')
WEATHER_THRESHOLD = 15

# Data directory
DATA_DIR = get_tool_data_dir('world')
LOCATION_FILE = DATA_DIR / "location.json"

# Global cache
location_cache = None
weather_cache = None
weather_cache_time = None
datetime_cache = {}
datetime_cache_second = None

def get_cached_datetime():
    """Cache datetime components within same second for efficiency"""
    global datetime_cache, datetime_cache_second
    now = datetime.now()
    current_second = now.replace(microsecond=0)
    
    if datetime_cache_second != current_second:
        time_format_12 = '%-I:%M%p' if os.name != 'nt' else '%#I:%M%p'
        
        datetime_cache = {
            'now': now,
            'iso': now.isoformat(),
            'unix': int(now.timestamp()),
            'day': now.strftime('%a'),
            'day_full': now.strftime('%A'),
            'date': now.strftime('%Y-%m-%d'),
            'date_nice': now.strftime('%b %-d' if os.name != 'nt' else '%b %#d'),
            'time_12': now.strftime(time_format_12),
            'time_24': now.strftime('%H:%M'),
            'month': now.strftime('%b'),
            'year': str(now.year),
            'hour': str(now.hour),
            'minute': str(now.minute)
        }
        datetime_cache_second = current_second
    
    return datetime_cache

def get_location():
    """Get location - from cache, file, or IP lookup"""
    global location_cache
    
    if location_cache:
        return location_cache
    
    # Try loading saved location
    if LOCATION_FILE.exists():
        try:
            import json
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
                    import json
                    with open(LOCATION_FILE, 'w', encoding='utf-8') as f:
                        json.dump(location_cache, f)
                except:
                    pass
                return location_cache
    except:
        pass
    
    return None

def get_weather():
    """Get weather using Open-Meteo"""
    global weather_cache, weather_cache_time
    
    # Cache weather for 10 minutes
    if weather_cache and weather_cache_time:
        if (datetime.now() - weather_cache_time).seconds < 600:
            return weather_cache
    
    location = get_location()
    
    if not location or not location.get("lat") or not location.get("lon"):
        weather_cache = {
            "temp_c": None,
            "description": None,
            "wind_kmh": None,
            "is_extreme": False
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
            
            weather_codes = {
                0: "clear", 1: "clear", 2: "cloudy", 3: "cloudy",
                45: "foggy", 48: "foggy",
                51: "drizzle", 53: "drizzle", 55: "drizzle",
                61: "rain", 63: "rain", 65: "heavy rain",
                71: "snow", 73: "snow", 75: "heavy snow",
                95: "storm", 96: "storm", 99: "storm"
            }
            
            code = curr.get("weathercode", 0)
            temp_c = curr.get("temperature", 0)
            wind = curr.get("windspeed", 0)
            
            is_extreme = (
                temp_c < 0 or temp_c > 30 or
                wind > WEATHER_THRESHOLD or
                code >= 65
            )
            
            weather_cache = {
                "temp_c": temp_c,
                "description": weather_codes.get(code, ""),
                "wind_kmh": wind if wind > WEATHER_THRESHOLD else None,
                "is_extreme": is_extreme
            }
            weather_cache_time = datetime.now()
            return weather_cache
    except:
        pass
    
    weather_cache = {
        "temp_c": None,
        "description": None,
        "wind_kmh": None,
        "is_extreme": False
    }
    weather_cache_time = datetime.now()
    return weather_cache

def format_location_short(location: dict) -> str:
    """Format location ultra-compactly"""
    if not location:
        return "?"
    
    city = location.get("city", "?")
    code = location.get("country_code", "")
    
    if city == "Unknown" or city == "?":
        return code if code else "?"
    
    return f"{city},{code}" if code else city

def build_context(include: List[str] = None, force_all: bool = False) -> str:
    """Build context string based on what's needed"""
    if include is None:
        include = DEFAULT_CONTEXT if not force_all else ['time', 'date', 'location', 'weather', 'identity']
    
    include = [item.lower().strip() for item in include]
    
    dt = get_cached_datetime()
    parts = []
    
    # Time/Date handling
    if 'time' in include and 'date' in include:
        parts.append(f"{dt['date']} {dt['time_24']}")
    elif 'time' in include:
        parts.append(dt['time_24'])
    elif 'date' in include:
        parts.append(dt['date'])
    
    # Location
    if 'location' in include:
        location = get_location()
        parts.append(format_location_short(location))
    
    # Weather (only if extreme or explicitly requested)
    if 'weather' in include:
        weather = get_weather()
        if weather['temp_c'] is not None:
            if force_all or weather['is_extreme']:
                w_parts = [f"{weather['temp_c']:.0f}°C"]
                if weather['description']:
                    w_parts.append(weather['description'])
                if weather['wind_kmh']:
                    w_parts.append(f"{weather['wind_kmh']:.0f}km/h")
                parts.append(' '.join(w_parts))
    
    # Unix timestamp
    if 'unix' in include:
        parts.append(str(dt['unix']))
    
    # Identity (only if explicitly requested)
    if 'identity' in include:
        parts.append(CURRENT_AI_ID)
    
    # Format based on output mode
    if OUTPUT_FORMAT == 'pipe':
        return '|'.join(pipe_escape(p) for p in parts)
    elif OUTPUT_FORMAT == 'json':
        import json
        result = {}
        for i, part in enumerate(parts):
            if i < len(include):
                result[include[i]] = part
        return json.dumps(result)
    else:
        return ' | '.join(parts) if len(parts) > 1 else parts[0] if parts else ""

# ============= TOOL FUNCTIONS =============

def world_command(compact: bool = None, **kwargs):
    """Get world context - ultra minimal by default"""
    if compact is None:
        compact = True
    
    if compact:
        return {"context": build_context(['time', 'location'])}
    else:
        return {"context": build_context(force_all=True)}

def datetime_command(compact: bool = None, **kwargs):
    """Get datetime - single line by default"""
    if compact is None:
        compact = True
    
    dt = get_cached_datetime()
    
    if compact:
        if OUTPUT_FORMAT == 'pipe':
            return {"datetime": f"{dt['date']}|{dt['time_24']}"}
        else:
            return {"datetime": f"{dt['date']} {dt['time_24']}"}
    else:
        if OUTPUT_FORMAT == 'pipe':
            return {"datetime": f"{dt['day']}|{dt['date']}|{dt['time_24']}|{dt['unix']}"}
        elif OUTPUT_FORMAT == 'json':
            import json
            return {"datetime": json.dumps({
                'day': dt['day'],
                'date': dt['date'],
                'time': dt['time_24'],
                'unix': dt['unix']
            })}
        else:
            return {"datetime": f"{dt['day']} {dt['date']} {dt['time_24']}"}

def weather_command(compact: bool = None, **kwargs):
    """Get weather - only notable conditions by default"""
    if compact is None:
        compact = True
    
    location = get_location()
    weather = get_weather()
    
    if compact:
        if weather['is_extreme'] and weather['temp_c'] is not None:
            loc = format_location_short(location)
            if OUTPUT_FORMAT == 'pipe':
                return {"weather": f"{loc}|{weather['temp_c']:.0f}°C|{weather['description']}"}
            else:
                return {"weather": f"{loc} {weather['temp_c']:.0f}°C {weather['description']}"}
        else:
            loc = format_location_short(location)
            if OUTPUT_FORMAT == 'pipe':
                return {"weather": f"{loc}|normal"}
            else:
                return {"weather": f"{loc} (normal conditions)"}
    else:
        loc = format_location_short(location)
        if weather['temp_c'] is not None:
            parts = [loc, f"{weather['temp_c']:.0f}°C", weather['description']]
            if weather['wind_kmh']:
                parts.append(f"{weather['wind_kmh']:.0f}km/h")
            
            if OUTPUT_FORMAT == 'pipe':
                return {"weather": '|'.join(parts)}
            else:
                return {"weather": ' '.join(parts)}
        else:
            return {"weather": f"{loc} (weather unavailable)"}

def context_command(include: List[str] = None, compact: bool = None, **kwargs):
    """Get specific context elements"""
    if compact is None:
        compact = True
    
    return {"context": build_context(include, force_all=not compact)}

def batch(operations: List[Dict] = None, **kwargs) -> Dict:
    """Execute multiple operations efficiently"""
    if operations is None:
        operations = kwargs.get('operations', [])
    
    if not operations:
        return {"error": "No operations"}
    
    if len(operations) > 10:
        return {"error": "Max 10 operations"}
    
    results = []
    op_map = {
        'world': world_command, 'w': world_command,
        'datetime': datetime_command, 'dt': datetime_command,
        'weather': weather_command, 'wx': weather_command,
        'context': context_command, 'ctx': context_command
    }
    
    for op in operations:
        op_type = op.get('type', '').lower()
        op_args = op.get('args', {})
        
        if op_type not in op_map:
            results.append(f"Unknown: {op_type}")
            continue
        
        result = op_map[op_type](**op_args)
        results.append(list(result.values())[0] if result else "")
    
    return {"batch_results": results}

# ============= MCP SERVER =============

def main():
    server = MCPServer("world", VERSION, "AI-First Context: 80% fewer tokens")
    
    # Register tools
    server.register_tool(
        world_command, "world",
        "Get context (time+location by default)",
        {"compact": {"type": "boolean", "description": "Compact mode (default: true)"}}
    )
    
    server.register_tool(
        datetime_command, "datetime",
        "Get date and time",
        {"compact": {"type": "boolean", "description": "Compact mode (default: true)"}}
    )
    
    server.register_tool(
        weather_command, "weather",
        "Get weather (only shows if extreme)",
        {"compact": {"type": "boolean", "description": "Compact mode (default: true)"}}
    )
    
    server.register_tool(
        context_command, "context",
        "Get specific context elements",
        {
            "include": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Elements: time, date, location, weather, identity, unix"
            },
            "compact": {"type": "boolean", "description": "Compact mode (default: true)"}
        }
    )
    
    server.register_tool(
        batch, "batch",
        "Execute multiple operations",
        {
            "operations": {
                "type": "array",
                "description": "List of operations",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "Operation type"},
                        "args": {"type": "object", "description": "Arguments"}
                    }
                }
            }
        },
        ["operations"]
    )
    
    # Custom result formatting
    def format_result(tool_name: str, result: Dict) -> str:
        if "error" in result:
            return f"Error: {result['error']}"
        elif "batch_results" in result:
            if OUTPUT_FORMAT == 'pipe':
                return '|'.join(str(r) for r in result['batch_results'])
            else:
                return '\n'.join(str(r) for r in result['batch_results'])
        else:
            return str(list(result.values())[0]) if result else ""
    
    server.format_tool_result = format_result
    
    # Run server
    server.run()

if __name__ == "__main__":
    main()
