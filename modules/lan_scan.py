# pyre-ignore-all-errors
import time
import nmap
import socket
from utils.logger import get_logger
from utils.result_handler import create_result

logger = get_logger()

# Helper function to get the local IP block of an interface.
# Note: For cross-platform reliability, a robust implementation would use netifaces or psutil. 
# We use a simple socket trick here for demonstration purposes, normally defaulting to the local subnet.
def get_local_subnet():
    try:
        # Connect to an external IP to find the preferred local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Assume a standard /24 subnet for LAN
        parts = local_ip.split('.')
        base_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        return base_ip
    except Exception as e:
        logger.error(f"Could not determine local subnet: {e}")
        return "192.168.1.0/24" # Fallback

def run(config, callback=None, target=None, **kwargs):
    """
    Standard contract implementation for the LAN Scan module.
    """
    module_name = "lan_scan"
    logger.info(f"Running {module_name} module...")
    
    # Retrieve specific config for this module
    mod_config = config.get("modules", {}).get(module_name, {})
    interface = mod_config.get("interface", "eth0")
    
    if not mod_config.get("enabled", False):
        logger.warning(f"Module {module_name} is disabled in config.")
        if callback: callback(f"[!] Module {module_name} is disabled in config.")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    subnet = target if (target and target.strip()) else get_local_subnet()
    logger.debug(f"Targeting Subnet: {subnet} on interface: {interface}")
    
    # --- ACTUAL NMAP SCAN LOGIC ---
    print(f"[{module_name}] Starting nmap scan on {subnet}...")
    if callback: callback(f"[*] Dispatching Nmap interface mapping sequence on {interface}...")
    if callback: callback(f"[*] Target subnet acquired: {subnet}")
    time.sleep(0.5)
    if callback: callback(f"[*] Executing ICMP Sweep to identify active nodes...")
    
    nm = nmap.PortScanner(nmap_search_path=('nmap', '/usr/bin/nmap', '/usr/local/bin/nmap', '/sw/bin/nmap', '/opt/local/bin/nmap', '/opt/homebrew/bin/nmap'))
    
    try:
        # Perform a ping scan to find active hosts quickly
        nm.scan(hosts=subnet, arguments='-sn')
        
        up_hosts = []
        for host in nm.all_hosts():
            if nm[host].state() == 'up':
                up_hosts.append(host)
                if callback: callback(f"[+] Discovered active host: {host}")
                
        active_hosts = []
        if up_hosts:
            logger.info(f"Port scanning {len(up_hosts)} active hosts for services...")
            if callback: callback(f"\n[*] ICMP Sweep Complete. Found {len(up_hosts)} live targets.")
            if callback: callback(f"[*] Engaging parallel deep-scan port enumeration profiling...")
            
            nm.scan(hosts=' '.join(up_hosts), arguments='-F -sV --version-light -T4')
            
            for host in nm.all_hosts():
                if nm[host].state() == 'up':
                    mac_address = nm[host]['addresses'].get('mac', '')
                    vendor = nm[host].get('vendor', {}).get(mac_address, 'Unknown')
                    
                    if callback: callback(f"\n[>] PROFILE TARGET: {host} (MAC: {mac_address} | Vendor: {vendor})")
                    
                    ports = []
                    if 'tcp' in nm[host]:
                        for p in nm[host]['tcp']:
                            port_info = nm[host]['tcp'][p]
                            if port_info['state'] == 'open':
                                if callback: callback(f"    - OPEN: Port {p}/tcp - {port_info.get('name', 'unknown')} ({port_info.get('version', 'unknown')})")
                                ports.append({
                                    "port": p,
                                    "state": "open",
                                    "name": port_info.get('name', 'unknown'),
                                    "product": port_info.get('product', ''),
                                    "version": port_info.get('version', '')
                                })
                    
                    if not ports:
                        if callback: callback(f"    - No openly accessible services detected.")
                                
                    host_info = {
                        "ip": host,
                        "mac": mac_address,
                        "vendor": vendor,
                        "hostname": nm[host].hostname(),
                        "status": "up",
                        "ports": ports
                    }
                    # We store it under 'scan_results' dict format to match GUI expectations
                    active_hosts.append((host, host_info))
                
        scan_data = {
            "hosts_up": len(active_hosts),
            "scan_results": dict(active_hosts)
        }
        
        print(f"[{module_name}] Scan complete. Found {len(active_hosts)} hosts.")
        if callback: callback(f"\n[+] LAN Reconnaissance complete. Cataloged {len(active_hosts)} active entities.")
        
        return create_result(
            module_name=module_name,
            status="success",
            data=scan_data
        )

    except Exception as e:
        error_msg = f"Nmap scan failed: {e}"
        logger.error(error_msg)
        print(f"[{module_name}] Error: {error_msg}")
        if callback: callback(f"[!] FATAL ERROR: {error_msg}")
        return create_result(
            module_name=module_name,
            status="error",
            errors=[error_msg]
        )
