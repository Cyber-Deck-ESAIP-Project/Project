import threading
from typing import Dict, Any
from core.event_bus import event_bus, RISK_UPDATED, TOPOLOGY_UPDATED, THREAD_REGISTERED, THREAD_TERMINATED, HISTORY_UPDATED

class AppState:
    """
    Centralized, thread-safe Singleton to hold and broadcast the global state 
    of the CyberDeck platform. Modules and UI will read from here instead of globals.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppState, cls).__new__(cls)
                cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        # Operational State
        self._lab_mode_enabled = True # Always default safe in defensive setup
        self._system_locked_down = False
        
        # Threads
        self._active_threads: Dict[str, threading.Thread] = {}
        
        # Analytics & Metrics
        self._telemetry = {
            "total_operations": 0,
            "entities_tracked": 0,
            "breakdown": {
                "LAN Scans": 0,
                "WiFi Audits": 0,
                "Bluetooth Sweeps": 0,
                "Passive Monitors": 0
            }
        }
        
        # Risk & Topology
        self._risk_score = 0
        self._last_scan_data: Dict[str, Any] = {}
        
        # Defense
        self._honeypot_hits = 0
        self._live_devices_detected = 0

    # --- Thread Management ---
    def register_thread(self, name: str, thread: threading.Thread):
        with self._lock:
            self._active_threads[name] = thread
        event_bus.publish(THREAD_REGISTERED, name)

    def terminate_thread(self, name: str):
        with self._lock:
            if name in self._active_threads:
                del self._active_threads[name]
        event_bus.publish(THREAD_TERMINATED, name)
        
    def get_active_threads(self) -> Dict[str, threading.Thread]:
        with self._lock:
            return self._active_threads.copy()

    # --- Metrics & History ---
    def update_telemetry(self, module_name: str, entities_found: int):
        with self._lock:
            self._telemetry["total_operations"] += 1
            self._telemetry["entities_tracked"] += entities_found
            
            # Map dynamic names to internal breakdown keys
            if "LAN" in module_name:
                self._telemetry["breakdown"]["LAN Scans"] += 1
            elif "WiFi" in module_name:
                self._telemetry["breakdown"]["WiFi Audits"] += 1
            elif "Bluetooth" in module_name or "BT" in module_name:
                self._telemetry["breakdown"]["Bluetooth Sweeps"] += 1
            elif "Passive" in module_name:
                self._telemetry["breakdown"]["Passive Monitors"] += 1
                
        event_bus.publish(HISTORY_UPDATED, self._telemetry)

    def get_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._telemetry)

    # --- Topology & Scan Data ---
    def set_last_scan_data(self, data: Dict[str, Any]):
        with self._lock:
            self._last_scan_data = dict(data)
        event_bus.publish(TOPOLOGY_UPDATED, self._last_scan_data)
        
    def get_last_scan_data(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._last_scan_data)

    # --- Risk Engine Interface ---
    def set_risk_score(self, score: int):
        with self._lock:
            # Cap at 100 per spec
            self._risk_score = min(score, 100)
        event_bus.publish(RISK_UPDATED, self._risk_score)
        
    def get_risk_score(self) -> int:
        with self._lock:
            return self._risk_score

    # --- Lab Mode & Core State ---
    @property
    def lab_mode(self) -> bool:
        with self._lock:
            return self._lab_mode_enabled
            
    def set_lab_mode(self, state: bool):
        with self._lock:
            self._lab_mode_enabled = state
            
    @property
    def is_locked_down(self) -> bool:
        with self._lock:
            return self._system_locked_down
            
    def set_lockdown(self, state: bool):
        with self._lock:
            self._system_locked_down = state

# Global State Accessor
state = AppState()
