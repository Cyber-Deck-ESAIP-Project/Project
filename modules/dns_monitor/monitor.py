import os
import sys
import time
import threading
from collections import Counter, defaultdict
from datetime import datetime

try:
    from scapy.all import sniff, DNSQR, UDP, IP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

import re

LOG_FILE = os.path.join(os.path.dirname(__file__), "dns_queries.log")
SUSPICIOUS_TLDS = {".xyz", ".top", ".gq", ".tk", ".ml", ".cf", ".cc", ".pw", ".ws", ".work", ".download", ".club"}
_CONSONANT_RE = re.compile(r"[bcdfghjklmnpqrstvwxyz]{6,}", re.I)

DNS_QTYPE_NAMES = {
    1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR",
    15: "MX", 16: "TXT", 28: "AAAA", 33: "SRV", 255: "ANY",
}

# Heuristic: domain is suspicious if it's very long, looks random, or has uncommon TLD

def is_suspicious(domain):
    if not domain:
        return False
    if len(domain) > 50:
        return True
    tld = "." + domain.split(".")[-1]
    if tld in SUSPICIOUS_TLDS:
        return True
    digit_ratio = sum(c.isdigit() for c in domain) / len(domain)
    if digit_ratio > 0.4:
        return True
    if _CONSONANT_RE.search(domain):
        return True
    return False

class DNSMonitor:
    def __init__(self, iface=None, callback=None):
        self.iface = iface
        self.stats = defaultdict(int)
        self.domain_counter = Counter()
        self.suspicious_domains = Counter()
        self.suspicious_count = 0
        self.total_count = 0
        self.running = True
        self.lock = threading.Lock()
        self.callback = callback

    def log_query(self, src_ip, domain, qtype, ts, suspicious):
        with open(LOG_FILE, "a") as f:
            f.write(f"{ts} | {src_ip} | {domain} | {qtype} | {'SUSPICIOUS' if suspicious else 'OK'}\n")

    def print_query(self, src_ip, domain, qtype, ts, suspicious):
        msg = f"{ts} | {src_ip} | {domain} | {qtype} {'[SUSPICIOUS]' if suspicious else '[OK]'}"
        try:
            if self.callback:
                self.callback(msg)
            else:
                color = "\033[91m" if suspicious else "\033[92m"
                reset = "\033[0m"
                print(f"{color}{msg}{reset}")
        except Exception:
            pass

    def process_packet(self, pkt):
        if pkt.haslayer(DNSQR) and pkt.haslayer(UDP) and pkt[UDP].dport == 53:
            domain = pkt[DNSQR].qname.decode(errors="ignore").rstrip('.').lower()
            qtype = DNS_QTYPE_NAMES.get(pkt[DNSQR].qtype, str(pkt[DNSQR].qtype))
            src_ip = pkt[IP].src if pkt.haslayer(IP) else "unknown"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            suspicious = is_suspicious(domain)
            with self.lock:
                self.total_count += 1
                self.domain_counter[domain] += 1
                self.stats[qtype] += 1
                if suspicious:
                    self.suspicious_count += 1
                    self.suspicious_domains[domain] += 1
            self.log_query(src_ip, domain, qtype, ts, suspicious)
            self.print_query(src_ip, domain, qtype, ts, suspicious)

    def stats_loop(self):
        while self.running:
            time.sleep(10)
            with self.lock:
                top_domains = self.domain_counter.most_common(3)
                stats_msg = [
                    "--- DNS Query Stats ---",
                    f"Total queries: {self.total_count}",
                    f"Suspicious: {self.suspicious_count}",
                    "Top domains:",
                ]
                for dom, cnt in top_domains:
                    stats_msg.append(f"  {dom}: {cnt}")
                stats_msg.append("----------------------\n")
                msg = "\n".join(stats_msg)
                if self.callback:
                    self.callback(msg)
                else:
                    print(msg)

    def start(self):
        if not SCAPY_AVAILABLE:
            msg = "[!] Scapy not installed. Run: pip install scapy"
            if self.callback:
                self.callback(msg)
            else:
                print(msg)
            self.running = False
            return
        if os.geteuid() != 0:
            msg = "[!] Root privileges required to sniff packets. Run with sudo."
            if self.callback:
                self.callback(msg)
            else:
                print(msg)
            self.running = False
            return
        start_msg = "[*] Starting Real-Time DNS Query Monitor..."
        log_msg = f"[*] Logging to: {LOG_FILE}"
        if self.callback:
            self.callback(start_msg)
            self.callback(log_msg)
        else:
            print(start_msg)
            print(log_msg)
        stats_thread = threading.Thread(target=self.stats_loop, daemon=True)
        stats_thread.start()
        try:
            sniff(filter="udp port 53", prn=self.process_packet, iface=self.iface, store=0, stop_filter=lambda x: not self.running)
        except KeyboardInterrupt:
            msg = "\n[!] Stopping monitor..."
            if self.callback:
                self.callback(msg)
            else:
                print(msg)
            self.running = False
        except Exception as e:
            msg = f"[!] Error: {e}"
            if self.callback:
                self.callback(msg)
            else:
                print(msg)
            self.running = False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Real-Time DNS Query Monitor")
    parser.add_argument("-i", "--iface", help="Network interface to sniff on (default: all)")
    args = parser.parse_args()
    monitor = DNSMonitor(iface=args.iface)
    monitor.start()

if __name__ == "__main__":
    main()
