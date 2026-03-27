# ⚙️ CyberDeck OS - Technical Reference Manual

This document outlines the implementation details of the currently active modules in CyberDeck OS v2.0.

---

## 🔍 I. The Reconnaissance Grid

### 1. LAN Scanner (`modules/lan_scan.py`)
*   **Methodology:** Nmap ping sweep (`-sn`) to find live hosts, then fast port + version scan (`-F -sV -T4`).
*   **Output:** `hosts_up`, `scan_results` dict keyed by IP with ports, product, version.
*   **Dependencies:** `python-nmap`. Requires root.

### 2. 802.11 WiFi Audit (`modules/wifi_audit.py`)
*   **Methodology:** Uses `nmcli` to sweep for active access points, sorted by signal strength.
*   **Output:** `networks_found`, `scan_results` list. Flags `WEAK_CRYPTO` / `OPEN_NETWORK`.

### 3. Bluetooth Recon (`modules/bluetooth_recon.py`)
*   **Methodology:** Queries the local Bluetooth stack via `bluetoothctl devices`.
*   **Output:** `devices_found`, `scan_results` list with MAC and name.

### 4. Passive Monitor (`modules/passive_monitor.py`)
*   **Methodology:** Scapy `sniff()` on the configured interface for `duration` seconds.
*   **Detects:** ARP spoofing, TCP port scans (15+ unique ports), ICMP floods (50+ packets).
*   **Output:** `total_packets_captured`, `anomalous_packets`, `scanners_detected`, `arp_table_snapshot`. Requires root.

### 5. ARP Monitor (`modules/arp_monitor.py`)
*   **Methodology:** Scapy BPF-filtered ARP-only capture. Builds IP→MAC trust table; flags MAC changes.
*   **Output:** `total_arp_packets`, `unique_hosts`, `arp_table`, `conflict_events`. Requires root.

### 6. TLS Audit (`modules/tls_audit.py`)
*   **Methodology:** stdlib `ssl` only. Connects to port 443 on each target and inspects the certificate and handshake.
*   **Flags:** `CERT_EXPIRED`, `CERT_EXPIRING_SOON`, `SELF_SIGNED_CERT`, `HOSTNAME_MISMATCH`, `WEAK_TLS_VERSION`.

### 7. Real-Time DNS Query Monitor (`modules/dns_monitor/`)
*   **Methodology:** Scapy sniff on UDP port 53. Tracks query frequency, detects suspicious domains (long names, rare TLDs, high digit ratio).
*   **Output:** Domain counters, suspicious query flags, live stats every 10 seconds. Requires root.

---

## 🛡️ II. Advanced Operations

### 8. Pentest Tools (`modules/pentest_tools.py`)
*   **Methodology:** Attempts Metasploit MSFRPC connection; falls back to port-mapped exploit simulation.
*   **Dependencies:** `pymetasploit3` (optional).

### 9. AI Anomaly Detection (`modules/anomaly_detect.py`)
*   **Methodology:** Reads last 20 records from `logs/history.json`. Runs 7 heuristic rules. Optionally sends flagged rules to Gemini AI for a threat narrative.
*   **Rules:** `HIGH_ERROR_RATE`, `ARP_SPOOFING_DETECTED`, `PORT_SCAN_ACTIVITY`, `ICMP_FLOOD_DETECTED`, `WEAK_WIFI_NETWORKS`, `LARGE_LAN_FOOTPRINT`, `HIGH_RISK_PORTS_OPEN`.

### 10. CVE Vulnerability Matcher (`modules/cve_matcher.py`)
*   **Methodology:** Reads the latest LAN Scan result from `logs/history.json`, extracts service name + version strings from open ports, queries the NVD (National Vulnerability Database) free API for matching CVEs.
*   **Output:** `services_scanned`, `cves_found`, `vulnerabilities` list (sorted by CVSS score), `severity_summary` dict.
*   **Visual:** Severity distribution donut chart + color-coded CVE table rendered in the dashboard automatically.
*   **Rate limit:** 5 NVD requests / 30 sec (unauthenticated). Caps at 15 unique services.
*   **Prerequisite:** Run LAN Scanning first.

---

## 📊 III. Monitoring & Reporting

### 11. Hardware Telemetry Monitor (`modules/hwmon_telemetry.py`)
*   **Methodology:** Collects 30 time-series samples of CPU, temperature, battery, and power draw via `psutil`.
*   **Output:** Aggregated stats (avg/max/min) per metric, risk assessment score (0–100 deployment readiness).
*   **Visual:** CPU bar chart, temperature bar chart, readiness donut rendered in the dashboard automatically.
*   **Dependencies:** `psutil`.

### 12. Reports & Analytics (`modules/dashboard.py`)
*   **Methodology:** Reads `logs/history.json` + `results/` dir. Generates HTML executive report via `report_generator.py`.
*   **Output:** Global dashboard HTML with module breakdown, scan history table, baseline comparison.

---

## ⚙️ IV. Core Systems

- **Event Bus (`core/event_bus.py`)**: Singleton Pub/Sub. Thread-safe cross-component communication.
- **App State (`core/app_state.py`)**: Thread-safe singleton state machine (threads, telemetry, risk score, lockdown).
- **Controller (`core/controller.py`)**: Single entry point for module dispatch. Handles threading, archival, event publishing.
- **Risk Engine (`core/risk_engine.py`)**: Subscribes to `SCAN_COMPLETED`. Auto-calculates risk score (+5/open port, +10/weak WiFi, +15/unknown device).
- **Scheduler (`core/scheduler.py`)**: Background daemon — runs LAN Scan every 300 seconds automatically.
