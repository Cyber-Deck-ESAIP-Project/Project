#!/bin/bash
# CyberDeck OS Deployment Script
# Automatically pulls the latest code and restarts services on a Raspberry Pi.

PROJECT_DIR="/home/psk03/Downloads/Cyber_Deck-ESAIP"

echo "[*] Pulling latest code from origin/main..."
cd $PROJECT_DIR
git fetch origin
git reset --hard origin/main

echo "[*] Ensuring dependencies are satisfied..."
source .venv/bin/activate
pip install -r requirements.txt

echo "[*] Restarting CyberDeck service..."
sudo systemctl restart cyberdeck.service

echo "[+] Deployment successful."
