# User Guide - Operating the Deck

Complete operator guide for CyberDeck OS v2.0. Covers every module, the GUI layout, output interpretation, and field workflows.

---

## GUI Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ CYBERDECK OS v2.0          [ EMERGENCY LOCKDOWN ]   [ SYSTEM IDLE ] │  ← Header
├──────────────┬──────────────────────────────────┬───────────────────┤
│ DEPLOY       │                                  │ TELEMETRY         │
│ MODULES      │   OPERATIONAL STREAM             │                   │
│              │   (scrolled console)             │ Total Ops: 0      │
│ [ PASSIVE  ] │                                  │ Entities: 0       │
│ [ ARP MON  ] │   >> System Ready.               │                   │
│ [ LAN SCAN ] │                                  │ Risk Level: 0     │
│ [ WIFI     ] │                                  │                   │
│ [ BLUETOOT ] │                                  │                   │
│ [ TLS AUDI ] │                                  │                   │
│ [ PENTEST  ] │                                  │                   │
│ [ ANOMALY  ] │                                  │                   │
│ [ REPORTS  ] │                                  │                   │
├──────────────┴──────────────────────────────────┴───────────────────┤
│ TARGET_HOST: [ 127.0.0.1                                           ] │  ← Footer
└─────────────────────────────────────────────────────────────────────┘
```

**Risk Level colour coding:**
- Green — 0–39 (nominal)
- Orange — 40–74 (elevated)
- Red — 75–100 (critical)

---

## 1. Launching the Deck

```bash
export GEMINI_API_KEY="your-key-here"   # optional — enables AI threat narrative
sudo python3 launcher.py
```

Root is required for packet capture (Scapy) and ping sweeps (Nmap). If you see a `Permission denied` error from a module, check that you launched with `sudo`.

---

## 2. Passive Network Monitoring

**What it does:** Captures all packets on the configured interface for `duration` seconds (default: 60s). Analyses them for three threat patterns in real time. Receive-only — no packets are transmitted.

**Steps:**
1. Click **[ PASSIVE MONITOR ]**.
2. Watch the console. Alerts are printed immediately as threats are detected.
3. A summary is printed at the end with total packet count and all anomaly events.

**Detects:**
| Threat | Trigger |
|---|---|
| ARP Spoofing | An IP address advertises a different MAC than previously seen |
| Port Scan | One source sends SYN packets to 15+ unique destination ports |
| ICMP Flood | One source sends 50+ ICMP packets |

**Output fields:** `total_packets_captured`, `anomalous_packets`, `scanners_detected`, `arp_table_snapshot`.

---

## 3. ARP Monitor

**What it does:** Listens exclusively to ARP traffic (BPF-filtered, lower overhead than Passive Monitor) for `duration` seconds (default: 120s). Builds an IP→MAC trust table from first-seen entries and immediately flags any host that changes its MAC — the primary indicator of an ARP-based MITM attack.

**Steps:**
1. Click **[ ARP MONITOR ]**.
2. The console shows each new IP→MAC mapping as it is learned.
3. Any conflict (MAC change for a known IP) triggers an immediate `[!] ARP CONFLICT` alert.
4. At the end of the session, the full ARP table snapshot is printed.

**Output fields:** `total_arp_packets`, `unique_hosts`, `arp_table`, `conflict_events`.

**Requires root.**

---

## 4. LAN Scanning

**What it does:** Active network sweep using Nmap. First a ping sweep (`-sn`) to find live hosts, then a fast port scan (`-F -sV -T4`) on each.

**Steps:**
1. Enter a target IP or subnet in the `TARGET_HOST` field (e.g. `192.168.1.0/24`).
2. Click **[ LAN SCANNING ]**.
3. Live hosts and open ports appear in the console as they are discovered.
4. The Risk Score updates automatically — +5 per open port found.

**Output fields:** `hosts_up`, `scan_results` (dict keyed by IP, each with `hostname`, `open_ports`, `services`).

---

## 5. WiFi Auditing

**What it does:** Uses `nmcli` to enumerate nearby access points, sorted by signal strength. Flags security-weak networks.

**Steps:**
1. Click **[ WIFI AUDIT ]**.
2. Results are printed in the console sorted by signal (strongest first).
3. Networks marked `VULNERABLE AP` have open or WEP encryption — treat as untrusted.

**Flags:**
- `OPEN_NETWORK` — no encryption at all
- `WEAK_CRYPTO` — WEP encryption (trivially crackable)

**Output fields:** `networks_found`, `scan_results` (list with BSSID, SSID, signal, security, flag).

---

## 6. Bluetooth Recon

**What it does:** Queries the local Bluetooth stack via `bluetoothctl devices` to list all cached/paired devices.

**Steps:**
1. Click **[ BLUETOOTH RECON ]**.
2. All devices known to the local Bluetooth adapter are listed in the console.

Note: This lists cached devices, not a live active scan. RSSI is reported as "N/A" — live signal strength requires `hcitool scan`.

**Output fields:** `devices_found`, `scan_results` (list with MAC, name, type).

---

## 7. TLS Audit

**What it does:** Connects to port 443 on each target host and inspects the TLS handshake and certificate. No new dependencies — uses Python's stdlib `ssl` module only.

**Steps:**
1. Enter a target in the `TARGET_HOST` field. Accepted formats:
   - Single IP: `192.168.1.10`
   - Hostname: `example.com`
   - Subnet: `192.168.1.0/24` (max 256 hosts)
   - Comma-separated: `10.0.0.1, 10.0.0.2`
2. Click **[ TLS AUDIT ]**.
3. Each host is probed and results are printed inline.

**Vulnerability flags:**
| Flag | Meaning |
|---|---|
| `CERT_EXPIRED` | Certificate validity period has passed |
| `CERT_EXPIRING_SOON` | Certificate expires within 30 days |
| `SELF_SIGNED_CERT` | Certificate issuer == subject (not CA-signed) |
| `HOSTNAME_MISMATCH` | Certificate CN does not match the target hostname |
| `WEAK_TLS_VERSION:TLSv1` | Server accepted a deprecated TLS version |

**Output fields:** `hosts_audited`, `hosts_reachable`, `vulnerabilities_found`, `tls_results`.

---

## 8. Pentest Toolkit

**What it does:** Attempts to connect to a local Metasploit MSFRPC daemon and match known exploits to open ports on the target. If no daemon is running, falls back to a built-in port-to-exploit mapping simulation.

**Steps:**
1. Enter the target IP in the `TARGET_HOST` field.
2. Click **[ PENTEST TOOLKIT ]**.
3. If Metasploit MSFRPC is running locally (default port 55553), live exploit matching is performed.
4. Without MSFRPC, the simulation maps common ports (21, 22, 23, 80, 443, 445, 3389, etc.) to known exploit categories.

---

## 9. Anomaly Detection

**What it does:** Reads the last 20 operations from `logs/history.json` and runs 7 heuristic rules to flag patterns that indicate a compromised or hostile environment. Optionally sends flagged rules to Gemini AI for a human-readable threat narrative.

**Steps:**
1. Run at least one other module first (needs history to analyse).
2. Click **[ ANOMALY DETECTION ]**.
3. Each triggered rule is printed with its severity.
4. If `GEMINI_API_KEY` is set, an AI narrative is appended.

**Rules:**
| Rule | Severity | Trigger |
|---|---|---|
| `HIGH_ERROR_RATE` | HIGH | >50% of last 20 ops errored |
| `ARP_SPOOFING_DETECTED` | CRITICAL | ARP conflicts found by passive_monitor or arp_monitor |
| `PORT_SCAN_ACTIVITY` | HIGH | Scanners detected by passive_monitor |
| `ICMP_FLOOD_DETECTED` | MEDIUM | ICMP flood detected by passive_monitor |
| `WEAK_WIFI_NETWORKS` | MEDIUM | WiFi audit found open/WEP networks |
| `LARGE_LAN_FOOTPRINT` | MEDIUM | LAN scan found 20+ live hosts |
| `HIGH_RISK_PORTS_OPEN` | HIGH | Ports 21/23/445/3389/5900 open on any host |

---

## 10. Reviewing Results

**What it does:** Reads all data from `logs/history.json` and the `results/` directory. Generates an HTML report and opens the Reports viewer window.

**Steps:**
1. Click **[ REPORTS ]**.
2. A pop-up window opens with:
   - **Top summary**: Total operations, entities found across all scans.
   - **Left panel**: List of all saved JSON result files.
   - **Right panel**: Raw JSON content of the selected file.
3. An HTML executive summary is automatically saved to `results/report_<timestamp>.html`.

---

## 11. Emergency Lockdown

Immediately blocks all further module dispatch and disables every sidebar button.

**Engage:**
- Click **[ EMERGENCY LOCKDOWN ]** in the top-right of the header bar.
- Status changes to `[ LOCKDOWN ACTIVE ]` in red.
- The background Scheduler also stops dispatching during lockdown.

**Disengage:**
- Click **[ DISENGAGE LOCKDOWN ]**.
- All buttons re-enable. Status returns to `[ SYSTEM IDLE ]`.

---

## Recommended Field Workflow

For a thorough assessment of an unknown network:

```
1. Passive Monitor (60s)     — baseline traffic, detect any active threats
2. ARP Monitor (120s)        — dedicated MITM check
3. LAN Scanning              — enumerate hosts and open ports
4. WiFi Audit                — survey the wireless landscape
5. TLS Audit                 — check HTTPS health on discovered hosts
6. Bluetooth Recon           — survey nearby Bluetooth devices
7. Anomaly Detection         — cross-analyse all session data
8. Reports                   — generate HTML summary for record-keeping
```

Run Anomaly Detection last — it is most useful once several other modules have built up session history.
