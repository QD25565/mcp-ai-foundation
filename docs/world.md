# World MCP Tool v3.0

Ultra-minimal contextual awareness with 80% token reduction. Time, location, and weather when it matters.

## Overview

World provides AI assistants with temporal and spatial context using minimal tokens. Version 3.0 delivers just the essential data - no decoration, no fluff, just pure context.

## Features

### Core Capabilities
- **Minimal Output**: Single line, pipe-delimited format
- **Smart Weather**: Only shows when extreme/notable
- **Contextual Time**: Multiple format options
- **Persistent Location**: Remembers across sessions
- **Batch Operations**: Multiple queries in one call
- **Format Flexibility**: Pipe, JSON, or text output

### v3.0 Improvements
- **80% Token Reduction**: From verbose to minimal
- **Single-Line Default**: Everything on one line
- **Weather Threshold**: Only extreme conditions shown
- **No Decorative Text**: Pure data output
- **Unified Format**: Consistent across all commands

## Usage

### Basic Operations

#### World (Default Context)
```python
world:world
  compact: true  # Default: true
```

**Output (pipe format)**:
```
17:54|Melbourne,AU
```

Only time and location by default - the essentials.

#### Date/Time
```python
world:datetime
  compact: true  # Default: true
```

**Output (compact)**:
```
2025-09-25|17:54
```

**Output (full)**:
```
Thu|2025-09-25|17:54|1758786916
```

#### Weather
```python
world:weather
  compact: true  # Default: true
```

**Output (normal conditions)**:
```
Melbourne,AU|normal
```

**Output (extreme conditions)**:
```
Melbourne,AU|38°C|storm|25km/h
```

Weather only shows details when:
- Temperature < 0°C or > 30°C
- Wind speed > 15 km/h  
- Severe conditions (storm, heavy rain, snow)

#### Custom Context
```python
world:context
  include: ["time", "date", "location", "weather", "identity", "unix"]
  compact: true
```

Choose exactly what context you need.

### Batch Operations

Execute multiple context queries efficiently:

```python
world:batch
  operations: [
    {type: "datetime", args: {compact: false}},
    {type: "weather", args: {}},
    {type: "context", args: {include: ["unix"]}}
  ]
```

**Output**:
```
Thu|2025-09-25|17:55|1758786916|Melbourne,AU|normal|1758786916
```

## Configuration

### Environment Variables

```bash
# Output format: 'pipe' (default), 'json', or 'text'
export WORLD_FORMAT=pipe

# Default context elements (comma-separated)
export WORLD_DEFAULT=time,location

# Weather threshold (km/h for wind)
export WEATHER_THRESHOLD=15

# Custom AI identity
export AI_ID=Assistant-001
```

### Storage Location
- **Windows**: `%APPDATA%\Claude\tools\world_data\`
- **macOS/Linux**: `~/.claude/tools/world_data/`
- **Fallback**: System temp directory

### Persisted Data
- `location.json` - Saved location data
- `ai_identity.txt` - Persistent AI ID

## Output Formats

### Pipe Format (Default)
Most efficient - 80% token reduction:
```
17:54|Melbourne,AU
```

### JSON Format
Structured data when needed:
```json
{
  "time": "17:54",
  "location": "Melbourne,AU"
}
```

### Text Format
Human-readable with separators:
```
17:54 | Melbourne,AU
```

## Context Elements

### Available Elements

| Element | Compact Output | Full Output | Description |
|---------|---------------|-------------|-------------|
| time | `17:54` | `17:54:32` | Current time (24h) |
| date | `2025-09-25` | `Thursday, September 25, 2025` | Current date |
| location | `Melbourne,AU` | `Melbourne, Victoria, Australia` | City and country |
| weather | (hidden if normal) | `23°C cloudy 10km/h` | Only if notable |
| identity | `Swift-Core-368` | `AI: Swift-Core-368` | AI identifier |
| unix | `1758786916` | `Unix: 1758786916` | Unix timestamp |

### Default Context
By default, includes only:
- Time (24-hour format)
- Location (city, country code)

### Weather Intelligence
Weather appears automatically when extreme:
- **Heat**: > 30°C
- **Cold**: < 0°C
- **Wind**: > 15 km/h
- **Conditions**: Storm, heavy rain, snow, fog

## Location System

### IP Geolocation
Automatically detects location via IP on first run:
```json
{
  "city": "Melbourne",
  "region": "Victoria", 
  "country": "Australia",
  "country_code": "AU",
  "lat": -37.814,
  "lon": 144.963,
  "timezone": "Australia/Melbourne"
}
```

### Persistence
Location saved after first detection - no repeated lookups.

### Manual Override
Create/edit `world_data/location.json`:
```json
{
  "city": "Tokyo",
  "country_code": "JP",
  "lat": 35.6762,
  "lon": 139.6503
}
```

## Time Formats

### Compact Mode
- Time: `17:54` (24-hour)
- Date: `2025-09-25` (ISO)
- Combined: `2025-09-25|17:54`

### Full Mode
- Time: `17:54:32` (with seconds)
- Date: `Thursday, September 25, 2025`
- Day: `Thu` or `Thursday`
- Unix: `1758786916`

### Platform-Specific
- Windows: `5:54PM` (12-hour without leading zero)
- Unix/Mac: `5:54PM` (platform-aware formatting)

## Weather Data

### Open-Meteo API
Free, no-auth weather service:
- Current conditions
- Temperature in Celsius
- Wind speed in km/h
- Weather codes (0-99)

### Weather Codes
- 0-3: Clear/Partly cloudy
- 45-48: Foggy
- 51-55: Drizzle
- 61-65: Rain
- 71-75: Snow
- 95-99: Thunderstorm

### Caching
Weather cached for 10 minutes to reduce API calls.

## Performance

### Optimization Features
- **Single-Line Output**: Minimal parsing needed
- **Lazy Weather**: Only fetched when requested/extreme
- **Location Cache**: One-time geolocation
- **Component Cache**: DateTime cached per second
- **Batch Support**: Up to 10 operations per call

### Token Efficiency
- **Default**: `17:54|Melbourne,AU` (19 characters)
- **Previous v2**: `{"time": "17:54", "location": {"city": "Melbourne", "country": "AU"}}` (70+ characters)
- **Reduction**: 80% fewer tokens

## Examples

### Minimal Context
```python
# Just the basics
world()
# Output: 17:54|Melbourne,AU

# Just time
context(include=["time"])
# Output: 17:54

# Just date
context(include=["date"])  
# Output: 2025-09-25
```

### Weather Awareness
```python
# Normal day (23°C, light wind)
weather()
# Output: Melbourne,AU|normal

# Hot day (38°C, strong wind)
weather()
# Output: Melbourne,AU|38°C|clear|25km/h

# Storm conditions
weather()
# Output: Melbourne,AU|22°C|storm|35km/h
```

### Full Context
```python
# Everything available
world(compact=false)
# Output: Thu|2025-09-25|17:54|1758786916|Melbourne,AU|23°C|cloudy|Swift-Core-368

# Or via context
context(include=["time", "date", "location", "weather", "identity", "unix"])
```

### Batch Efficiency
```python
# Multiple queries, one call
batch(operations=[
  {type: "w"},      # World (short alias)
  {type: "dt"},     # DateTime
  {type: "wx"},     # Weather
  {type: "ctx", args: {include: ["unix"]}}  # Context
])
```

## Best Practices

1. **Use Compact Mode**: Default is optimal for most cases
2. **Trust Weather Logic**: It knows when conditions matter
3. **Batch When Possible**: Reduce call overhead
4. **Cache Location**: Let it persist, don't re-detect
5. **Pick Your Format**: Pipe for efficiency, JSON for structure

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No location | Check internet, will use "Unknown" as fallback |
| Weather unavailable | Open-Meteo may be down, continues without weather |
| Wrong timezone | Update location.json with correct timezone |
| Identity changes | Check AI_ID environment variable |

### Debug Mode
```bash
# Enable debug logging
export WORLD_DEBUG=1
```

## Version History

### v3.0.0 (Current)
- 80% token reduction
- Pipe format by default
- Single-line output
- Weather thresholds
- Format configuration

### v2.0.0
- Added weather support
- Location persistence
- Identity management

### v1.0.0
- Initial release
- Basic time/location

---

Context without the clutter. Every token counts.
