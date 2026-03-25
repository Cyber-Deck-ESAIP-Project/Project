# Real-Time DNS Query Monitor

A Python-based module for real-time DNS traffic monitoring and basic threat detection, designed for integration with the Cyber Deck project.

## Features
- Captures and analyzes DNS queries in real time using Scapy
- Displays live DNS queries in the terminal with suspicious queries highlighted
- Flags suspicious domains based on heuristics (length, randomness, uncommon TLDs)
- Logs all DNS queries to a file for later analysis
- Tracks statistics: total queries, suspicious count, top queried domains
- Modular, well-commented, and easy to integrate

## Usage
```sh
sudo python3 monitor.py [-i <interface>]
```
- `-i <interface>`: (Optional) Specify network interface to sniff (default: all)

## Requirements
- Python 3.x
- Scapy (`pip install scapy`)

## Integration
- Place this folder in `modules/dns_monitor/`
- Call `main()` from your cyberdeck menu or CLI

## Notes
- Requires root privileges for packet capture
- Efficient and suitable for demonstration in cybersecurity projects
