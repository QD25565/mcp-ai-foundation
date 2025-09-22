# World MCP v2.0.0

Temporal and spatial grounding with optimized token efficiency.

## Overview

World provides essential real-world context - time, date, weather, and location. v2.0.0 introduces 60-85% token reduction through smart formatting, batch operations, and selective context retrieval.

## Key Features

- **Token-Efficient** - Reduced output by 60-85% from v1.0.0
- **Batch Operations** - Multiple operations in single call
- **Selective Context** - Request only needed elements
- **Compact Modes** - Ultra-minimal single-line outputs
- **Persistent Identity** - Unique AI identifier across sessions
- **Smart Caching** - Datetime cached within same second

## Usage

### Commands

```python
# Complete snapshot
world()
# Returns (4 lines, 64 chars):
# Mon, Sep 22, 2025 11:08 PM
# Melbourne, AU
# 11°C Partly cloudy
# Sharp-Core-368

# Compact mode
world(compact=True)
# Returns (1 line, 62 chars):
# Mon 23:09 | Melbourne, AU 11°C partly cloudy | Sharp-Core-368

# Date and time
datetime()
# Returns (7 lines):
# Sep 22, 2025 11:09 PM
# 2025-09-22
# 11:09:58 PM (23:09:58)
# Mon
# 1758546598
# 2025-09-22T23:09:58.042618
# Sharp-Core-368

# Compact datetime
datetime(compact=True)
# Returns (1 line, 21 chars):
# Mon 2025-09-22 23:10

# Weather
weather(compact=True)
# Returns (1 line):
# Melbourne AU 11°C partly cloudy

# Selective context - pick exactly what you need
context(include=["time", "identity"], compact=True)
# Returns: 23:09 | Sharp-Core-368

context(include=["date", "weather", "location"])
# Returns:
# Sep 22, 2025
# 11°C Partly cloudy
# Melbourne, AU

# Batch operations - multiple in one call
batch([
    {"type": "datetime", "args": {"compact": True}},
    {"type": "weather", "args": {"compact": True}},
    {"type": "context", "args": {"include": ["unix"], "compact": True}}
])
# Returns all three results in one response
```

## Context Function Options

The `context()` function accepts an `include` parameter with any combination of:
- `time` - Current time
- `date` - Current date
- `weather` - Temperature and conditions
- `location` - City and country
- `identity` - AI identifier
- `unix` - Unix timestamp

## v2.0.0 Improvements

### Token Reduction
- Removed redundant prefixes ("Identity:", "Location:", etc.)
- Abbreviated day/month names (Monday → Mon, January → Jan)
- Removed leading zeros (03:45 PM → 3:45 PM)
- Removed Fahrenheit (redundant for most users)
- Removed timezone (inferrable from location)
- Only shows wind when notable (>15 km/h)

### Efficiency Gains
| Function | v1.0.0 | v2.0.0 Standard | v2.0.0 Compact |
|----------|---------|-----------------|----------------|
| world() | 178 chars | 64 chars (-64%) | 62 chars (-65%) |
| datetime() | 146 chars | 109 chars (-25%) | 21 chars (-86%) |
| weather() | 135 chars | 50 chars (-63%) | 34 chars (-75%) |

## Data Sources

- **Location**: IP geolocation via ip-api.com
- **Weather**: Open-Meteo API (no key required)
- **Identity**: Persistent file storage

## Storage

- **Identity**: `world_data/ai_identity.txt`
- **Location Cache**: `world_data/location.json`
- **Weather Cache**: 10-minute in-memory cache

## Best Practices

1. **Use compact mode** when tokens matter most
2. **Use context()** when you only need specific elements
3. **Use batch()** for multiple operations to reduce overhead
4. **Cache datetime calls** - results cached within same second
5. **world()** at conversation start for full grounding
6. **context(include=["time"])** for just timestamps