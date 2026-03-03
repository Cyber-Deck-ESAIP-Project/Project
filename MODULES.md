# ⚙️ CyberDeck OS - Technical Reference Manual

This document provides a deep-dive into the underlying architecture of CyberDeck OS. It outlines precisely *how* each module functions under the hood, the required Python libraries, and the native operating system binaries they rely on.

---

## 🔍 I. The Reconnaissance Grid

### 1. LAN Scanner (`modules/nmap_scanner.py`)
*   **Methodology:** Executes synchronous network sweeps targeting the active subnet (e.g., `192.168.1.0/24`) to identify alive hosts, open ports, and running services.
*   **Python Libraries:** `nmap` (`python-nmap` wrapper)
*   **OS Tools Required:** `nmap` (must be installed on the host OS).

### 2. DNS Subdomain Enumerator (`modules/dns_recon.py`)
*   **Methodology:** Utilizes a built-in dictionary wordlist of common subdomains (e.g., `admin`, `api`, `dev`). It iterates through the list, appending the target root domain, and attempts to resolve the A-Record via Python sockets.
*   **Python Libraries:** `socket`, `concurrent.futures.ThreadPoolExecutor`
*   **OS Tools Required:** None. Relies on the host's default DNS resolver.

### 3. Web Directory Fuzzer (`modules/dir_fuzzer.py`)
*   **Methodology:** Launches a multi-threaded HTTP `HEAD`/`GET` brute-force attack against a web server to discover hidden directories and files (e.g., `/.git/`, `/backup.zip`) bypassing standard site crawling.
*   **Python Libraries:** `urllib.request`, `concurrent.futures.ThreadPoolExecutor`
*   **OS Tools Required:** None.

### 4. OSINT IP Geo-Locator (`modules/osint_geo.py`)
*   **Methodology:** Accepts a public IP address or Domain Name and queries a third-party REST API (`http://ip-api.com/json/`) to retrieve the physical GPS coordinates, ISP, Corporate ASN, and City of the target.
*   **Python Libraries:** `urllib.request`, `json`
*   **OS Tools Required:** None.

### 5. 802.11 WiFi Audit (`modules/wifi_audit.py`)
*   **Methodology:** Triggers the native OS wireless network card into a passive scanning state to rapidly identify broadcasting SSIDs, BSSIDs (MAC Addresses), Channel frequencies, and Encryption types (WPA2/WPA3).
*   **Python Libraries:** `subprocess`, `re` (Regex parsing)
*   **OS Tools Required:** 
    *   **macOS:** `/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -s`
    *   **Linux/Kali:** `iwlist wlan0 scan`

### 6. Bluetooth Recon (`modules/bt_scan.py`)
*   **Methodology:** Queries the local Bluetooth hardware stack for cached or actively broadcasting physical devices in the immediate physical vicinity.
*   **Python Libraries:** `subprocess`, `json`
*   **OS Tools Required:** 
    *   **macOS:** `system_profiler SPBluetoothDataType -json`
    *   **Linux/Kali:** `bluetoothctl devices`

### 7. Built-in SSH Client (`ui/recon_container.py`)
*   **Methodology:** Spawns a dedicated asynchronous Popen subprocess that pipes STDIN, STDOUT, and STDERR from the host's native SSH client directly into a Tkinter GUI Text widget to provide an interactive remote shell.
*   **Python Libraries:** `subprocess`, `threading`
*   **OS Tools Required:** `ssh` (OpenSSH Client)

---

## 👁️ II. Passive Surveillance

### 8. Passive Packet Sniffer (`modules/sniffer.py`)
*   **Methodology:** Drops the active network interface into Promiscuous Mode, intercepting raw 802.3 Ethernet frames. It filters and dissects packets in real-time to alert on unencrypted HTTP, FTP, or Telnet traffic containing sensitive data.
*   **Python Libraries:** `scapy.all`
*   **OS Tools Required:** Root/Administrator privileges (e.g., `sudo`) to bind raw sockets.

---

## 🛡️ III. Defense & Countermeasures

### 9. Active Deception (FTP Honeypot) (`modules/honeypot.py`)
*   **Methodology:** Spins up a fake socket-listener binding to port 21 (or custom 2121). It responds to inbound TCP connections with a forged banner (e.g., `vsFTPd 3.0.3`) and captures the attacker's origin IP and attempted credentials before dropping the connection.
*   **Python Libraries:** `socket`, `threading`
*   **OS Tools Required:** None. Pure Python socket implementation.

### 10. Password Auditor (`modules/password_audit.py`)
*   **Methodology:** A multi-threaded simulation tool that tests active network services (FTP, SSH) against a dictionary of weak default credentials to verify system hardening.
*   **Python Libraries:** `paramiko` (for SSH auth), `ftplib` (for FTP auth), `concurrent.futures`
*   **OS Tools Required:** None.

### 11. Metasploit RPC Bridge (`modules/metasploit_rpc.py`)
*   **Methodology:** Authenticates via HTTP-RPC API to a running instance of `msfrpcd` (Metasploit Framework RPC Daemon). It dynamically feeds identified open ports from the LAN Scanner into MSF to automatically identify and optionally detonate corresponding exploit modules.
*   **Python Libraries:** `pymetasploit3`
*   **OS Tools Required:** `msfconsole`, `msfrpcd` (Metasploit Framework must be installed and running in the background).

### 12. Stealth Mode (MAC Spoofing) (`modules/stealth_mode.py`)
*   **Methodology:** Takes down the active network interface, randomly generates a locally-administered MAC address hex string, applies it to the hardware, and brings the link back up to obscure the machine's physical identity on the Local Area Network.
*   **Python Libraries:** `subprocess`, `random`
*   **OS Tools Required:** 
    *   **macOS:** `ifconfig en0 ether [MAC]`
    *   **Linux/Kali:** `macchanger -r wlan0` or `ifconfig eth0 hw ether [MAC]`

### 13. Payload Generator (`ui/defense_container.py`)
*   **Methodology:** A pure frontend string-manipulation utility that dynamically injects the operator's designated Local IP (LHOST) and Local Port (LPORT) into known, weaponized one-liner Reverse Shell strings (Bash, Python, PowerShell, Netcat).
*   **Python Libraries:** `base64`, `urllib.parse`
*   **OS Tools Required:** None.

### 14. Interactive Hash Cracker (`modules/hash_breaker.py`)
*   **Methodology:** A CPU-bound brute-forcing daemon. It takes an input cryptographic hash and aggressively hashes strings from an internal wordlist using standard algorithms (MD5, SHA1, SHA256) until a string collision successfully reveals the plaintext.
*   **Python Libraries:** `hashlib`, `concurrent.futures.ThreadPoolExecutor`
*   **OS Tools Required:** None.

### 15. Netcat Shell Listener (`ui/defense_container.py`)
*   **Methodology:** Spawns a background asynchronous process piping a native Netcat listener to a GUI console. Ready to act as a localized Command and Control (C2) hook for catching reverse shells triggered by the Payload Generator.
*   **Python Libraries:** `subprocess`, `threading`
*   **OS Tools Required:** `nc` (Netcat GNU/BSD binary).

---

## 🧠 IV. AI Threat Intelligence

### 16. Gemini AI CVE Mapping (`modules/ai_analyzer.py`)
*   **Methodology:** Securely authenticates over TLS to Google's cloud infrastructure. It serializes the raw JSON network topology captured by CyberDeck (open ports, discovered MACs, OS fingerprints) into a custom adversarial LLM prompt. The AI cross-references this dataset against real-time global CVEs, returning a marked-up Markdown threat report via the native Tkinter Webview container.
*   **Python Libraries:** `google-generativeai`
*   **OS Tools Required:** None. Requires an active Internet connection and a valid API key in `.env`.

---

## ⚙️ V. Core Architecture & Event Management

### 17. The Event Bus (`core/event_bus.py`)
*   **Methodology:** A Singleton Pub/Sub object pattern. It acts as the central nervous system of CyberDeck OS. Modules publish `Event` objects (e.g., `SCAN_COMPLETE`, `THREAT_DETECTED`) to the bus without knowing who is listening. The UI components subscribe to the bus to dynamically re-render themselves without creating rigid circular dependencies.
*   **Python Libraries:** `threading`, `typing.Callable`

### 18. App State Manager (`core/app_state.py`)
*   **Methodology:** A global thread-safe state machine. It prevents race conditions (e.g., running two Nmap scans simultaneously corrupting the output buffer) and maintains globally accessible variables like `Risk Score` and `System Lockdown` statuses.
*   **Python Libraries:** `threading.Lock`

### 19. Background Daemon (`core/scheduler.py`)
*   **Methodology:** A continuous non-blocking daemon thread. It operates independently of the main Tkinter `mainloop()`. Authorized background modules are registered into the queue, and the scheduler executes them silently at user-defined intervals (e.g., sweeping the LAN every 5 minutes while the operator works on Hash Cracking).
*   **Python Libraries:** `threading`, `time`, `schedule`
