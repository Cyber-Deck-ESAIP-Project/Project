from typing import Dict, Any
from core.app_state import state
from core.event_bus import event_bus, SCAN_COMPLETED, HONEYPOT_HIT, DEVICE_DETECTED

HIGH_RISK_PORTS = {21, 23, 445, 3389, 5900}

class RiskEngine:
    """
    Deterministic scoring engine that calculates a 0-100 system Risk Score
    based on the current State metrics and recent event streams.
    """
    def __init__(self):
        self._base_risk = 0
        self._honeypot_hits = 0
        self._unknown_devices = 0
        self._open_ports = 0
        self._high_risk_port_hits = 0
        self._weak_crypto_networks = 0
        
        # Subscribe to operational events to recalculate risk automatically
        event_bus.subscribe(SCAN_COMPLETED, self._on_scan_completed)
        event_bus.subscribe(HONEYPOT_HIT, self._on_honeypot_hit)
        event_bus.subscribe(DEVICE_DETECTED, self._on_device_detected)
        
    def _on_scan_completed(self, payload: Dict[str, Any]):
        """Parse scan results for specific threat indicators."""
        if not payload or not isinstance(payload, dict):
            return

        mod = payload.get("module", "")
        # raw_data contains the full create_result() output
        data = payload.get("raw_data", {}).get("data", {})

        if mod == "LAN Scanning":
            results = data.get("scan_results", {})
            if isinstance(results, dict):
                self._open_ports = sum(len(host_data.get("ports", [])) for host_data in results.values())
                self._high_risk_port_hits = sum(
                    1 for host_data in results.values()
                    for p in host_data.get("ports", [])
                    if p.get("port") in HIGH_RISK_PORTS
                )

        elif mod == "WiFi Audit":
            results = data.get("scan_results", [])
            if isinstance(results, list):
                weak_count = sum(
                    1 for net in results
                    if "OPEN_NETWORK" in net.get("flags", []) or "WEAK_CRYPTO" in net.get("flags", [])
                    or "OPN" in net.get("crypto", "") or "WEP" in net.get("crypto", "")
                )
                self._weak_crypto_networks = weak_count

        elif mod == "Bluetooth Recon":
            results = data.get("scan_results", [])
            if isinstance(results, list):
                self._unknown_devices = len(results)

        self.recalculate()
            
    def _on_honeypot_hit(self, data: Any):
        self._honeypot_hits += 1
        self.recalculate()
        
    def _on_device_detected(self, data: Any):
        self._unknown_devices += 1
        self.recalculate()

    def recalculate(self):
        """
        Calculates deterministic scoring defined by the master plan:
        +5 per open port
        +10 per weak crypto
        +15 per unknown device
        +5 per honeypot hit
        Capped at 100.
        """
        score = self._base_risk
        score += (self._open_ports * 5)
        score += (self._high_risk_port_hits * 20)
        score += (self._weak_crypto_networks * 10)
        score += (self._unknown_devices * 15)
        score += (self._honeypot_hits * 5)
        
        # Push update to State Manager (which fires RISK_UPDATED event)
        state.set_risk_score(score)

# Global accessor
risk_engine = RiskEngine()
