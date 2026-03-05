# 🖧 CyberDeck OS v2.0 - Operations Manual

Welcome to the **Event-Driven MVC** evolution of CyberDeck OS. This guide details how to test and verify every module in the arsenal in real-time safely.

---

## 🚀 System Boot

To launch the operating system and spin up the EventBus, Background Schedulers, and UI Routers:

```bash
source .venv/bin/activate
sudo python3 launcher.py
```
*(Running with `sudo` is highly recommended, as packet sniffing, ping sweeps, and Bluetooth discovery often require root hardware privileges).*

---

## 🔍 Modules Reference

### 1. Passive Monitor (`modules/passive_monitor.py`)
Multi-protocol Scapy packet capture. Detects ARP spoofing, TCP port scans, and ICMP floods in real time. Receive-only mode — no packets transmitted. Requires root.

### 2. ARP Monitor (`modules/arp_monitor.py`)
Dedicated ARP traffic auditor. Builds an IP→MAC trust table and flags any host that changes its MAC address — a key MITM indicator. Uses a BPF "arp" filter for low overhead. Requires root.

### 3. LAN Scanner (`modules/lan_scan.py`)
Active network sweeps to identify alive hosts and open ports via `python-nmap`.

### 4. 802.11 WiFi Audit (`modules/wifi_audit.py`)
Passive scanning of wireless networks for security profiling via `nmcli`. Flags open and WEP-encrypted networks.

### 5. Bluetooth Recon (`modules/bluetooth_recon.py`)
Discovery of nearby Bluetooth devices and hardware profiles via `bluetoothctl`.

### 6. TLS Audit (`modules/tls_audit.py`)
TLS certificate health checker for HTTPS hosts. Accepts a single IP, hostname, or subnet from the target field. Detects expired certs, short expiry windows, self-signed certs, hostname mismatches, and deprecated TLS versions. Uses only stdlib `ssl` — no new dependencies.

### 7. Pentest Tools (`modules/pentest_tools.py`)
Integration with Metasploit MSFRPC. Falls back to a port-to-exploit simulation if no daemon is running.

### 8. AI Anomaly Detection (`modules/anomaly_detect.py`)
Heuristic analysis of session history across 7 rules. Optional Gemini AI narrative via `GEMINI_API_KEY`.

### 9. Reports & Analytics (`modules/dashboard.py`)
Executive summary generation and result visualization. Auto-generates an HTML report on every run.

---

## 📊 Documentation
Detailed technical guides are available in the `docs/` directory:
- [Architecture Overview](docs/architecture.md)
- [Installation Guide](docs/installation.md)
- [Development Workflow](docs/workflow.md)
- [User Guide](docs/user_guide.md)

---

## ⚙️ Deployment (Raspberry Pi)
To turn a Raspberry Pi into an autonomous CyberDeck, use the provided scripts:
1. Initialize environment: `./scripts/setup_env.sh`
2. Deploy latest code: `./scripts/deploy.sh`

### End of Line.
*Happy Hunting.*
