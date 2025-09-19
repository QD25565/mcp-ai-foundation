# Token Optimization Guide for MCP Tools

## Overview

Through developing these tools, we discovered practical techniques for reducing token usage by 35-40% while maintaining full functionality. This guide shares those discoveries for developers building their own MCP tools.

## Key Discoveries

### Where Real Token Savings Come From

#### High-Impact Optimizations (Save 100s-1000s tokens)

1. **Content Truncation (Biggest Wins)**
   ```python
   # Bad: Return everything
   return {"notes": all_notes}  # Could be 10,000+ tokens
   
   # Good: Smart preview with full access option
   return {"notes": truncated_preview}  # 500 tokens
   # Plus separate: get_full_note(id) when needed
   ```

2. **Metadata Deduplication (20-30 tokens per item)**
   ```python
   # Bad: Repeat session ID for every note
   notes = [
     {"id": 1, "content": "...", "session": "20250919_101530"},
     {"id": 2, "content": "...", "session": "20250919_101530"},  # Redundant!
   ]
   
   # Good: Only store when it changes
   notes = [
     {"id": 1, "content": "...", "session": "20250919_101530"},
     {"id": 2, "content": "..."},  # Session implied from previous
   ]
   ```

3. **Smart Time Formatting (8-10 tokens per timestamp)**
   ```python
   # Bad: Full ISO timestamp
   "2025-09-19T10:03:44.049355"  # 28 characters
   
   # Good: Contextual format
   "@10:03"     # Today
   "@y10:03"    # Yesterday
   "@3d"        # 3 days ago
   "@9/15"      # Older dates
   ```

#### Low-Impact Optimizations (Save 1-2 tokens)

Field abbreviation provides minimal benefit:
```python
# Saves only 1 token
"message" vs "msg"
"content" vs "c"
```

Unless you're using single-letter keys throughout (which hurts readability), don't bother with abbreviations.

## The 99/1 Rule

Design your tools around this principle:
- **99% of use cases** need efficient, truncated previews
- **1% of use cases** need full content access

Implementation:
```python
class NotebookTool:
    def get_status(self):
        # 99% case: Smart preview
        return truncated_recent_notes[:5000]  
    
    def get_full_note(self, id):
        # 1% case: Complete content
        return complete_note_content
```

## Smart Truncation Algorithms

### Content-Aware Truncation

```python
def smart_truncate(text: str, max_chars: int) -> str:
    """Truncate intelligently based on content type"""
    
    # Detect content type
    code_indicators = ['```', 'def ', 'class ', 'import ', '{']
    is_code = any(indicator in text[:200] for indicator in code_indicators)
    
    if is_code and max_chars > 100:
        # For code: Show beginning and end
        start_chars = int(max_chars * 0.65)
        end_chars = max_chars - start_chars - 5
        return text[:start_chars] + "\n...\n" + text[-end_chars:]
    else:
        # For prose: Clean cutoff at word boundary
        cutoff = text.rfind(' ', 0, max_chars - 3)
        if cutoff == -1 or cutoff < max_chars * 0.8:
            cutoff = max_chars - 3
        return text[:cutoff] + "..."
```

### Proportional Space Distribution

When showing multiple items with a total character limit:

```python
def distribute_preview_space(items, total_chars=5000):
    """Distribute available space intelligently"""
    results = []
    remaining_chars = total_chars
    items_left = len(items)
    
    for item in items:
        if remaining_chars <= 0:
            break
            
        # Allocate space proportionally to remaining items
        max_for_this_item = min(
            800,  # Cap per item
            remaining_chars // max(1, items_left)
        )
        
        truncated = smart_truncate(item.content, max_for_this_item)
        results.append(truncated)
        remaining_chars -= len(truncated)
        items_left -= 1
    
    return results
```

## Compact JSON Storage

### Internal Storage Format

Use single-letter keys internally, but transform for display:

```python
# Internal storage (compact)
note = {
    "s": 123,        # sequence
    "c": "content",  # content
    "t": "2025-...", # timestamp
}

# Display format (readable)
display = {
    "id": note["s"],
    "content": note["c"],
    "time": format_time_contextual(note["t"])
}
```

### Efficient Serialization

```python
# Compact JSON (no extra whitespace)
json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

# vs Default (adds unnecessary whitespace)
json.dump(data, f, indent=2)  # Pretty but costly!
```

## MCP-Specific Optimizations

### Handle Tool Name Prefixes

MCP sends tool names with prefixes that must be stripped:

```python
def handle_tools_call(params):
    tool_name = params.get("name", "").lower()
    
    # MCP sends "notebook:get_full_note"
    # Must strip prefix for string matching
    if ":" in tool_name:
        tool_name = tool_name.split(":", 1)[1]
    
    # Now can match properly
    if "get_full_note" in tool_name:
        return get_full_note(params.get("arguments"))
```

## Data Migration Strategy

When optimizing existing tools:

1. **Start Fresh (Recommended)**
   - Delete old data files
   - Begin with optimized format
   - No migration complexity

2. **Gradual Migration**
   - Support both old and new field names
   - Convert on load
   - Save in new format

## Common Pitfalls to Avoid

### 1. Over-Abbreviation
```python
# Bad: Unreadable
{"i": 1, "c": "...", "t": "...", "s": "..."}

# Good: Balance readability and efficiency
{"id": 1, "content": "...", "time": "..."}
```

### 2. Truncating Without Access Path
```python
# Bad: Data is truncated with no way to get full version
return truncated_content[:100]

# Good: Provide both preview and full access
def get_preview(): return truncated[:100]
def get_full(id): return complete_content
```

### 3. Not Caching Expensive Operations
```python
# Bad: Reformat every time
def get_time():
    return format_complex_timestamp(note["timestamp"])

# Good: Format once and cache
if "formatted_time" not in note:
    note["formatted_time"] = format_complex_timestamp(note["timestamp"])
return note["formatted_time"]
```

## Measuring Token Usage

### Quick Estimation

- Average English word: ~1.3 tokens
- Timestamp: ~15-20 tokens
- JSON structure overhead: ~2-5 tokens per field
- Whitespace in JSON: ~1 token per indentation level

### Actual Measurement

```python
def estimate_tokens(text):
    """Rough token estimation"""
    # Approximate - actual tokenization is more complex
    words = len(text.split())
    chars = len(text)
    
    # Use higher of word or character estimate
    word_estimate = words * 1.3
    char_estimate = chars / 4
    
    return int(max(word_estimate, char_estimate))
```

## Results You Can Expect

Applying these optimizations to our MCP tools resulted in:

- **Notebook**: 35-40% reduction (from ~3000 to ~1800 tokens for typical session)
- **Task Manager**: 40% reduction (from ~2000 to ~1200 tokens for 20 tasks)
- **World**: 20% reduction (already minimal, mainly formatting gains)

## Summary

Token optimization is about smart defaults and escape hatches:

1. **Show previews by default** (99% of uses)
2. **Provide full access when needed** (1% of uses)
3. **Remove redundancy** (dedup metadata)
4. **Format contextually** (relative times)
5. **Truncate intelligently** (content-aware)

Remember: The goal isn't to make the code unreadable, but to transmit the same information in fewer tokens while maintaining full functionality.

---

*"Every token saved is a thought preserved."*