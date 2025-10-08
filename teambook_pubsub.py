#!/usr/bin/env python3
"""
TEAMBOOK MCP - REDIS PUB/SUB LAYER
=====================================================
Real-time event notifications for AI collaboration.
Enables wait_for_event(), hooks, and eliminates polling.

Built by AIs, for AIs.
=====================================================
"""

import redis
import json
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timezone
from teambook_shared import CURRENT_AI_ID, CURRENT_TEAMBOOK

# ============= AUTO-TRIGGERS INTEGRATION =============
try:
    from teambook_auto_triggers import fire_hooks
    _HOOKS_AVAILABLE = True
except ImportError:
    _HOOKS_AVAILABLE = False
    fire_hooks = None

# ============= REDIS CONNECTION =============
_redis_client: Optional[redis.Redis] = None
_pubsub: Optional[redis.client.PubSub] = None
_subscriber_thread: Optional[threading.Thread] = None
_event_handlers: Dict[str, List[Callable]] = {}
_running = False

def get_redis_client() -> redis.Redis:
    """Get or create Redis client connection"""
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,  # Auto-decode bytes to strings
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            _redis_client.ping()
            logging.info("✅ Redis connected")
        except Exception as e:
            logging.error(f"❌ Redis connection failed: {e}")
            logging.error("   Make sure Redis is running: docker-compose up -d")
            raise
    
    return _redis_client

def close_redis():
    """Close Redis connections"""
    global _redis_client, _pubsub, _subscriber_thread, _running
    
    _running = False
    
    if _pubsub:
        try:
            _pubsub.close()
        except:
            pass
        _pubsub = None
    
    if _subscriber_thread and _subscriber_thread.is_alive():
        _subscriber_thread.join(timeout=2)
    
    if _redis_client:
        try:
            _redis_client.close()
        except:
            pass
        _redis_client = None
    
    logging.info("Redis connections closed")

# ============= PUB/SUB CHANNELS =============

def get_channel_name(channel_type: str, detail: str = "") -> str:
    """Generate standardized channel names"""
    teambook = CURRENT_TEAMBOOK or "_private"
    
    if channel_type == "note_created":
        return f"teambook:{teambook}:note:created"
    elif channel_type == "note_updated":
        return f"teambook:{teambook}:note:updated"
    elif channel_type == "message":
        return f"teambook:{teambook}:message:{detail}"  # detail = AI ID
    elif channel_type == "broadcast":
        return f"teambook:{teambook}:broadcast:{detail}"  # detail = channel name
    elif channel_type == "dm":
        return f"teambook:{teambook}:dm:{detail}"  # detail = recipient AI ID
    else:
        return f"teambook:{teambook}:{channel_type}"

# ============= PUBLISHING EVENTS =============

def publish_event(event_type: str, data: Dict[str, Any], detail: str = ""):
    """Publish an event to Redis"""
    try:
        client = get_redis_client()
        channel = get_channel_name(event_type, detail)
        
        # Add metadata
        event_data = {
            "type": event_type,
            "data": data,
            "author": CURRENT_AI_ID,
            "teambook": CURRENT_TEAMBOOK or "_private",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Publish to Redis
        client.publish(channel, json.dumps(event_data))
        logging.debug(f"📤 Published {event_type} to {channel}")
        
    except Exception as e:
        logging.error(f"Failed to publish event: {e}")

def publish_note_created(note_id: int, content: str, summary: str):
    """Publish note creation event"""
    publish_event("note_created", {
        "note_id": note_id,
        "content": content[:200],  # Truncated for efficiency
        "summary": summary
    })

def publish_note_updated(note_id: int, changes: Dict[str, Any]):
    """Publish note update event"""
    publish_event("note_updated", {
        "note_id": note_id,
        "changes": changes
    })

def publish_direct_message(to_ai: str, content: str):
    """Publish direct message"""
    publish_event("dm", {
        "from": CURRENT_AI_ID,
        "content": content
    }, detail=to_ai)

def publish_broadcast(channel: str, content: str):
    """Publish broadcast message"""
    publish_event("broadcast", {
        "channel": channel,
        "content": content
    }, detail=channel)

# ============= SUBSCRIBING TO EVENTS =============

def subscribe_to_channel(channel_type: str, detail: str = "", handler: Optional[Callable] = None):
    """Subscribe to a Redis channel"""
    global _pubsub, _subscriber_thread, _running
    
    try:
        client = get_redis_client()
        
        if _pubsub is None:
            _pubsub = client.pubsub()
            _running = True
        
        # Use pattern subscription for event types that need wildcards
        use_pattern = (channel_type in ['broadcast', 'dm'] and detail == "")
        
        if use_pattern:
            # Subscribe to ALL channels of this type using pattern
            pattern = get_channel_name(channel_type, "*")
            
            # Add handler to registry with pattern key
            if handler:
                if pattern not in _event_handlers:
                    _event_handlers[pattern] = []
                _event_handlers[pattern].append(handler)
            
            # Subscribe using psubscribe for patterns
            _pubsub.psubscribe(pattern)
            logging.info(f"📥 Pattern subscribed to {pattern}")
        else:
            # Normal subscription to specific channel
            channel = get_channel_name(channel_type, detail)
            
            # Add handler to registry
            if handler:
                if channel not in _event_handlers:
                    _event_handlers[channel] = []
                _event_handlers[channel].append(handler)
            
            # Subscribe to channel
            _pubsub.subscribe(channel)
            logging.info(f"📥 Subscribed to {channel}")
        
        # Start subscriber thread if not running
        if _subscriber_thread is None or not _subscriber_thread.is_alive():
            _subscriber_thread = threading.Thread(target=_message_listener, daemon=True)
            _subscriber_thread.start()
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to subscribe: {e}")
        return False

def unsubscribe_from_channel(channel_type: str, detail: str = ""):
    """Unsubscribe from a Redis channel"""
    global _pubsub
    
    if _pubsub is None:
        return
    
    try:
        channel = get_channel_name(channel_type, detail)
        _pubsub.unsubscribe(channel)
        
        # Remove handlers
        if channel in _event_handlers:
            del _event_handlers[channel]
        
        logging.info(f"Unsubscribed from {channel}")
        
    except Exception as e:
        logging.error(f"Failed to unsubscribe: {e}")

def _message_listener():
    """Background thread that listens for messages"""
    global _pubsub, _running
    
    logging.info("🎧 Message listener started")
    
    while _running and _pubsub:
        try:
            message = _pubsub.get_message(timeout=1.0)
            if not message:
                continue
            
            # Handle both regular messages and pattern messages
            msg_type = message['type']
            if msg_type not in ['message', 'pmessage']:
                continue
            
            # Extract channel and data
            if msg_type == 'pmessage':
                pattern = message['pattern']
                channel = message['channel']
                data = json.loads(message['data'])
            else:
                channel = message['channel']
                data = json.loads(message['data'])
                pattern = None
            
            logging.debug(f"📨 Received message on {channel}")
            
            # Fire auto-trigger hooks for this event
            if _HOOKS_AVAILABLE and fire_hooks:
                try:
                    # Determine hook type from channel name
                    if ':broadcast:' in channel:
                        hook_type = 'on_broadcast'
                    elif ':dm:' in channel:
                        hook_type = 'on_dm'
                    elif ':note:created' in channel:
                        hook_type = 'on_note_created'
                    elif ':note:updated' in channel:
                        hook_type = 'on_note_edited'
                    else:
                        hook_type = None
                    
                    if hook_type:
                        # Extract trigger data from event
                        trigger_data = data.get('data', {})
                        trigger_data['from_ai'] = data.get('author')
                        trigger_data['timestamp'] = data.get('timestamp')
                        
                        # Fire matching hooks
                        fire_hooks(hook_type, trigger_data)
                except Exception as e:
                    logging.error(f"Hook firing error: {e}")
            
            # Call registered handlers - check both exact channel and pattern
            handlers_to_call = []
            
            # Exact channel match
            if channel in _event_handlers:
                handlers_to_call.extend(_event_handlers[channel])
            
            # Pattern match
            if pattern and pattern in _event_handlers:
                handlers_to_call.extend(_event_handlers[pattern])
            
            # Execute all matching handlers
            for handler in handlers_to_call:
                try:
                    handler(data)
                except Exception as e:
                    logging.error(f"Handler error: {e}")
                        
        except Exception as e:
            if _running:  # Only log if we're supposed to be running
                logging.error(f"Message listener error: {e}")
            time.sleep(0.1)
    
    logging.info("🎧 Message listener stopped")

# ============= WAIT FOR EVENT (THE KILLER FEATURE) =============

def wait_for_event(event_type: str, timeout: int = 60, filter_func: Optional[Callable] = None) -> Optional[Dict]:
    """
    Wait for a specific event to occur.

    This is the feature that makes QD___ not a message bus!
    AIs can now wait for events instead of polling or having QD___ relay messages.

    Args:
        event_type: Type of event to wait for (note_created, message, etc.)
        timeout: Maximum seconds to wait (default 60)
        filter_func: Optional function to filter events (return True to accept)

    Returns:
        Event data dict if event occurred, None if timeout

    Example:
        # Wait for a specific note to be created
        event = wait_for_event("note_created",
                               timeout=30,
                               filter_func=lambda e: e['data']['note_id'] == 123)
    """
    # Convert timeout to int if it comes as string from CLI
    timeout = int(timeout) if isinstance(timeout, str) else timeout

    received_event = {'data': None}
    event_received = threading.Event()

    def event_handler(data: Dict):
        """Handler that captures the event"""
        # Apply filter if provided
        if filter_func and not filter_func(data):
            return

        received_event['data'] = data
        event_received.set()

    # Subscribe to channel with handler
    subscribe_to_channel(event_type, handler=event_handler)

    try:
        # Wait for event or timeout
        if event_received.wait(timeout=timeout):
            logging.info(f"✅ Event received: {event_type}")
            return received_event['data']
        else:
            logging.info(f"⏱️ Timeout waiting for {event_type}")
            return None
    finally:
        # Clean up subscription
        # Note: We don't unsubscribe here because other code might still need it
        pass

def standby(timeout: int = 300, ai_name: str = None) -> Optional[Dict]:
    """
    Enter standby mode - wake on ANY relevant activity.

    This is the FORGIVING mode QD___ requested. AIs wake up when:
    - Direct messages to them
    - Broadcasts mentioning their name or @mention
    - Tasks assigned to them
    - Notes mentioning them
    - General help requests in broadcasts

    Args:
        timeout: Maximum seconds to wait (default 300 = 5 minutes)
        ai_name: AI name to watch for (defaults to CURRENT_AI_ID)

    Returns:
        Event data dict with wake reason, or None if timeout

    Example:
        # Go into standby, wake on any relevant activity
        event = standby(timeout=600)  # 10 minute standby
        if event:
            print(f"Woke up because: {event['wake_reason']}")
    """
    timeout = int(timeout) if isinstance(timeout, str) else timeout
    ai_name = ai_name or CURRENT_AI_ID

    # Variations of the AI name to watch for
    name_variations = [
        ai_name,
        ai_name.lower(),
        ai_name.replace('-', ' '),
        ai_name.replace('claude-instance-', 'instance-'),
        ai_name.replace('claude-instance-', 'instance '),
        ai_name.replace('claude-instance-', 'i-'),
    ]

    # Add friendly names if known (Cascade, Sage, Lyra, Resonance, Weaver)
    friendly_names = {
        'claude-instance-1': ['sage', 'instance-1', 'i-1', 'instance 1'],
        'claude-instance-2': ['cascade', 'instance-2', 'i-2', 'instance 2'],
        'claude-instance-3': ['lyra', 'instance-3', 'i-3', 'instance 3'],
        'claude-instance-4': ['resonance', 'instance-4', 'i-4', 'instance 4'],
        'claude-desktop': ['weaver', 'desktop', 'claude-desktop'],
    }
    if ai_name in friendly_names:
        name_variations.extend(friendly_names[ai_name])

    # SMART STANDBY KEYWORDS - Wake on collaboration signals
    help_keywords = [
        # Help/Assistance
        'help', 'assist', 'assistance', 'need', 'needed',
        'anyone', 'anybody', 'someone', 'available',
        'wake up', 'wake', 'ping',

        # Coordination
        'verify', 'review', 'check', 'validate', 'confirm',
        'coordinate', 'sync', 'align', 'collaborate',

        # Decision Making
        'vote', 'voting', 'consensus', 'decide', 'decision',
        'thoughts?', 'opinions?', 'ideas?', 'input?',
        'should we', 'shall we', "let's", 'lets',

        # Urgency
        'critical', 'urgent', 'important', 'breaking', 'asap',
        'priority', 'emergency', 'blocker', 'blocked',

        # Requests
        'can someone', 'who can', 'anyone able', 'can anyone',
        'could someone', 'would someone', 'can you',

        # Task/Queue
        'queue_task', 'task added', 'new task', 'assigned',
        'take this', 'handle this', 'work on', 'pick up',
    ]

    received_event = {'data': None}
    event_received = threading.Event()

    def smart_filter(event_data: Dict) -> bool:
        """Check if this event is relevant to this AI"""
        event_type = event_data.get('type', '')
        data = event_data.get('data', {})
        author = event_data.get('author', '')

        # 1. Direct message TO this AI - always wake
        if event_type == 'dm' and data.get('from') != ai_name:
            received_event['data'] = event_data
            received_event['data']['wake_reason'] = 'direct_message'
            return True

        # 2. Task assigned to this AI - always wake
        if event_type == 'note_created':
            content = data.get('content', '').lower()
            if any(f'assign:{name}' in content or f'@{name}' in content for name in name_variations):
                received_event['data'] = event_data
                received_event['data']['wake_reason'] = 'task_assigned'
                return True

        # 3. Broadcast mentioning this AI's name - wake
        if event_type == 'broadcast':
            content = data.get('content', '').lower()

            # Check for name mentions
            if any(name in content for name in name_variations):
                received_event['data'] = event_data
                received_event['data']['wake_reason'] = 'name_mentioned'
                return True

            # Check for help keywords
            if any(keyword in content for keyword in help_keywords):
                received_event['data'] = event_data
                received_event['data']['wake_reason'] = 'help_requested'
                return True

        # 4. Note mentioning this AI - wake
        if event_type == 'note_created' or event_type == 'note_updated':
            content = data.get('content', '').lower()
            summary = data.get('summary', '').lower()

            if any(name in content or name in summary for name in name_variations):
                received_event['data'] = event_data
                received_event['data']['wake_reason'] = 'mentioned_in_note'
                return True

        # 5. HIGH PRIORITY content - wake EVERYONE (critical/urgent/emergency)
        priority_keywords = ['critical', 'urgent', 'emergency', 'asap', 'breaking', 'blocker']

        if event_type == 'broadcast':
            content_lower = data.get('content', '').lower()
            if any(keyword in content_lower for keyword in priority_keywords):
                received_event['data'] = event_data
                received_event['data']['wake_reason'] = 'priority_alert'
                return True

        if event_type in ['note_created', 'note_updated']:
            content_lower = data.get('content', '').lower()
            summary_lower = data.get('summary', '').lower()
            if any(keyword in content_lower or keyword in summary_lower for keyword in priority_keywords):
                received_event['data'] = event_data
                received_event['data']['wake_reason'] = 'priority_note'
                return True

        return False

    # Subscribe to ALL relevant event types
    subscribe_to_channel("dm", detail=ai_name)
    subscribe_to_channel("broadcast")  # All broadcasts
    subscribe_to_channel("note_created")
    subscribe_to_channel("note_updated")

    def universal_handler(data: Dict):
        """Handler that checks all events with smart filter"""
        if smart_filter(data):
            event_received.set()

    # Add handler for each subscription
    for event_type in ["dm", "broadcast", "note_created", "note_updated"]:
        detail = ai_name if event_type == "dm" else ""
        # Use pattern key for broadcast and dm when no detail (to match psubscribe)
        if event_type in ["broadcast", "dm"] and detail == "":
            channel = get_channel_name(event_type, "*")  # Pattern key
        else:
            channel = get_channel_name(event_type, detail)

        if channel not in _event_handlers:
            _event_handlers[channel] = []
        _event_handlers[channel].append(universal_handler)

    logging.info(f"😴 {ai_name} entering standby mode for {timeout}s...")
    logging.info(f"   Will wake on: DMs, @mentions, name mentions, help requests, assignments")

    try:
        if event_received.wait(timeout=timeout):
            wake_reason = received_event['data'].get('wake_reason', 'unknown')
            logging.info(f"⚡ {ai_name} woke up! Reason: {wake_reason}")
            return received_event['data']
        else:
            logging.info(f"⏰ {ai_name} standby timeout after {timeout}s")
            return None
    finally:
        # Clean up handlers
        for event_type in ["dm", "broadcast", "note_created", "note_updated"]:
            detail = ai_name if event_type == "dm" else ""
            # Use pattern key for broadcast and dm when no detail (to match registration)
            if event_type in ["broadcast", "dm"] and detail == "":
                channel = get_channel_name(event_type, "*")  # Pattern key
            else:
                channel = get_channel_name(event_type, detail)

            if channel in _event_handlers and universal_handler in _event_handlers[channel]:
                _event_handlers[channel].remove(universal_handler)

# ============= HELPER FUNCTIONS =============

def is_redis_available() -> bool:
    """Check if Redis is available"""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except:
        return False

def get_subscription_count() -> int:
    """Get number of active subscriptions"""
    global _pubsub
    if _pubsub is None:
        return 0
    
    try:
        patterns = _pubsub.patterns if hasattr(_pubsub, 'patterns') else {}
        channels = _pubsub.channels if hasattr(_pubsub, 'channels') else {}
        return len(patterns) + len(channels)
    except:
        return 0

# ============= AUTO-TRIGGER SYSTEM =============
# REMOVED: Minimal implementation per QD___ requirements
# Proper auto-trigger architecture to be designed with full team consensus
# before implementation. See Teambook Note #97 for architecture proposals.

# ============= INITIALIZATION =============

def init_pubsub():
    """Initialize Redis pub/sub system"""
    try:
        client = get_redis_client()
        logging.info(f"🚀 Redis pub/sub initialized for {CURRENT_AI_ID}")
        
        # Auto-subscribe to personal DM channel
        subscribe_to_channel("dm", detail=CURRENT_AI_ID)
        
        return True
    except Exception as e:
        logging.warning(f"Redis pub/sub init failed: {e}")
        return False

# Clean up on module unload
import atexit
atexit.register(close_redis)
