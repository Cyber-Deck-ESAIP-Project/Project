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

### 1. LAN Scanner (`modules/lan_scan.py`)
Active network sweeps to identify alive hosts and open ports.

### 2. 802.11 WiFi Audit (`modules/wifi_audit.py`)
Passive scanning of wireless networks for security profiling.

### 3. Bluetooth Recon (`modules/bluetooth_recon.py`)
Discovery of nearby Bluetooth devices and hardware profiles.

### 4. Pentest Tools (`modules/pentest_tools.py`)
Integration with external vulnerability scanning frameworks.

### 5. AI Anomaly Detection (`modules/anomaly_detect.py`)
Heuristic analysis of network traffic for threat identification.

### 6. Reports & Analytics (`modules/dashboard.py`)
Executive summary generation and result visualization.

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
