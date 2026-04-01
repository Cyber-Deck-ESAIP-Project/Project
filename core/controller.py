import threading
import json
import os
from datetime import datetime
from typing import Callable, Any

from core.app_state import state
from core.event_bus import (
    event_bus, 
    MODULE_STARTED, 
    MODULE_STOPPED, 
    SCAN_REQUESTED,
    SCAN_COMPLETED
)
from utils.config_loader import load_config

HISTORY_FILE = "logs/history.json"

class SystemController:
    """
    The Controller layer mediates between the UI and the underlying Module Logic.
    It spins up isolated worker threads, catches their output, updates the State,
    and publishes the final events across the EventBus.
    """
    def __init__(self):
        # Ensure log directory exists
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        self.config = load_config()

    def dispatch_module(self, module_name: str, target_func: Callable, **kwargs):
        """
        Spins up a background thread to execute a module without blocking the GUI.
        """
        if state.is_locked_down:
            print(f"[Controller] Blocked execution of {module_name}. System is in Lockdown.")
            return

        # Fire requested event
        event_bus.publish(SCAN_REQUESTED, module_name)

        thread = threading.Thread(
            target=self._module_worker,
            args=(module_name, target_func),
            kwargs=kwargs,
            daemon=True
        )
        
        state.register_thread(module_name, thread)
        event_bus.publish(MODULE_STARTED, module_name)
        thread.start()

    def _module_worker(self, module_name: str, target_func: Callable, **kwargs):
        """The actual isolated execution context for the module."""
        payload = None
        try:
            # Inject config automatically if the module expects it
            if "config" not in kwargs:
                kwargs["config"] = self.config
                
            # Execute the heavy module task
            payload = target_func(**kwargs)
        except Exception as e:
            print(f"[{module_name} Error]: {e}")
            payload = {"status": "error", "error": str(e)}

        finally:
            # Thread cleanup & Data Routing
            state.terminate_thread(module_name)
            event_bus.publish(MODULE_STOPPED, module_name)

            if payload and isinstance(payload, dict):
                # Standardize payload embedding
                history_record = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "module": module_name,
                    "targets": self._extract_target_count(payload),
                    "raw_data": payload
                }
                
                # 1. Archive to Disk
                self._archive_to_disk(history_record)
                
                # 2. Update Global App State
                state.update_telemetry(module_name, history_record["targets"])
                if module_name in ["LAN Scanning", "WiFi Audit", "Bluetooth Recon"]:
                    state.set_last_scan_data(history_record)
                
                # 3. Publish completion object for UI subscribers
                event_bus.publish(SCAN_COMPLETED, history_record)
                
    def _extract_target_count(self, payload: dict) -> int:
        """Safely extract the number of entities discovered from a generic payload."""
        try:
            data = payload.get("data", {})
            if "hosts_up" in data:
                return int(data["hosts_up"])
            if "scan_results" in data:
                return len(data["scan_results"])
            if "anomalous_packets" in data:
                return len(data["anomalous_packets"])
            if "total_queries" in data:
                return int(data["total_queries"])
            if "samples_collected" in data:
                return int(data["samples_collected"])
            if "cves_found" in data:
                return int(data["cves_found"])
            if "total_matches" in data:     # pentest_tools
                return int(data["total_matches"])
            if "probes_total" in data:      # tls_audit
                return int(data["probes_total"])
        except:
            pass
        return 0

    def _archive_to_disk(self, record: dict):
        """Append the raw JSON record to the historian database."""
        try:
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            history.append(record)
            with open(HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            print(f"[Historian] Failed to archive object: {e}")

# Global Controller Accessor
controller = SystemController()
