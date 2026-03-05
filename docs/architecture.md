# CyberDeck OS - System Architecture

This document describes the high-level architecture and data flow of CyberDeck OS v2.0.

## Overview
CyberDeck OS is built on an **Event-Driven MVC** (Model-View-Controller) architecture, designed for extensibility and thread-safe operations on a Raspberry Pi or any Linux host.

## Core Components

### 1. View Layer (`mode_select/`)
- **MainWindow (`main_window.py`)**: The central GUI hub built with Tkinter. Contains a header bar (title, Emergency Lockdown button, status label), module sidebar, central console, and telemetry pane. Subscribes to `MODULE_STARTED`, `MODULE_STOPPED`, `RISK_UPDATED`, `HISTORY_UPDATED`, and `SCAN_COMPLETED` events.
- **ReportsWindow (`reports_window.py`)**: A dedicated `Toplevel` window for browsing saved scan results and viewing raw JSON. Opened automatically when the Reports module completes.

### 2. Controller Layer (`core/controller.py`)
- The `SystemController` singleton manages module execution. It spawns isolated daemon threads, injects `config` and `callback` automatically, handles exceptions, archives results to `logs/history.json`, and publishes lifecycle events on the EventBus.

### 3. Model & State (`core/app_state.py`)
- A thread-safe singleton that maintains the system's "Source of Truth": active thread registry, telemetry counters, risk score (0-100), last scan data, and lockdown flag. All mutations fire EventBus events.

### 4. Event Bus (`core/event_bus.py`)
- A thread-safe Pub/Sub singleton. Decouples the UI from backend logic. Key events: `MODULE_STARTED/STOPPED`, `SCAN_REQUESTED/COMPLETED`, `RISK_UPDATED`, `HISTORY_UPDATED`, `TOPOLOGY_UPDATED`, `DEVICE_DETECTED`, `HONEYPOT_HIT`.

### 5. Risk Engine (`core/risk_engine.py`)
- Subscribes to `SCAN_COMPLETED`, `HONEYPOT_HIT`, and `DEVICE_DETECTED`. Deterministically scores the environment: +5 per open port, +10 per weak-crypto network, +15 per unknown device, +5 per honeypot hit. Capped at 100. Pushes score to `AppState` which fires `RISK_UPDATED`.

### 6. Scheduler (`core/scheduler.py`)
- Background daemon that dispatches `lan_scan.run` via the Controller every 300 seconds (configurable). Respects `state.is_locked_down` — sleeps without acting when the system is locked.

## Module Inventory

| Module | File | Key Technology | Root Required |
|---|---|---|---|
| Passive Monitor | `modules/passive_monitor.py` | Scapy `sniff()` — multi-protocol capture; detects ARP spoof, TCP port scan, ICMP flood | Yes |
| ARP Monitor | `modules/arp_monitor.py` | Scapy BPF-filtered ARP-only capture; builds IP→MAC trust table, flags MITM conflicts | Yes |
| LAN Scanning | `modules/lan_scan.py` | `python-nmap` ping sweep + port scan | Yes |
| WiFi Audit | `modules/wifi_audit.py` | `nmcli` subprocess; flags open/WEP networks | No |
| Bluetooth Recon | `modules/bluetooth_recon.py` | `bluetoothctl devices` subprocess | No |
| TLS Audit | `modules/tls_audit.py` | stdlib `ssl` — cert expiry, self-signed, hostname, weak TLS version checks | No |
| Pentest Toolkit | `modules/pentest_tools.py` | Metasploit MSFRPC; falls back to port-to-exploit simulation | No |
| Anomaly Detection | `modules/anomaly_detect.py` | 7 heuristic rules against `logs/history.json`; optional Gemini AI narrative | No |
| Reports | `modules/dashboard.py` | Reads history + results dir; generates HTML via `report_generator.py` | No |

## Data Flow
1. **Trigger**: User clicks a module button in the GUI sidebar.
2. **Dispatch**: `SystemController.dispatch_module()` checks lockdown, publishes `SCAN_REQUESTED`, spawns a daemon thread.
3. **Execution**: The module runs (Nmap, Scapy, bluetoothctl, ssl, etc.) and returns a standardized `create_result()` dict.
4. **Collation**: The Controller wraps the result into a `HistoryRecord` `{timestamp, module, targets, raw_data}`.
5. **Persistence**: The record is appended to `logs/history.json`. A per-scan JSON is saved to `results/`.
6. **Notification**: The Controller publishes `SCAN_COMPLETED` with the full record.
7. **Risk Update**: `RiskEngine` receives `SCAN_COMPLETED`, recalculates risk score, publishes `RISK_UPDATED`.
8. **UI Update**: `MainWindow` callbacks update the status label, telemetry pane, and risk display via `root.after(0, ...)`.
9. **HTML Report**: When the Reports module runs, `report_generator.py` saves an HTML summary to `results/`.
