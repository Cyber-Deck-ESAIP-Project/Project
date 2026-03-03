import threading
import time
from core.app_state import state
from core.controller import controller
from modules import lan_scan, wifi_audit

class AutomationScheduler:
    """
    Background daemon that manages autonomous, periodic actions like Recon sweeps,
    alert-only Monitoring, and Auto-report generation, feeding directly back 
    into the EventBus and AppState.
    """
    def __init__(self):
        self._running = False
        self._thread = None
        self._sweep_interval_seconds = 300  # Default 5 minutes

    def start(self):
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SchedulerDaemon")
        state.register_thread("SchedulerDaemon", self._thread)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            state.terminate_thread("SchedulerDaemon")
            
    def set_interval(self, seconds: int):
        self._sweep_interval_seconds = seconds

    def _run_loop(self):
        while self._running:
            # Respect Global System Lockdown
            if state.is_locked_down:
                time.sleep(5)
                continue
                
            # Perform Autonomous Sweep (if not locked down)
            print("[Scheduler] Initiating Background Autonomous Recon Sweep...")
            # Dispatch LAN Scan via Controller (doesn't block)
            from utils.config_loader import load_config
            controller.dispatch_module("LAN Scan", lan_scan.run, config=load_config())
            
            # Wait for next cycle
            time.sleep(self._sweep_interval_seconds)

# Global Instance Accessor
scheduler = AutomationScheduler()
