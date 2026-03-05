# 📥 Installation & Setup Guide

Get CyberDeck OS up and running on your hardware.

## Prerequisites
- **Python**: 3.12+ 
- **System Tools**: `nmap`, `bluetoothctl`, `nmcli`, `iwlist`.
- **Permissions**: Root/Sudo privileges are required for most hardware-level scans.

## Standard Installation (Linux/macOS)
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/psharma-03/Cyber_Deck-ESAIP.git
    cd Cyber_Deck-ESAIP
    ```
2.  **Setup Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    ./scripts/setup_env.sh
    ```
4.  **Configure** (optional):
    ```bash
    cp config/config.example.json config/config.json
    # Edit config/config.json to set your interface names (eth0, wlan1, hci0)
    ```
5.  **Set Gemini API key** (optional — enables AI threat narrative in Anomaly Detection):
    ```bash
    export GEMINI_API_KEY="your-key-here"
    ```

## Raspberry Pi Deployment (Kali Linux)
1.  Follow the standard installation steps above.
2.  To enable auto-boot on startup, use the `systemd` service configuration details provided in the `README.md`.
3.  Ensure your wireless adapter supports monitor mode if using advanced WiFi features.
4.  Use `scripts/deploy.sh` to pull and restart on subsequent updates — the script auto-detects its location.
