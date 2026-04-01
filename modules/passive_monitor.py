# pyre-ignore-all-errors
import os
import sys
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

# Add project root to path for local execution and linting context
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger  # type: ignore
from utils.result_handler import create_result  # type: ignore

logger = get_logger()

try:
    from scapy.all import sniff, ARP, IP, TCP, ICMP  # type: ignore
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("scapy not installed. Passive monitor unavailable. Run: pip install scapy")

# Detection thresholds
PORT_SCAN_THRESHOLD = 15   # unique dst ports from one src triggers port scan alert
ICMP_FLOOD_THRESHOLD = 50  # ICMP packets from one src triggers flood alert


def run(config: dict, callback=None, **kwargs) -> dict:
    module_name = "passive_monitor"
    logger.info(f"Running {module_name} module...")

    mod_config = config.get("modules", {}).get(module_name, {})
    interface = mod_config.get("interface", "eth0")
    duration = mod_config.get("duration", 60)

    if not mod_config.get("enabled", False):
        if callback: callback(f"[-] Module {module_name} disabled.")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    if not SCAPY_AVAILABLE:
        msg = "Scapy library not installed. Cannot perform passive capture. Run: pip install scapy"
        if callback: callback(f"[!] {msg}")
        return create_result(module_name, "error", errors=[msg])

    if callback: callback(f"[*] Initializing promiscuous mode on {interface}...")
    if callback: callback(f"[*] Capturing packets for {duration}s... (PASSIVE MODE — no packets transmitted)")

    # --- Shared state for the packet handler ---
    anomalous: List[Dict[str, Any]] = []
    packet_count = [0]
    arp_table: Dict[str, str] = {}                    # ip -> mac, for ARP spoof detection
    syn_tracker: Dict[str, set] = defaultdict(set)    # src_ip -> {dst_ports}, for port scan detection
    icmp_counter: Dict[str, int] = defaultdict(int)   # src_ip -> count, for ICMP flood detection

    def packet_handler(pkt):
        packet_count[0] += 1
        ts = datetime.now().strftime("%H:%M:%S")

        # --- ARP Spoofing Detection ---
        # An ARP reply (op=2) advertising a different MAC for an already-seen IP is a spoof indicator.
        if pkt.haslayer(ARP) and pkt[ARP].op == 2:
            sender_ip = pkt[ARP].psrc
            sender_mac = pkt[ARP].hwsrc
            if sender_ip in arp_table and arp_table[sender_ip] != sender_mac:
                entry = {
                    "src_ip": sender_ip,
                    "dst_ip": pkt[ARP].pdst,
                    "proto": "ARP",
                    "reason": (
                        f"ARP spoofing: IP {sender_ip} changed MAC "
                        f"from {arp_table[sender_ip]} to {sender_mac}"
                    ),
                    "timestamp": ts,
                }
                anomalous.append(entry)
                if callback: callback(f"[!] ARP SPOOF DETECTED: {entry['reason']}")
            arp_table[sender_ip] = sender_mac

        # --- Port Scan Detection (TCP SYN-only packets) ---
        # A single source hitting PORT_SCAN_THRESHOLD unique destination ports with bare SYN packets
        # is characteristic of a port scanner (nmap -sS style).
        if pkt.haslayer(IP) and pkt.haslayer(TCP):
            tcp_layer = pkt[TCP]
            ip_layer = pkt[IP]
            if tcp_layer.flags == 0x02:  # SYN only
                src = ip_layer.src
                syn_tracker[src].add(tcp_layer.dport)
                if len(syn_tracker[src]) >= PORT_SCAN_THRESHOLD:
                    entry = {
                        "src_ip": src,
                        "dst_ip": ip_layer.dst,
                        "proto": "TCP",
                        "reason": (
                            f"Port scan: {src} sent SYN to {PORT_SCAN_THRESHOLD} unique ports"
                        ),
                        "timestamp": ts,
                    }
                    anomalous.append(entry)
                    if callback: callback(f"[!] PORT SCAN DETECTED from {src} ({PORT_SCAN_THRESHOLD}+ ports targeted)")

        # --- ICMP Flood Detection ---
        if pkt.haslayer(IP) and pkt.haslayer(ICMP):
            src = pkt[IP].src
            icmp_counter[src] += 1
            if icmp_counter[src] >= ICMP_FLOOD_THRESHOLD:
                entry = {
                    "src_ip": src,
                    "dst_ip": pkt[IP].dst,
                    "proto": "ICMP",
                    "reason": f"ICMP flood: {src} sent {ICMP_FLOOD_THRESHOLD}+ ICMP packets",
                    "timestamp": ts,
                }
                anomalous.append(entry)
                if callback: callback(f"[!] ICMP FLOOD DETECTED from {src}")

    # --- Run Capture ---
    try:
        if callback: callback(f"[*] Sniff started. Monitoring {interface} for {duration}s...")
        sniff(iface=interface, timeout=duration, prn=packet_handler, store=False)
    except PermissionError:
        msg = "Permission denied. Passive capture requires root privileges (run with sudo)."
        logger.error(msg)
        if callback: callback(f"[!] FATAL: {msg}")
        return create_result(module_name, "error", errors=[msg])
    except OSError as e:
        msg = f"Interface error on '{interface}': {e}"
        logger.error(msg)
        if callback: callback(f"[!] FATAL: {msg}")
        return create_result(module_name, "error", errors=[msg])
    except Exception as e:
        msg = f"Packet capture failed: {e}"
        logger.error(msg)
        if callback: callback(f"[!] FATAL: {msg}")
        return create_result(module_name, "error", errors=[msg])

    # --- Summarize ---
    total = packet_count[0]
    found = len(anomalous)
    scanners = [ip for ip, ports in syn_tracker.items() if len(ports) >= PORT_SCAN_THRESHOLD]

    if callback: callback(f"\n[+] Capture complete. Analyzed {total} packets over {duration}s.")
    if found:
        if callback: callback(f"[!] {found} anomaly event(s) detected:")
        for a in anomalous:
            if callback: callback(f"    [{a['proto']}] {a['reason']}")
    else:
        if callback: callback(f"[+] No anomalies detected. Network traffic appears normal.")

    logger.info(f"{module_name} complete. {total} packets, {found} anomalies.")

    return create_result(
        module_name=module_name,
        status="success",
        data={
            "total_packets_captured": total,
            "anomalous_packets": anomalous,
            "interface": interface,
            "duration_seconds": duration,
            "scanners_detected": scanners,
            "arp_table_snapshot": arp_table,
        },
    )
