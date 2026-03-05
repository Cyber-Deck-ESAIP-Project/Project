# CyberDeck OS v2.0 - System Architecture

This document is the complete technical reference for the CyberDeck OS v2.0 architecture. It covers every layer of the system — from boot to scan output — including threading, event flow, config loading, persistence, and lockdown behaviour.

---

## Overview

CyberDeck OS is built on an **Event-Driven MVC** (Model-View-Controller) architecture designed for extensibility and thread-safe operation on a Raspberry Pi or any Linux host.

Three principles govern the design:

1. **Modules never touch the UI.** They call `callback("text")` only. The controller wires the callback to the GUI.
2. **All state flows through the EventBus.** No component polls another — everything reacts to published events.
3. **The controller is the only entry point for running modules.** It handles thread lifecycle, error capture, archiving, and event publishing centrally.

---

## Folder Structure

```
CyberDeck-ESAIP/
├── launcher.py               # Primary entry point (GUI boot)
├── menu.py                   # Legacy CLI entry point
├── requirements.txt
│
├── config/
│   ├── config.json           # Active configuration (single source of truth)
│   └── config.example.json   # Documented template for new deployments
│
├── core/                     # Infrastructure layer (not modules)
│   ├── app_state.py          # Singleton state machine
│   ├── controller.py         # Module dispatcher and thread manager
│   ├── event_bus.py          # Pub/Sub decoupling layer
│   ├── risk_engine.py        # Automatic deterministic risk scorer
│   └── scheduler.py          # Background autonomous sweep daemon
│
├── mode_select/              # View layer
│   ├── main_window.py        # Primary Tkinter GUI
│   └── reports_window.py     # Scan results viewer (Toplevel window)
│
├── modules/                  # Scan modules (implement the run() contract)
│   ├── arp_monitor.py
│   ├── anomaly_detect.py
│   ├── bluetooth_recon.py
│   ├── dashboard.py
│   ├── lan_scan.py
│   ├── passive_monitor.py
│   ├── pentest_tools.py
│   ├── tls_audit.py
│   └── wifi_audit.py
│
├── utils/                    # Shared helpers
│   ├── config_loader.py
│   ├── logger.py
│   ├── report_generator.py
│   └── result_handler.py
│
├── logs/                     # Runtime output (gitignored)
│   ├── cyberdeck_YYYYMMDD.log
│   ├── history.json
│   └── pcaps/
│
├── results/                  # Per-scan output (gitignored)
│   ├── <module>_<timestamp>.json
│   └── report_<timestamp>.html
│
├── docs/
└── scripts/
    ├── setup_env.sh
    └── deploy.sh
```

---

## Boot Sequence

### Primary path: `launcher.py` → GUI

```
launcher.py
  │
  ├── 1. Auto-injects .venv/lib/pythonX.Y/site-packages into sys.path
  │      (allows sudo python3 launcher.py to find pip-installed packages)
  │
  ├── 2. load_config("config/config.json")
  │      Validates the config file is readable before the UI starts.
  │      Aborts with a clear error if the file is missing or malformed.
  │
  └── 3. start_ui()  ──▶  MainWindow(root)  ──▶  root.mainloop()
```

### Legacy path: `menu.py` → CLI

```
menu.py
  │
  ├── Scans modules/ directory via importlib
  ├── Validates each file has a run() function
  ├── Presents a numbered menu loop
  └── Calls module.run(config, callback=print)
      (uses the same controller infrastructure optionally)
```

---

## Core Components

### 1. View Layer — `mode_select/`

**`main_window.py` (`MainWindow`)**

Builds the full Tkinter GUI in a single class:

| GUI Region | Contents |
|---|---|
| Header bar | Title label, `[ EMERGENCY LOCKDOWN ]` toggle button, status label |
| Left sidebar | One button per module — dispatches via `_execute_module()` |
| Central console | `ScrolledText` — receives all `callback("text")` output |
| Right telemetry pane | Total Ops counter, Entities counter, Risk Score (colour-coded) |
| Footer | `TARGET_HOST` entry field — value passed as `target` kwarg to modules |

Subscribes to 5 EventBus events: `MODULE_STARTED`, `MODULE_STOPPED`, `RISK_UPDATED`, `HISTORY_UPDATED`, `SCAN_COMPLETED`.

All UI mutations from background threads use `root.after(0, fn)` — the only thread-safe way to update Tkinter from outside the main thread.

**`reports_window.py` (`ReportsWindow`)**

A `Toplevel` window opened automatically when the Reports module completes (triggered by `SCAN_COMPLETED`). Shows an aggregated summary header, a left listbox of all JSON result files, and a right viewer pane for raw JSON content.

---

### 2. Controller Layer — `core/controller.py`

`SystemController` is a singleton. `dispatch_module(name, func, **kwargs)` is the **only** way modules should be launched.

**What dispatch_module does:**

```
dispatch_module(name, func, callback, target, ...)
  │
  ├── 1. Check state.is_locked_down → abort if True
  ├── 2. Publish SCAN_REQUESTED on EventBus
  ├── 3. Spawn daemon thread running _module_worker(name, func, kwargs)
  └── 4. Register thread in AppState, publish MODULE_STARTED

_module_worker (runs in daemon thread):
  │
  ├── Calls func(config=self.config, callback=callback, **kwargs)
  ├── Catches all exceptions → converts to error result dict
  │
  └── finally block (always runs):
        ├── Unregister thread from AppState
        ├── Publish MODULE_STOPPED
        ├── Wrap result into HistoryRecord {timestamp, module, targets, raw_data}
        ├── Append HistoryRecord to logs/history.json
        ├── Save per-scan JSON to results/<module>_<timestamp>.json
        ├── Call state.update_telemetry() → fires HISTORY_UPDATED
        ├── Call state.set_last_scan_data() → fires TOPOLOGY_UPDATED
        └── Publish SCAN_COMPLETED with the full HistoryRecord
```

---

### 3. Model & State — `core/app_state.py`

`AppState` is a thread-safe singleton holding the system's source of truth:

| Field | Type | Description |
|---|---|---|
| `active_threads` | `dict` | Maps module name → thread object |
| `telemetry` | `dict` | `{total_operations, entities_tracked, breakdown}` |
| `risk_score` | `int` | 0–100, updated by RiskEngine |
| `last_scan_data` | `dict` | Raw data from the most recent recon scan |
| `is_locked_down` | `bool` | Blocks all controller dispatch when True |

Every mutation method publishes a corresponding EventBus event. No external code reads raw state — everything reacts to events.

---

### 4. Event Bus — `core/event_bus.py`

Thread-safe Pub/Sub singleton. All cross-component communication flows through here.

**Full event catalogue:**

| Event | Published by | Subscribed by | Payload |
|---|---|---|---|
| `SCAN_REQUESTED` | Controller | — | `module_name` (str) |
| `MODULE_STARTED` | Controller | MainWindow | `module_name` (str) |
| `MODULE_STOPPED` | Controller | MainWindow | `module_name` (str) |
| `SCAN_COMPLETED` | Controller | MainWindow, RiskEngine | `history_record` (dict) |
| `RISK_UPDATED` | RiskEngine | MainWindow | `score` (int) |
| `HISTORY_UPDATED` | AppState | MainWindow | `telemetry` (dict) |
| `TOPOLOGY_UPDATED` | AppState | — | `scan_data` (dict) |
| `DEVICE_DETECTED` | modules (optional) | RiskEngine | `device_info` (dict) |
| `HONEYPOT_HIT` | modules (optional) | RiskEngine | `hit_info` (dict) |

Usage:
```python
event_bus.subscribe("SCAN_COMPLETED", my_callback)
event_bus.publish("SCAN_COMPLETED", payload)
```

---

### 5. Risk Engine — `core/risk_engine.py`

`RiskEngine` is a singleton that subscribes to `SCAN_COMPLETED`, `HONEYPOT_HIT`, and `DEVICE_DETECTED`. It recalculates the risk score deterministically after every event.

**Scoring table:**

| Signal | Points |
|---|---|
| Each open port found in a LAN scan | +5 |
| Each weak-crypto (WEP/Open) WiFi network | +10 |
| Each unknown/new device detected | +15 |
| Each honeypot hit | +5 |

Score is capped at 100. The result is pushed to `AppState.risk_score`, which fires `RISK_UPDATED`. `MainWindow` then colour-codes the display: green (<40), orange (<75), red (≥75).

---

### 6. Scheduler — `core/scheduler.py`

`AutomationScheduler` runs a background daemon loop that dispatches `lan_scan.run` via the controller every 300 seconds (configurable). It checks `state.is_locked_down` before each dispatch and sleeps without acting when locked.

This means even without any user interaction, the system maintains an up-to-date picture of the LAN and keeps the risk score current.

---

## Module Inventory

All modules implement the same contract: `run(config, callback=None, **kwargs) -> dict`.

| Module | File | Key Technology | Root Required |
|---|---|---|---|
| Passive Monitor | `modules/passive_monitor.py` | Scapy `sniff()` — multi-protocol; detects ARP spoof, TCP port scan (15+ ports), ICMP flood (50+ pkts) | Yes |
| ARP Monitor | `modules/arp_monitor.py` | Scapy BPF `"arp"` filter; IP→MAC trust table; flags MAC changes as MITM conflicts | Yes |
| LAN Scanning | `modules/lan_scan.py` | `python-nmap` ping sweep (`-sn`) + fast port scan (`-F -sV -T4`) | Yes |
| WiFi Audit | `modules/wifi_audit.py` | `nmcli` subprocess; sorts by signal; flags `WEAK_CRYPTO` / `OPEN_NETWORK` | No |
| Bluetooth Recon | `modules/bluetooth_recon.py` | `bluetoothctl devices` subprocess | No |
| TLS Audit | `modules/tls_audit.py` | stdlib `ssl` only — cert expiry, self-signed, hostname, deprecated TLS version | No |
| Pentest Toolkit | `modules/pentest_tools.py` | Metasploit MSFRPC (`pymetasploit3`); falls back to port-to-exploit simulation | No |
| Anomaly Detection | `modules/anomaly_detect.py` | 7 heuristic rules on `logs/history.json`; optional Gemini AI narrative | No |
| Reports | `modules/dashboard.py` | Reads history + results dir; generates HTML via `report_generator.py` | No |

---

## Threading Model

Every module runs in its own **daemon thread** spawned by the controller. Daemon threads are automatically killed if the main process exits.

**Why daemon threads:**
- The GUI remains fully responsive during long scans (Scapy capture, Nmap sweep).
- A crash inside a module does not bring down the whole application — the controller's `finally` block always executes.

**Thread safety rules:**
- Modules communicate back to the UI exclusively via `callback("text")`, which internally calls `root.after(0, fn)` — the Tkinter-safe deferred execution mechanism.
- All `AppState` mutations are protected with `threading.Lock`.
- The EventBus delivers events from any thread; subscribers that update Tkinter widgets must use `root.after(0, ...)`.

---

## Config Loading

```
Boot
  └── load_config("config/config.json")   [utils/config_loader.py]
        │
        └── Returns full config dict
              │
              └── Stored in SystemController.config
                    │
                    └── Injected into every module call as:
                          func(config=self.config, ...)
```

Modules read their own slice:
```python
mod_config = config.get("modules", {}).get("module_name", {})
interface  = mod_config.get("interface", "eth0")
```

The Gemini API key lookup order (in `anomaly_detect.py`):
```
os.environ.get("GEMINI_API_KEY")
  or config["system"]["gemini_api_key"]
  or config["api_keys"]["google_gemini_key"]
  or None  →  AI narrative skipped gracefully
```

---

## Result & Persistence Pipeline

```
module.run() returns create_result(...)
  │
  │   {
  │     "module":    "lan_scan",
  │     "timestamp": "2026-03-05T12:00:00.000000",
  │     "status":    "success",
  │     "data":      { ... scan-specific payload ... },
  │     "errors":    []
  │   }
  │
  └── Controller wraps into HistoryRecord:
        {
          "timestamp": "2026-03-05 12:00:00",
          "module":    "LAN Scanning",
          "targets":   5,            ← extracted from data["hosts_up"] etc.
          "raw_data":  { ...full result dict... }
        }
          │
          ├── Appended to logs/history.json  (append-only session log)
          ├── Saved to results/lan_scan_20260305_120000.json
          └── Published as SCAN_COMPLETED payload
                │
                ├── RiskEngine recalculates score
                ├── MainWindow updates console / telemetry
                └── If module == "Reports":
                      MainWindow opens ReportsWindow Toplevel
                      report_generator.py saves results/report_<ts>.html
```

---

## Emergency Lockdown Flow

```
User clicks [ EMERGENCY LOCKDOWN ]
  │
  └── MainWindow._toggle_lockdown()
        │
        ├── state.set_lockdown(True)
        │     └── AppState sets is_locked_down = True
        │
        ├── lbl_status → "[ LOCKDOWN ACTIVE ]" (red)
        ├── btn_lockdown → "[ DISENGAGE LOCKDOWN ]" (red)
        └── All sidebar buttons → tk.DISABLED

Any subsequent dispatch_module() call:
  └── Controller checks state.is_locked_down → True → aborts immediately

Scheduler loop:
  └── Checks state.is_locked_down → True → sleeps, skips dispatch

User clicks [ DISENGAGE LOCKDOWN ]
  └── state.set_lockdown(False)
      All buttons re-enabled, status returns to "[ SYSTEM IDLE ]"
```

---

## Anomaly Detection Heuristic Rules

The `anomaly_detect` module analyses the last 20 records from `logs/history.json` against 7 rules:

| Rule | Severity | Trigger condition |
|---|---|---|
| `HIGH_ERROR_RATE` | HIGH | >50% of last 20 ops returned `status: error` |
| `ARP_SPOOFING_DETECTED` | CRITICAL | `passive_monitor` or `arp_monitor` logged ARP conflicts |
| `PORT_SCAN_ACTIVITY` | HIGH | `passive_monitor` found entries in `scanners_detected` |
| `ICMP_FLOOD_DETECTED` | MEDIUM | `passive_monitor` logged ICMP protocol anomalies |
| `WEAK_WIFI_NETWORKS` | MEDIUM | `wifi_audit` found `WEAK_CRYPTO` or `OPEN_NETWORK` flags |
| `LARGE_LAN_FOOTPRINT` | MEDIUM | LAN scan found 20+ live hosts |
| `HIGH_RISK_PORTS_OPEN` | HIGH | Ports 21/23/445/3389/5900 open on any LAN host |

If `GEMINI_API_KEY` is set, the flagged rules are sent to `gemini-pro` and a threat narrative is appended to the console output.

---

## File Output Locations

| Output | Path | Created by |
|---|---|---|
| Daily rotating log | `logs/cyberdeck_YYYYMMDD.log` | `utils/logger.py` |
| Session history | `logs/history.json` | `core/controller.py` |
| Per-scan JSON | `results/<module>_<YYYYMMDD_HHMMSS>.json` | `core/controller.py` |
| HTML report | `results/report_<timestamp>.html` | `utils/report_generator.py` |
| Packet captures | `logs/pcaps/capture_<timestamp>.pcap` | `modules/passive_monitor.py` |

All paths under `logs/` and `results/` are gitignored.
