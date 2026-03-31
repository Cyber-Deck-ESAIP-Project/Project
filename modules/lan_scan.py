# pyre-ignore-all-errors
import time
import nmap
import subprocess
from utils.logger import get_logger
from utils.result_handler import create_result

logger = get_logger()

def get_local_subnet(interface="wlan0"):
    """Detect subnet from the configured network interface using ip addr."""
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", interface],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                # e.g. "inet 172.16.0.132/24 brd ..."
                cidr = line.split()[1]  # "172.16.0.132/24"
                ip, prefix = cidr.split("/")
                parts = ip.split(".")
                subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.0/{prefix}"
                logger.info(f"Auto-detected subnet from {interface}: {subnet}")
                return subnet
    except Exception as e:
        logger.error(f"Could not detect subnet from {interface}: {e}")
    return "192.168.1.0/24"  # Fallback

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

    _invalid = {"", "127.0.0.1", "localhost"}
    if target and target.strip() and target.strip() not in _invalid:
        subnet = target.strip()
    else:
        subnet = get_local_subnet(interface)
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

            max_deep = int(mod_config.get("max_deep_scan_hosts", 30))
            deep_hosts = up_hosts[:max_deep]
            skipped = len(up_hosts) - len(deep_hosts)

            if callback: callback(f"[*] Deep scanning {len(deep_hosts)} hosts (max_deep_scan_hosts={max_deep}).")
            if skipped:
                if callback: callback(f"[*] {skipped} additional hosts discovered but skipped for deep scan.")
            if callback: callback(f"[*] Engaging parallel deep-scan port enumeration profiling...")

            nm.scan(hosts=' '.join(deep_hosts), arguments='-F -sV -T4 --host-timeout 30s --max-retries 2')
            
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
