# User Guide - Operating the Deck

A step-by-step guide for operators to perform field reconnaissance and defense.

## 1. Launching the Deck
```bash
export GEMINI_API_KEY="your-key-here"   # optional — enables AI threat narrative
sudo python3 launcher.py
```

## 2. Performing a LAN Scan
1.  Enter a target IP or subnet in the `TARGET_HOST` field at the bottom (default: `127.0.0.1`).
2.  Click **[ LAN SCANNING ]** on the sidebar.
3.  Watch the console for discovered hosts and open ports. The Risk Score updates automatically.

## 3. WiFi Auditing
1.  Click **[ WIFI AUDIT ]**.
2.  The system uses `nmcli` to sweep the spectrum and list APs sorted by signal strength.
3.  Networks flagged `VULNERABLE AP` have open or WEP encryption — treat as untrusted.

## 4. Passive Network Monitoring
1.  Click **[ PASSIVE MONITOR ]**.
2.  The module captures packets on the configured interface for the duration set in `config.json` (default 60s).
3.  Alerts are raised in the console for ARP spoofing, port scans, and ICMP floods.
4.  Requires root. No packets are transmitted — receive-only mode.

## 5. ARP Monitor
1.  Click **[ ARP MONITOR ]**.
2.  The module listens exclusively to ARP traffic (BPF-filtered) on the configured interface for `duration` seconds (default 120s).
3.  It builds an IP→MAC trust table in real time and alerts immediately if any host advertises a new MAC for a known IP — a primary indicator of an ARP-based MITM attack.
4.  A full ARP table snapshot is printed to the console at the end of the session.
5.  Requires root.

## 6. Bluetooth Recon
1.  Click **[ BLUETOOTH RECON ]**.
2.  Lists all devices cached by the local Bluetooth stack via `bluetoothctl`.

## 7. TLS Audit
1.  Enter a target IP, hostname, or subnet (e.g. `192.168.1.0/24`) in the `TARGET_HOST` field.
2.  Click **[ TLS AUDIT ]**.
3.  The module connects to port 443 on each host and inspects the TLS handshake and certificate.
4.  Issues flagged: `CERT_EXPIRED`, `CERT_EXPIRING_SOON` (<30 days), `SELF_SIGNED_CERT`, `HOSTNAME_MISMATCH`, `WEAK_TLS_VERSION` (TLS 1.0/1.1 or older).
5.  No new dependencies required — uses Python's stdlib `ssl` module.

## 8. Pentest Toolkit
1.  Enter the target IP in the `TARGET_HOST` field.
2.  Click **[ PENTEST TOOLKIT ]**.
3.  The module attempts to connect to a local Metasploit MSFRPC daemon and match exploits to open ports.
4.  If no daemon is running, it falls back to a simulation based on common port-to-exploit mappings.

## 9. Anomaly Detection
1.  Run at least one other module first to build session history.
2.  Click **[ ANOMALY DETECTION ]**.
3.  The engine analyzes the last 20 operations from `logs/history.json` against 7 heuristic rules.
4.  If a `GEMINI_API_KEY` is set, an AI-generated threat narrative is appended to the output.

## 10. Reviewing Results
1.  Click **[ REPORTS ]**.
2.  The Executive Summary window opens showing aggregated stats (Total Ops, Entities found).
3.  Select any JSON file from the left list to view its raw scan data.
4.  An HTML report is automatically saved to `results/report_<timestamp>.html` on every run.

## 11. Emergency Lockdown
- Click the **[ EMERGENCY LOCKDOWN ]** button in the top-right of the header bar.
- All running module dispatches are blocked immediately and all sidebar buttons are disabled.
- Click **[ DISENGAGE LOCKDOWN ]** to resume normal operation.
