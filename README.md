# 🖧 CyberDeck OS v2.0 - Operations Manual

Welcome to the **Event-Driven MVC** evolution of CyberDeck OS. This guide details how to test and verify every module in the arsenal in real-time safely.

---

## 🚀 System Boot

To launch the operating system and spin up the EventBus, Background Schedulers, and UI Routers:

```bash
source .venv/bin/activate
sudo python3 boot/launcher.py
```
*(Running with `sudo` is highly recommended, as packet sniffing, ping sweeps, and Bluetooth discovery often require root hardware privileges on macOS/Linux).*

---

## 🔍 I. The Reconnaissance Grid

Recon modules actively probe your network.

**1. LAN Scanner**
*   **Where:** `[ Recon ]` Tab -> `[ LAN Scan ]`
*   **How to Test:** Click the button. Watch the live terminal console stream Nmap outputs. 
*   **Real-time Check:** Wait for the scan to finish. Instantly switch to the `[ Dashboard ]` tab. You will see the "Global Risk", "Entities Tracked", and "Live Nodes" counters dynamically increase across the EventBus!

**2. 802.11 WiFi Audit**
*   **Where:** `[ Recon ]` Tab -> `[ 802.11 WiFi ]`
*   **How to Test:** Click the button. The console will display detected SSIDs, MAC addresses, and crypto types.
*   **Real-time Check:** Switch to the `[ History ]` tab. Select the newest "WiFi Audit" log. Click `[ ANALYTICS CHART ]` to see a dynamic `matplotlib` bar chart visualizing the signal strength (dBm) of the Access Points you just discovered.

**3. Bluetooth Recon**
*   **Where:** `[ Recon ]` Tab -> `[ Bluetooth ]`
*   **How to Test:** Ensure your Mac/Linux Bluetooth hardware is enabled. Click the module.
*   **Real-time Check:** Open the `[ History ]` tab -> `[ FORMATTED REPORT ]` to see a clean Markdown breakdown of nearby Bluetooth devices, their MAC addresses, and hardware profiles.

**4. DNS Subdomain Enumerator**
*   **Where:** `[ Recon ]` Tab -> `[ DNS Enum ]`
*   **How:** Input a target domain (e.g., `example.com`) into the Target Vector.
*   **Benefit:** Resolves subdomains via Python sockets to map the external attack surface of a corporation (finding hidden staging or dev servers).

**5. Web Directory Fuzzer**
*   **Where:** `[ Recon ]` Tab -> `[ Dir Fuzz ]`
*   **How:** Input a target web URL/IP.
*   **Benefit:** Launches a threaded concurrent HTTP brute-force attack against a built-in wordlist to discover hidden admin panels, `.git` configs, and backup `.zip` files hosted on the web server.

**6. OSINT IP Geo-Locator**
*   **Where:** `[ Recon ]` Tab -> `[ OSINT Geo ]`
*   **How:** Input a target public IP or URL.
*   **Benefit:** Queries a public routing registry API to instantly pivot an IP address into a physical GPS location, City, ISP, and Corporate ASN for real-world footprinting.

**7. Built-in SSH Client**
*   **Where:** `[ Recon ]` Tab -> `[ SSH Connect ]`
*   **How:** Input a target IP. Click to spawn an interactive terminal overlay.
*   **Benefit:** Allows the operator to launch remote interactive Bash shells natively from within the CyberDeck GUI using `subprocess` without spawning external terminal windows.

---

## 👁️ II. Passive Surveillance

Surveillance modules listen without broadcasting to the network.

**8. Passive Packet Sniffer**
*   **Where:** `[ Monitor ]` Tab -> `[ Passive Sniffer ]`
*   **How to Test:** Click the button to start the `scapy` packet capture stream. 
*   **Real-time Check:** Open a web browser and go to `http://neverssl.com` (an unencrypted HTTP site). Stop the sniffer and check the `[ History ]` tab. You should see anomalous port 80 traffic flagged in the report!

---

## 🛡️ III. Defense & Countermeasures

**Prerequisite:** You MUST go to `[ Settings ]` and check the **"Enable Lab Mode"** box first. Offensive tools and active traps are safety-locked by default.

**9. Active Deception (FTP Honeypot)**
*   **Where:** `[ Defense ]` Tab -> `[ Deploy FTP Honeypot ]`
*   **How to Test:** Start the Honeypot. Then, from *another computer* or your terminal, try to connect to it: `ftp 127.0.0.1 2121`
*   **Real-time Check:** The `[ Defense ]` module console will instantly scream in red text that a connection attempt was blocked. If you check the `[ Dashboard ]`, the **Risk Score** will have permanently spiked by +5 points per hit!

**10. Password Auditor (Brute-Force)**
*   **Where:** `[ Defense ]` Tab -> `[ Password Auditor ]`
*   **How to Test:** Click to launch a simulated threaded dictionary attack against common default credentials.
*   **Real-time Check:** Watch the UI explicitly print auth failures before finally cracking the root account, generating a `[ SUCCESS ]` payload to the EventBus.

**11. Metasploit RPC Bridge**
*   **Where:** `[ Defense ]` Tab -> `[ Metasploit RPC ]`
*   **How to Test:** Click to query the MSFRPC daemon (or the localized simulation fallback) for known exploit vectors against open ports.
*   **Real-time Check:** The console traces the vulnerability mapping logic interactively matching FTP and SSH to `vsftpd_234_backdoor` and `libssh_auth_bypass`.

**12. Stealth Mode (MAC Spoofing)**
*   **Where:** `[ Defense ]` Tab -> `[ Stealth Mode ]`
*   **How to Test:** Click to execute a randomized interface hardware spoof.
*   **Real-time Check:** The UI tracks the interface teardown, address injection, and promiscuous mode reboot synchronously.

**13. Payload Generator**
*   **Where:** `[ Defense ]` Tab -> `[ Payload Gen ]`
*   **How:** Interactive pop-up to input your Local Host IP and Port.
*   **Benefit:** Instantly generates copy-pasteable Reverse Shell payloads in Bash, Python, and PowerShell natively inside the UI for exploitation.

**14. Interactive Hash Cracker**
*   **Where:** `[ Defense ]` Tab -> `[ Hash Cracker ]`
*   **How:** Interactive pop-up to select Hash Type (MD5, SHA1, SHA256) and paste a stolen hash string.
*   **Benefit:** Rapidly brute-forces the hash locally using a built-in Python threading engine against common password permutations until a plaintext collision is found.

**15. Netcat Shell Listener**
*   **Where:** `[ Defense ]` Tab -> `[ NC Listener ]`
*   **How:** Interactive pop-up to bind a port.
*   **Benefit:** CyberDeck acts as the C2 Server. It spawns an interactive `nc -lvnp` subprocess listener right inside the GUI to catch inbound reverse shells generated by the Payload tool.

**16. System Lockdown**
*   **Where:** `[ Dashboard ]` Tab -> `[ EMERGENCY LOCKDOWN ]`
*   **How to Test:** Click the big red button and confirm the prompt.
*   **Real-time Check:** The UI banner flashes RED. Try to go to the `[ Automation ]` tab and start the daemon—the UI will forcibly block you, proving the `AppState` global singleton constraints.

---

## 🧠 IV. AI Threat Intelligence

**17. Gemini CVE Mapping**
*   **Where:** `[ History ]` Tab -> Select Any Recent Scan -> `[🧠 AI THREAT ANALYSIS ]`
*   **How to Test:** After discovering services on your network, go to your History log. Click a scan record, then click the purple AI analysis button.
*   **Real-time Check:** CyberDeck securely bundles the raw JSON payload and transmits it to the Google Gemini API. It instructs the LLM to cross-reference your exact node topology against the global Common Vulnerabilities and Exposures (CVE) database. When completed, a master `AI CVE Mapper` threat report effortlessly populates your History listbox for review!

---

## 📊 V. Reporting & Analytics

**18. Executive Summary Reports**
*   **Where:** `[ Sidebar ]` -> `[ REPORTS ]`
*   **How to Test:** Execute several modules (LAN Scan, WiFi Audit, etc.). Click the Reports button.
*   **Real-time Check:** The system aggregates all telemetry from `logs/history.json` and produces an executive summary. A new window spawns allowing you to browse all previous `.json` result files from the `results/` directory directly within the GUI.

---

## ⚙️ VI. Automation & State

**19. Background Scheduler**
*   **Where:** `[ Automation ]` Tab
*   **How to Test:** Set the Sweep Interval to `1` minute. Click `[ START DAEMON ]`.
*   **Real-time Check:** Do not touch the computer. Exactly 60 seconds later, watch your `[ Dashboard ]` Operation metrics and threads autonomously increase as the background worker fires a LAN scan silently.

**20. Airspace Topology Router**
*   **Where:** Any recon scan.
*   **How to Test:** Run a LAN or WiFi sweep.
*   **Real-time Check:** Look at the main Python background terminal (where you ran `boot/launcher.py`). The controller logs will prove that the thread gracefully bundled the raw JSON, hit the `EventBus`, updated the `AppState`, and saved to `logs/history.json` safely.

---

## 🛠️ VII. Deployment (Kali Linux / Raspberry Pi)

To turn a Raspberry Pi running Kali Linux into a headless autonomous CyberDeck that launches the OS automatically when plugged in, configure a `systemd` service:

**1. Create the Service File**
```bash
sudo nano /etc/systemd/system/cyberdeck.service
```

**2. Add the Configuration**
*(Adjust `/home/kali/Cyber_Deck-ESAIP` to match your actual installation path)*
```ini
[Unit]
Description=CyberDeck OS Auto-Boot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/kali/Cyber_Deck-ESAIP
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/kali/.Xauthority"
ExecStart=/home/kali/Cyber_Deck-ESAIP/.venv/bin/python3 /home/kali/Cyber_Deck-ESAIP/boot/launcher.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```
*Note: The `DISPLAY` and `XAUTHORITY` exports are required for Tkinter strictly if you want the GUI to render on the physical HDMI display. If you remove the UI later for a purely headless cron-box, you can remove those.*

---

### End of Line.
*Happy Hunting.*
