# 📖 User Guide - Operating the Deck

A step-by-step guide for operators to perform field reconnaissance and defense.

## 1. Launching the Deck
Run the following from the root directory:
```bash
sudo python3 launcher.py
```

## 2. Performing a LAN Scan
1.  Enter a target IP or Subnet in the `TARGET_HOST` field (default: `127.0.0.1`).
2.  Click **[ LAN SCANNING ]** on the sidebar.
3.  Watch the console for discovered hosts and open ports.

## 3. WiFi Auditing
1.  Click **[ WIFI AUDIT ]**.
2.  The system will sweep the spectrum and list APs, encryption types, and potential vulnerabilities.

## 4. Reviewing Results
1.  Click the **[ REPORTS ]** button.
2.  The Executive Summary window will open, showing aggregated stats (Total Ops, Entities found).
3.  Select a JSON file from the side list to view the raw data for that specific session.

## 5. Emergency Procedures
- Use the **[ EMERGENCY LOCKDOWN ]** button on the Dashboard tab to instantly halt all active modules and prevent new ones from starting.
