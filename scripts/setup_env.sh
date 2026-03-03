#!/bin/bash
# Environment Setup Script for CyberDeck OS v2.0

echo "[*] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y nmap bluetooth bluez wireless-tools

echo "[*] Installing Python requirements..."
pip install -r requirements.txt

echo "[+] Setup complete. You can now launch the deck using 'sudo python3 launcher.py'."
