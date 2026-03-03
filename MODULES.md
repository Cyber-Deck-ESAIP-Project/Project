# ⚙️ CyberDeck OS - Technical Reference Manual

This document outlines the implementation details of the currently active modules in CyberDeck OS v2.0.

---

## 🔍 I. The Reconnaissance Grid

### 1. LAN Scanner (`modules/lan_scan.py`)
*   **Methodology:** Executes synchronous network sweeps to identify alive hosts via ICMP and port scans.
*   **Dependencies:** `python-nmap`.

### 2. 802.11 WiFi Audit (`modules/wifi_audit.py`)
*   **Methodology:** Uses `nmcli` or `iwlist` to sweep for active beacons and identify encryption types.
*   **Outcome:** Detects SSID, BSSID, Signal Strength, and Security Flags.

### 3. Bluetooth Recon (`modules/bluetooth_recon.py`)
*   **Methodology:** Queries the local Bluetooth stack for broadcasting devices using `bluetoothctl`.
*   **Outcome:** Returns device names and MAC addresses.

## 🛡️ II. Advanced Operations

### 4. Pentest Tools (`modules/pentest_tools.py`)
*   **Methodology:** Provides a bridge to deeper vulnerability analysis tools (Metasploit integration).
*   **Dependencies:** `pymetasploit3`.

### 5. Anomaly Detection (`modules/anomaly_detect.py`)
*   **Methodology:** Pure Python heuristic engine for identifying suspicious network patterns.

### 6. Reports Module (`modules/dashboard.py`)
*   **Methodology:** Aggregates session telemetry from `logs/history.json` and produces an executive summary for the operator.

---
## ⚙️ III. Core Systems
- **Event Bus (`core/event_bus.py`)**: Singleton Pub/Sub object pattern.
- **App State (`core/app_state.py`)**: Thread-safe global state machine.
- **Scheduler (`core/scheduler.py`)**: Background daemon for periodic tasks.
