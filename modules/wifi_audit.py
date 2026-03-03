# pyre-ignore-all-errors
import sys
import os
# Fix for IDE path resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from utils.logger import get_logger # type: ignore
from utils.result_handler import create_result # type: ignore

logger = get_logger()

def run(config, callback=None, **kwargs):
    module_name = "wifi_audit"
    logger.info(f"Running {module_name} module...")
    
    mod_config = config.get("modules", {}).get(module_name, {})
    interface = mod_config.get("interface", "wlan1")
    
    if not mod_config.get("enabled", False):
        if callback: callback("[-] MODULE DISABLED IN CONFIGURATION.\n")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    # --- SCAN LOGIC GOES HERE ---
    if callback: callback(f"[{module_name}] Starting Wi-Fi audit on {interface}...")
    time.sleep(1)
    if callback: callback(f"[*] Sweeping 802.11 spectrum for active beacons and probes via nmcli...")
    
    networks = []
    rogue_aps = [] # Needs more advanced analysis or kismet, kept empty for standard nmcli
    
    try:
        import subprocess
        import re
        # Using nmcli for broader compatibility on modern linux without requiring root for basic scan
        # Format: BSSID:SSID:SIGNAL:SECURITY
        proc = subprocess.run(['nmcli', '-t', '-f', 'BSSID,SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        
        if proc.returncode == 0:
            lines = proc.stdout.strip().split('\n')
            for line in lines:
                if not line: continue
                # Regex for splitting by ':' NOT preceded by '\'
                # This correctly handles nmcli's escaped colons.
                parts = re.split(r'(?<!\\):', line)
                
                if len(parts) >= 4:
                    bssid = parts[0].replace('\\:', ':')
                    ssid = parts[1].replace('\\:', ':') if parts[1] else "Hidden"
                    signal = parts[2]
                    security = parts[3]
                    
                    flags = []
                    if not security or "WPA1" in security or "WEP" in security: flags.append("WEAK_CRYPTO")
                    if not security: flags.append("OPEN_NETWORK")
                    
                    networks.append({
                        "bssid": bssid,
                        "ssid": ssid,
                        "rssi": f"{signal}%",
                        "crypto": security if security else "OPN",
                        "flags": flags
                    })
        else:
             logger.error(f"nmcli failed: {proc.stderr}")
             if callback: callback(f"[!] Warning: Failed to execute nmcli. Output: {proc.stderr}")
             
    except Exception as e:
        logger.error(f"Error during WiFi scan: {e}")
        if callback: callback(f"[!] Fatal Error during WiFi reconnaissance: {e}")
        return create_result(module_name, "error", errors=[str(e)])
        
    all_networks = networks + rogue_aps
    
    if callback: callback(f"\n[+] Spectrum Sweep Complete. Found {len(all_networks)} Access Points.")
    if callback: callback(f"[*] Extracting detailed AP profiles...\n")
    
    # Sort by signal strength (descending)
    all_networks.sort(key=lambda x: int(x['rssi'].replace('%','')), reverse=True)

    for ap in all_networks:
        flags_str = " | ".join(ap['flags']) if ap['flags'] else "OK"
        # User requested SSID first!
        log_line = f"[{ap['ssid']}] (BSSID: {ap['bssid']} | Sig: {ap['rssi']} | {ap['crypto']})"
        
        if "EVIL" in flags_str or "SUSPECT" in flags_str:
            if callback: callback(f"[!] ROGUE AP: {log_line} -> FLAGS: [{flags_str}]")
        elif "OPEN" in flags_str or "WEAK" in flags_str:
            if callback: callback(f"[-] VULNERABLE AP: {log_line} -> FLAGS: [{flags_str}]")
        else:
            if callback: callback(f"[+] AP: {log_line}")
    
    scan_data = {
        "networks_found": len(networks),
        "rogue_aps_detected": len(rogue_aps),
        "scan_results": all_networks
    }
    
    if callback: callback(f"\n[+] Scan complete. Correlating threat signatures.\n")
    
    return create_result(module_name, "success", data=scan_data)
