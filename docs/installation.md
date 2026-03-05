# Installation & Setup Guide

Complete setup guide for CyberDeck OS v2.0 on Linux, macOS, and Raspberry Pi.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | Required |
| pip | Latest | Comes with Python |
| nmap | Any | Required for LAN Scanning |
| bluetoothctl | Any | Required for Bluetooth Recon (part of `bluez`) |
| nmcli | Any | Required for WiFi Audit (part of `network-manager`) |
| Root/sudo | — | Required for packet capture, ping sweep, Bluetooth |

---

## Standard Installation (Linux / macOS)

### 1. Clone the Repository

```bash
git clone https://github.com/Cyber-Deck-ESAIP-Project/Project.git
cd Project
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

The setup script installs both system packages (via `apt`) and Python packages (via `pip`):

```bash
./scripts/setup_env.sh
```

What it installs:
- **System**: `nmap`, `bluetooth`, `bluez`, `wireless-tools`
- **Python**: `python-nmap`, `scapy`, `pymetasploit3`, `google-generativeai`

On macOS, run the pip install manually if apt is unavailable:
```bash
pip install -r requirements.txt
```

### 4. Configure Interface Names

Copy the example config and edit it to match your hardware:

```bash
cp config/config.example.json config/config.json
```

Key fields to update in `config/config.json`:

```json
"modules": {
    "lan_scan":        { "interface": "eth0"  },   // your wired interface
    "wifi_audit":      { "interface": "wlan1" },   // your wireless interface
    "bluetooth_recon": { "interface": "hci0"  },   // your Bluetooth adapter
    "passive_monitor": { "interface": "eth0"  },   // interface to sniff on
    "arp_monitor":     { "interface": "eth0"  }    // interface to monitor ARP
}
```

To find your interface names:
```bash
ip link show          # lists all network interfaces
hciconfig             # lists Bluetooth adapters
```

### 5. Set Gemini API Key (optional)

Enables the AI threat narrative in Anomaly Detection. Set as an environment variable — do not put the key in `config.json`:

```bash
export GEMINI_API_KEY="your-key-here"
```

To make it persist across sessions, add it to your shell profile (`~/.bashrc` or `~/.zshrc`).

### 6. Launch

```bash
sudo python3 launcher.py
```

`sudo` is required because packet capture (Scapy), ping sweeps (Nmap), and Bluetooth scanning all need raw socket access.

---

## Raspberry Pi Deployment (Kali Linux / Raspberry Pi OS)

### Initial Setup

Follow all standard installation steps above, then continue:

### Enable Auto-Boot via systemd

Create a service file so CyberDeck starts automatically on boot:

```bash
sudo nano /etc/systemd/system/cyberdeck.service
```

Paste the following (adjust `User` and paths to match your Pi):

```ini
[Unit]
Description=CyberDeck OS v2.0
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/Project
ExecStart=/home/pi/Project/.venv/bin/python3 /home/pi/Project/launcher.py
Restart=on-failure
Environment=DISPLAY=:0
Environment=GEMINI_API_KEY=your-key-here

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cyberdeck.service
sudo systemctl start cyberdeck.service
```

Check status:
```bash
sudo systemctl status cyberdeck.service
```

### Subsequent Updates

Use `deploy.sh` to pull the latest code and restart the service automatically:

```bash
./scripts/deploy.sh
```

The script:
1. `git fetch origin && git reset --hard origin/main`
2. Re-runs `pip install -r requirements.txt`
3. `sudo systemctl restart cyberdeck.service`

### WiFi Monitor Mode (for advanced passive scanning)

Some modules benefit from a wireless adapter in monitor mode. To enable:

```bash
sudo ip link set wlan1 down
sudo iw dev wlan1 set type monitor
sudo ip link set wlan1 up
```

Not all adapters support monitor mode — check your chipset. Common compatible chipsets include Atheros AR9271 and Ralink RT3070.

---

## Dependency Reference

| Package | Version | Purpose | Optional |
|---|---|---|---|
| `python-nmap` | 0.7.1 | LAN Scanning | No |
| `scapy` | 2.7.0 | Passive Monitor, ARP Monitor | No |
| `pymetasploit3` | 1.0.3 | Pentest Toolkit (MSFRPC) | Yes — has simulation fallback |
| `google-generativeai` | 0.3.1 | Anomaly Detection (AI narrative) | Yes — skipped gracefully if absent |

All other modules use Python stdlib only (`ssl`, `subprocess`, `socket`, `ipaddress`, etc.).

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: scapy` | Virtual env not active or pip install failed | `source .venv/bin/activate && pip install scapy` |
| `Permission denied` on packet capture | Not running as root | `sudo python3 launcher.py` |
| `Interface error on 'eth0'` | Wrong interface name in config | Update `config/config.json` with your actual interface name |
| `nmcli: command not found` | `network-manager` not installed | `sudo apt install network-manager` |
| `bluetoothctl: command not found` | `bluez` not installed | `sudo apt install bluez` |
| Tkinter window does not open over SSH | No display forwarding | Use `ssh -X` or run on the physical display |
| `nmap: command not found` | nmap not installed | `sudo apt install nmap` |
