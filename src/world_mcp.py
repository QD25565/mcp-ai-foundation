#!/usr/bin/env python3
"""
WORLD MCP v1.0.0 - TEMPORAL & LOCATION GROUNDING
================================================
Tools for time, date, weather, and location.
Persistent AI identity for consistency.

Tools:
- world() - Complete snapshot: time, date, weather, location, identity
- datetime() - Temporal data only
- weather() - Weather and location only
================================================
"""

import json
import sys
import os
import logging
from datetime import datetime
from pathlib import Path
import requests
import random

# Version
VERSION = "1.0.0"

# Configure logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    stream=sys.stderr
)

# Storage for location persistence
BASE_DIR = Path.home() / "AppData" / "Roaming" / "Claude" / "tools"
DATA_DIR = BASE_DIR / "world_data"
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

def get_persistent_id():
    """Get or create persistent AI identity - shared across all tools"""
    # CRITICAL: Use BASE_DIR (Claude/tools/), not tool-specific dir
    id_file = Path.home() / "AppData" / "Roaming" / "Claude" / "tools" / "ai_identity.txt"
    
    # Fallback for permission issues
    if not os.access(Path.home() / "AppData" / "Roaming", os.W_OK):
        id_file = Path(os.environ.get('TEMP', '/tmp')) / "ai_identity.txt"
    
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
        id_file.parent.mkdir(parents=True, exist_ok=True)
        with open(id_file, 'w') as f:
            f.write(new_id)
        logging.info(f"Created new persistent identity: {new_id}")
    except Exception as e:
        logging.error(f"Error saving identity file: {e}")
    
    return new_id

# Get ID from environment or persistent storage
CURRENT_AI_ID = os.environ.get('AI_ID', get_persistent_id())

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

def world_command():
    """Get everything - concise summary with identity"""
    now = datetime.now()
    location = get_location()
    weather = get_weather()
    
    # Build location string
    if location:
        loc_parts = []
        if location.get("city") and location["city"] != "Unknown":
            loc_parts.append(location["city"])
        if location.get("region") and location["region"] not in ["Unknown", "", location.get("city")]:
            loc_parts.append(location["region"]) 
        if location.get("country_code"):
            loc_parts.append(location["country_code"])
        location_str = ", ".join(loc_parts) if loc_parts else "Location unknown"
    else:
        location_str = "Location unknown"
    
    # Build output
    lines = []
    lines.append(f"{now.strftime('%A, %B %d, %Y at %I:%M %p')}")
    lines.append(f"Identity: {CURRENT_AI_ID}")  # Add identity for consistency
    lines.append(f"Location: {location_str}")
    
    if weather["temp_c"] is not None:
        lines.append(f"Weather: {weather['temp_c']:.0f}°C/{weather['temp_f']:.0f}°F, {weather['description']}")
        lines.append(f"Wind: {weather['wind_speed_kmh']} km/h")
    else:
        lines.append("Weather: Not available")
    
    if location and location.get("timezone"):
        lines.append(f"Timezone: {location['timezone']}")
    
    return "\n".join(lines)

def datetime_command():
    """Get date and time - essential formats only"""
    now = datetime.now()
    
    lines = []
    lines.append(f"{now.strftime('%B %d, %Y at %I:%M %p')}")
    lines.append(f"Date: {now.strftime('%Y-%m-%d')}")
    lines.append(f"Time: {now.strftime('%I:%M:%S %p')} ({now.strftime('%H:%M:%S')})")
    lines.append(f"Day: {now.strftime('%A')}")
    lines.append(f"Unix: {int(now.timestamp())}")
    lines.append(f"ISO: {now.isoformat()}")
    lines.append(f"Identity: {CURRENT_AI_ID}")  # Include identity even in datetime
    
    return "\n".join(lines)

def weather_command():
    """Get weather and location"""
    location = get_location()
    weather = get_weather()
    
    lines = []
    
    # Location
    if location:
        loc_parts = []
        if location.get("city") and location["city"] != "Unknown":
            loc_parts.append(location["city"])
        if location.get("region") and location["region"] not in ["Unknown", "", location.get("city")]:
            loc_parts.append(location["region"])
        if location.get("country_code"):
            loc_parts.append(location["country_code"])
        location_str = ", ".join(loc_parts) if loc_parts else "Location unknown"
        
        lines.append(f"Location: {location_str}")
        
        if location.get("lat") and location.get("lon"):
            lines.append(f"Coordinates: {location['lat']:.4f}, {location['lon']:.4f}")
        
        if location.get("timezone"):
            lines.append(f"Timezone: {location['timezone']}")
    else:
        lines.append("Location: Unknown (IP geolocation failed)")
        lines.append("Tip: Location will be cached once detected")
    
    # Weather
    if weather["temp_c"] is not None:
        lines.append(f"Temperature: {weather['temp_c']:.0f}°C / {weather['temp_f']:.0f}°F")
        lines.append(f"Conditions: {weather['description']}")
        lines.append(f"Wind: {weather['wind_speed_kmh']} km/h")
        if weather["is_day"] is not None:
            lines.append(f"Daylight: {'Yes' if weather['is_day'] else 'No'}")
    else:
        lines.append("Weather: Not available")
    
    lines.append(f"Observer: {CURRENT_AI_ID}")  # Include identity
    
    return "\n".join(lines)

def handle_tools_call(params):
    """Route tool calls"""
    tool_name = params.get("name", "")
    tool_lower = tool_name.lower().strip()
    
    # Match tool names
    if any(word in tool_lower for word in ['world', 'all', 'everything', 'full']):
        return world_command()
    elif any(word in tool_lower for word in ['datetime', 'date', 'time', 'clock', 'now', 'when']):
        return datetime_command()
    elif any(word in tool_lower for word in ['weather', 'temp', 'climate', 'forecast', 'conditions']):
        return weather_command()
    else:
        return world_command()  # Default

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
                        "description": "Time, date, weather, and location grounding with persistent identity"
                    }
                }
            
            elif method == "notifications/initialized":
                continue
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "world",
                            "description": "Get current date, time, weather, and location",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "datetime",
                            "description": "Get current date and time",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "weather",
                            "description": "Get current weather and location",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            
            elif method == "tools/call":
                result_text = handle_tools_call(params)
                response["result"] = {
                    "content": [{
                        "type": "text",
                        "text": result_text
                    }]
                }
            
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
