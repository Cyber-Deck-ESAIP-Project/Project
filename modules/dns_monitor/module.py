"""
Entry point for Cyber Deck integration.
Provides a run() function for menu-based or CLI invocation.
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.result_handler import create_result  # type: ignore
from .monitor import main

def run(config=None, target=None, callback=None, **kwargs):
    """
    Entry point for CyberDeck integration. Accepts config, target, and callback for web UI compatibility.
    """
    import threading
    import time
    from .monitor import DNSMonitor

    def web_log(msg):
        if callback:
            callback(msg)
        else:
            print(msg)

    try:
        mod_config = config.get('modules', {}).get('dns_monitor', {}) if config and isinstance(config, dict) else {}
        iface = mod_config.get('interface')
        duration = mod_config.get('duration', 30)
        monitor = DNSMonitor(iface=iface, callback=callback)

        # Run monitor in a thread so web UI doesn't block
        t = threading.Thread(target=monitor.start, daemon=True)
        t.start()
        web_log(f'[DNS Query Monitor] Started. Monitoring {iface or "default"} for {duration}s...')
        time.sleep(duration)
        monitor.running = False
        t.join(timeout=duration + 5)
        # After scan, always send stats to dashboard
        with monitor.lock:
            top_domains = monitor.domain_counter.most_common(3)
            stats_msg = [
                "--- DNS Query Stats ---",
                f"Total queries: {monitor.total_count}",
                f"Suspicious: {monitor.suspicious_count}",
                "Top domains:",
            ]
            for dom, cnt in top_domains:
                stats_msg.append(f"  {dom}: {cnt}")
            stats_msg.append("----------------------\n")
            msg = "\n".join(stats_msg)
            web_log(msg)
        web_log('[DNS Query Monitor] Stopped.')
        return create_result("dns_monitor", "success", data={
            "total_queries": monitor.total_count,
            "suspicious_count": monitor.suspicious_count,
            "top_domains": [{"domain": d, "count": c} for d, c in top_domains],
        })
    except KeyboardInterrupt:
        web_log("\n[!] DNS Monitor stopped by user.")
        return create_result("dns_monitor", "success", data={"total_queries": 0, "suspicious_count": 0, "top_domains": []})
    except Exception as e:
        web_log(f"[DNS Query Monitor Error]: {e}")
        return create_result("dns_monitor", "error", errors=[str(e)])
