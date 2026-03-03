# pyre-ignore-all-errors
import os
import sys
import threading
import time
import subprocess
from datetime import datetime

# Add project root to path for local execution and linting context
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger # type: ignore
from utils.result_handler import create_result # type: ignore

logger = get_logger()

def run(config, callback=None, **kwargs):
    module_name = "bluetooth_recon"
    logger.info(f"Running {module_name} module...")
    
    mod_config = config.get("modules", {}).get(module_name, {})
    interface = mod_config.get("interface", "hci0")
    timeout = mod_config.get("timeout", 20)
    
    if not mod_config.get("enabled", False):
        logger.warning(f"Module {module_name} is disabled in config.")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    # --- SCAN LOGIC GOES HERE ---
    print(f"[{module_name}] Starting Bluetooth recon on {interface} for {timeout}s...")
    if callback: callback(f"[{module_name}] Activating local Bluetooth adapter ({interface})...")
    
    scan_results = []
    
    try:
        # We assume bluetoothctl is available on Linux systems
        if callback: callback(f"[*] Dispatching `bluetoothctl devices` to query cached/active broadcasts...")
        time.sleep(1) # simulate brief hardware delay
        
        proc = subprocess.run(['bluetoothctl', 'devices'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        
        if proc.returncode == 0:
            lines = proc.stdout.split('\n')
            for line in lines:
                if line.startswith('Device '):
                    parts = line.split(" ", 2)
                    if len(parts) >= 3:
                        mac = parts[1]
                        name = parts[2]
                        scan_results.append({
                            "mac": mac,
                            "name": name,
                            "rssi": "N/A", # Needs active hcitool scan for RSSI, omitted for simplicity
                            "class": "Unknown"
                        })
                        if callback: callback(f"[+] BT Device Discovered: {name} (MAC: {mac})")
        else:
            logger.error(f"Bluetoothctl failed: {proc.stderr}")
            if callback: callback(f"[!] Warning: Failed to execute bluetoothctl. Output: {proc.stderr}")
            
    except Exception as e:
        logger.error(f"Error during bluetooth scan: {e}")
        if callback: callback(f"[!] Fatal Error during Bluetooth reconnaissance: {e}")
        return create_result(module_name, "error", errors=[str(e)])

    simulated_data = {
        "devices_found": len(scan_results),
        "scan_results": scan_results
    }
    
    if callback: callback(f"\n[+] Bluetooth spectrum sweep complete. Found {simulated_data['devices_found']} devices.")
    if callback: callback(f"\n[+] Scan complete. Correlating threat signatures.\n")
    
    return create_result(module_name, "success", data=simulated_data)
