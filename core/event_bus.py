import threading
from typing import Callable, Dict, List, Any

# --- Event Constants ---

# Module Lifecycle
MODULE_STARTED = "MODULE_STARTED"
MODULE_STOPPED = "MODULE_STOPPED"
SCAN_REQUESTED = "SCAN_REQUESTED"
SCAN_COMPLETED = "SCAN_COMPLETED"

# Data & Telemetry
HISTORY_UPDATED = "HISTORY_UPDATED"
TOPOLOGY_UPDATED = "TOPOLOGY_UPDATED"
RISK_UPDATED = "RISK_UPDATED"
METRICS_UPDATED = "METRICS_UPDATED"

# Monitor & Defense
DEVICE_DETECTED = "DEVICE_DETECTED"
HONEYPOT_HIT = "HONEYPOT_HIT"
VULNERABILITY_DETECTED = "VULNERABILITY_DETECTED"
SIMULATION_TRIGGERED = "SIMULATION_TRIGGERED"

# Thread Management
THREAD_REGISTERED = "THREAD_REGISTERED"
THREAD_TERMINATED = "THREAD_TERMINATED"

# System
SYSTEM_LOCKDOWN = "SYSTEM_LOCKDOWN"

class EventBus:
    """
    A Thread-safe Publisher/Subscriber Event Bus for passing decoupled 
    messages between the UI, Controllers, and State Managers.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._subscribers = {}
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if singleton already exists
        pass

    def subscribe(self, event_type: str, callback: Callable):
        """Register a callback function to listen for a specific event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove a callback from listening to a specific event type."""
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

    def publish(self, event_type: str, data: Any = None):
        """
        Emit an event, instantly synchronously dispatching it to all subscribers.
        For GUI updates, callbacks must handle thread-safety (e.g., master.after)
        if published from a background worker thread.
        """
        with self._lock:
            callbacks = self._subscribers.get(event_type, []).copy()
            
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error in subscriber {callback.__name__} for event {event_type}: {e}")

# Global singleton accessor
event_bus = EventBus()
