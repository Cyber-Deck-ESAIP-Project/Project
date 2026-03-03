# pyre-ignore-all-errors
import sys
import os
# Fix for IDE path resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from utils.logger import get_logger
from utils.result_handler import create_result

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
        # Using nmcli for broader compatibility on modern linux without requiring root for basic scan
        proc = subprocess.run(['nmcli', '-t', '-f', 'BSSID,SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        
        if proc.returncode == 0:
            lines = proc.stdout.strip().split('\n')
            for line in lines:
                if not line: continue
                # nmcli -t escapes colons in MAC addresses as \: so we need to handle that carefully.
                # Format: BSSID:SSID:SIGNAL:SECURITY
                # It's safer to split from the right for SIGNAL and SECURITY
                parts = line.rsplit(':', 2)
                if len(parts) >= 3:
                    security = parts[2]
                    signal = parts[1]
                    
                    # The rest is BSSID and SSID which might contain escaped colons
                    remainder = parts[0]
                    # BSSID is 17 chars long usually (e.g. AA:BB:CC:DD:EE:FF), but -t escapes it.
                    # Let's just do a basic split for demonstration
                    bssid_ssid = remainder.split(':', 1)
                    
                    bssid = bssid_ssid[0].replace('\\:', ':') if len(bssid_ssid) > 1 else remainder
                    ssid = bssid_ssid[1] if len(bssid_ssid) > 1 else "Hidden"
                    
                    flags = []
                    if not security or security == "WPA1" or security == "WEP": flags.append("WEAK_CRYPTO")
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
    
    for ap in all_networks:
        flags_str = " | ".join(ap['flags']) if ap['flags'] else "OK"
        if "EVIL" in flags_str or "SUSPECT" in flags_str:
            if callback: callback(f"[!] ROGUE AP: {ap['ssid']} (BSSID: {ap['bssid']} | Sig: {ap['rssi']} | {ap['crypto']}) -> FLAGS: [{flags_str}]")
        elif "OPEN" in flags_str or "WEAK" in flags_str:
            if callback: callback(f"[-] VULNERABLE AP: {ap['ssid']} (BSSID: {ap['bssid']} | Sig: {ap['rssi']} | {ap['crypto']}) -> FLAGS: [{flags_str}]")
        else:
            if callback: callback(f"[+] AP: {ap['ssid']} (BSSID: {ap['bssid']} | Sig: {ap['rssi']} | {ap['crypto']})")
    
    scan_data = {
        "networks_found": len(networks),
        "rogue_aps_detected": len(rogue_aps),
        "scan_results": all_networks
    }
    
    if callback: callback(f"\n[+] Scan complete. Correlating threat signatures.\n")
    
    return create_result(module_name, "success", data=scan_data)
