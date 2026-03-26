import os
import sys
import time
import threading
from collections import Counter, defaultdict
from datetime import datetime

try:
    from scapy.all import sniff, DNSQR, UDP
except ImportError:
    print("[!] Scapy is required. Install with: pip install scapy")
    sys.exit(1)

LOG_FILE = os.path.join(os.path.dirname(__file__), "dns_queries.log")
SUSPICIOUS_TLDS = {".xyz", ".top", ".gq", ".tk", ".ml", ".cf"}

# Heuristic: domain is suspicious if it's very long, looks random, or has uncommon TLD

def is_suspicious(domain):
    if len(domain) > 50:
        return True
    tld = "." + domain.split(".")[-1]
    if tld in SUSPICIOUS_TLDS:
        return True
    # Random-looking: many digits or alternating consonant/vowel
    digit_ratio = sum(c.isdigit() for c in domain) / len(domain)
    if digit_ratio > 0.4:
        return True
    # Looks random: long runs of consonants
    import re
    if re.search(r"[bcdfghjklmnpqrstvwxyz]{6,}", domain, re.I):
        return True
    return False

class DNSMonitor:
    def __init__(self, iface=None, callback=None):
        self.iface = iface
        self.stats = defaultdict(int)
        self.domain_counter = Counter()
        self.suspicious_count = 0
        self.total_count = 0
        self.running = True
        self.lock = threading.Lock()
        self.callback = callback

    def log_query(self, domain, qtype, ts, suspicious):
        with open(LOG_FILE, "a") as f:
            f.write(f"{ts} | {domain} | {qtype} | {'SUSPICIOUS' if suspicious else 'OK'}\n")

    def print_query(self, domain, qtype, ts, suspicious):
        msg = f"{ts} | {domain} | {qtype} {'[SUSPICIOUS]' if suspicious else '[OK]'}"
        if self.callback:
            self.callback(msg)
        else:
            color = "\033[91m" if suspicious else "\033[92m"
            reset = "\033[0m"
            print(f"{color}{msg}{reset}")

    def process_packet(self, pkt):
        if pkt.haslayer(DNSQR) and pkt.haslayer(UDP) and pkt[UDP].dport == 53:
            domain = pkt[DNSQR].qname.decode(errors="ignore").rstrip('.')
            qtype = pkt[DNSQR].qtype
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            suspicious = is_suspicious(domain)
            with self.lock:
                self.total_count += 1
                self.domain_counter[domain] += 1
                if suspicious:
                    self.suspicious_count += 1
            self.log_query(domain, qtype, ts, suspicious)
            self.print_query(domain, qtype, ts, suspicious)

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
        if os.geteuid() != 0:
            msg = "[!] Root privileges required to sniff packets. Exiting."
            if self.callback:
                self.callback(msg)
            else:
                print(msg)
            sys.exit(1)
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
