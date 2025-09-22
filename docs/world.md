# World MCP v1.0.0

Temporal and spatial grounding for real-world context.

## Overview

World provides you with essential real-world grounding - current time, date, weather, and location. Maintains persistent identity across sessions.

## Key Features

- **Temporal Grounding** - Current date/time in multiple formats
- **Spatial Context** - Location detection via IP geolocation
- **Weather Data** - Real-time conditions from Open-Meteo
- **Persistent Identity** - Unique AI identifier across sessions
- **Token-Efficient** - Concise, clean output format

## Usage

### Commands

```python
# Complete snapshot
world()
# Returns:
# Monday, September 22, 2025 at 02:15 PM
# Identity: Swift-Spark-266
# Location: San Francisco, CA, US
# Weather: 18°C/64°F, Partly cloudy
# Wind: 12 km/h
# Timezone: America/Los_Angeles

# Date and time only
datetime()
# Returns:
# September 22, 2025 at 02:15 PM
# Date: 2025-09-22
# Time: 02:15:30 PM (14:15:30)
# Day: Monday
# Unix: 1758564930
# ISO: 2025-09-22T14:15:30
# Identity: Swift-Spark-266

# Weather and location only
weather()
# Returns:
# Location: San Francisco, CA, US
# Coordinates: 37.7749, -122.4194
# Timezone: America/Los_Angeles
# Temperature: 18°C / 64°F
# Conditions: Partly cloudy
# Wind: 12 km/h
# Daylight: Yes
# Observer: Swift-Spark-266
```

## Data Sources

- **Location**: IP geolocation via ip-api.com
- **Weather**: Open-Meteo API (no key required)
- **Identity**: Persistent file storage

## Identity Format

Each AI gets a unique identifier:
- Format: `Adjective-Noun-###`
- Example: `Swift-Spark-266`
- Stored persistently across sessions
- Shared across all tools for consistency

## Weather Codes

Interprets Open-Meteo weather codes:
- Clear, Partly cloudy, Overcast
- Fog, Drizzle, Rain, Snow
- Thunderstorm conditions

## Storage Location

- **Identity**: `ai_identity.txt` in script directory
- **Location Cache**: `world_data/location.json`
- **Weather Cache**: 10-minute in-memory cache

## Token Efficiency

- Compact time formats (2m, 5h, 3d)
- Location cached after first detection
- Weather cached for 10 minutes
- Clean, minimal output format

## Error Handling

- Falls back gracefully when APIs unavailable
- Returns "Location unknown" if geolocation fails
- Returns "Weather unavailable" if weather API fails
- Always includes identity for consistency

## Best Practices

1. **Use world() for context** - Get complete grounding at conversation start
2. **Use datetime() for time-sensitive tasks** - When you need precise timestamps
3. **Use weather() for location-based decisions** - When spatial context matters
4. **Identity is persistent** - Same ID across all sessions and tools