# pyre-ignore-all-errors
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger  # type: ignore
from utils.result_handler import create_result  # type: ignore

logger = get_logger()

try:
    from scapy.all import sniff, ARP  # type: ignore
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("scapy not installed. ARP monitor unavailable. Run: pip install scapy")


def run(config: dict, callback=None, **kwargs) -> dict:
    module_name = "arp_monitor"
    logger.info(f"Running {module_name} module...")

    mod_config = config.get("modules", {}).get(module_name, {})
    if not mod_config.get("enabled", False):
        if callback: callback(f"[-] Module {module_name} disabled.")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    if not SCAPY_AVAILABLE:
        msg = "Scapy library not installed. Cannot run ARP monitor. Run: pip install scapy"
        if callback: callback(f"[!] {msg}")
        return create_result(module_name, "error", errors=[msg])

    interface = mod_config.get("interface", "eth0")
    duration = mod_config.get("duration", 120)

    if callback: callback(f"[*] ARP Monitor starting on {interface} for {duration}s...")
    if callback: callback(f"[*] Building IP -> MAC table. Conflicts will be flagged in real time.")

    # Shared capture state
    arp_table: Dict[str, str] = {}              # ip -> mac (first-seen = trusted baseline)
    conflict_events: List[Dict[str, Any]] = []
    arp_packet_count = [0]

    def arp_handler(pkt):
        if not pkt.haslayer(ARP):
            return
        arp_packet_count[0] += 1
        layer = pkt[ARP]
        ts = datetime.now().strftime("%H:%M:%S")

        src_ip = layer.psrc
        src_mac = layer.hwsrc

        # Skip link-local/unset addresses
        if not src_ip or src_ip == "0.0.0.0":
            return

        if src_ip in arp_table:
            if arp_table[src_ip] != src_mac:
                event: Dict[str, Any] = {
                    "timestamp": ts,
                    "ip": src_ip,
                    "original_mac": arp_table[src_ip],
                    "new_mac": src_mac,
                    "arp_op": "reply" if layer.op == 2 else "request",
                    "severity": "CRITICAL",
                    "reason": (
                        f"IP {src_ip} changed MAC from {arp_table[src_ip]} to {src_mac}"
                    ),
                }
                conflict_events.append(event)
                if callback:
                    callback(
                        f"[!] ARP CONFLICT [{ts}]: {src_ip} -- "
                        f"was {arp_table[src_ip]}, now {src_mac} (possible MITM)"
                    )
                arp_table[src_ip] = src_mac  # update to latest seen
        else:
            arp_table[src_ip] = src_mac

    try:
        # BPF filter "arp" restricts capture to ARP frames only — efficient on busy networks
        sniff(iface=interface, filter="arp", timeout=duration, prn=arp_handler, store=False)
    except PermissionError:
        msg = "Permission denied. ARP monitor requires root privileges (run with sudo)."
        logger.error(msg)
        if callback: callback(f"[!] FATAL: {msg}")
        return create_result(module_name, "error", errors=[msg])
    except OSError as e:
        msg = f"Interface error on '{interface}': {e}"
        logger.error(msg)
        if callback: callback(f"[!] FATAL: {msg}")
        return create_result(module_name, "error", errors=[msg])
    except Exception as e:
        msg = f"ARP capture failed: {e}"
        logger.error(msg)
        if callback: callback(f"[!] FATAL: {msg}")
        return create_result(module_name, "error", errors=[msg])

    # Summary
    total_pkt = arp_packet_count[0]
    total_hosts = len(arp_table)
    total_conflicts = len(conflict_events)

    if callback:
        callback(f"\n[+] ARP Monitor complete. {total_pkt} ARP packets, {total_hosts} unique hosts.")
    if total_conflicts:
        if callback: callback(f"[!] {total_conflicts} MAC conflict(s) detected -- possible MITM activity!")
    else:
        if callback: callback(f"[+] ARP table stable. No conflicts detected.")

    if arp_table and callback:
        callback(f"\n[*] ARP Table Snapshot ({total_hosts} entries):")
        for ip, mac in sorted(arp_table.items()):
            callback(f"    {ip:<18} -> {mac}")

    logger.info(f"{module_name} complete. {total_pkt} ARP pkts, {total_conflicts} conflicts.")

    return create_result(
        module_name=module_name,
        status="success",
        data={
            "monitored_seconds": duration,
            "total_arp_packets": total_pkt,
            "unique_hosts": total_hosts,
            "arp_table": arp_table,
            "conflict_events": conflict_events,
        },
    )
