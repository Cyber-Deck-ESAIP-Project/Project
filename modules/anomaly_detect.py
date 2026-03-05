# pyre-ignore-all-errors
import os
import sys
import json
from typing import List, Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger  # type: ignore
from utils.result_handler import create_result  # type: ignore

logger = get_logger()

try:
    import google.generativeai as genai  # type: ignore
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. AI narrative disabled. Run: pip install google-generativeai")

HISTORY_FILE = "logs/history.json"
HISTORY_LOOKBACK = 20  # analyze last N operations


def _load_recent_history(n: int) -> List[Dict[str, Any]]:
    """Load the last N records from history.json."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        return history[-n:] if len(history) > n else history
    except Exception as e:
        logger.warning(f"Could not load history: {e}")
        return []


def _run_heuristics(history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Apply deterministic rules to recent history.
    Returns a deduplicated list of anomaly flag dicts: {severity, rule, detail}.
    """
    flags: List[Dict[str, str]] = []
    seen_rules: set = set()

    def add_flag(severity: str, rule: str, detail: str):
        if rule not in seen_rules:
            seen_rules.add(rule)
            flags.append({"severity": severity, "rule": rule, "detail": detail})

    total = len(history)
    if total == 0:
        return flags

    errors = [r for r in history if r.get("raw_data", {}).get("status") == "error"]

    # Rule 1: High module error rate
    if len(errors) / total > 0.5:
        add_flag(
            "HIGH",
            "HIGH_ERROR_RATE",
            f"{len(errors)}/{total} recent operations failed — possible misconfiguration or hardware fault.",
        )

    for record in history:
        module = record.get("module", "")
        data = record.get("raw_data", {}).get("data", {})
        ts = record.get("timestamp", "unknown time")

        # Rule 2: ARP spoofing from passive monitor
        if module in ("passive_monitor", "Passive Monitor"):
            arp_events = [
                p for p in data.get("anomalous_packets", [])
                if p.get("proto") == "ARP"
            ]
            if arp_events:
                add_flag(
                    "CRITICAL",
                    "ARP_SPOOFING_DETECTED",
                    f"{len(arp_events)} ARP spoofing event(s) captured at {ts}. Possible MITM attack in progress.",
                )

        # Rule 3: Port scan activity from passive monitor
        if module in ("passive_monitor", "Passive Monitor"):
            scanners = data.get("scanners_detected", [])
            if scanners:
                add_flag(
                    "HIGH",
                    "PORT_SCAN_ACTIVITY",
                    f"Port scan activity from {len(scanners)} source(s): {', '.join(scanners)}.",
                )

        # Rule 4: ICMP flood from passive monitor
        if module in ("passive_monitor", "Passive Monitor"):
            icmp_events = [
                p for p in data.get("anomalous_packets", [])
                if p.get("proto") == "ICMP"
            ]
            if icmp_events:
                add_flag(
                    "MEDIUM",
                    "ICMP_FLOOD_DETECTED",
                    f"ICMP flood detected from {len(icmp_events)} source(s) at {ts}.",
                )

        # Rule 5: Weak WiFi networks found
        if module in ("wifi_audit", "WiFi Audit"):
            scan_results = data.get("scan_results", [])
            weak = [
                n for n in scan_results
                if "WEAK_CRYPTO" in n.get("flags", []) or "OPEN_NETWORK" in n.get("flags", [])
            ]
            if weak:
                ssids = [n.get("ssid", "?") for n in weak[:5]]
                add_flag(
                    "MEDIUM",
                    "WEAK_WIFI_NETWORKS",
                    f"{len(weak)} open/weak-crypto network(s) in range: {', '.join(ssids)}.",
                )

        # Rule 6: Unusually large LAN footprint
        if module in ("lan_scan", "LAN Scan", "LAN Scanning"):
            hosts_up = data.get("hosts_up", 0)
            if hosts_up >= 20:
                add_flag(
                    "MEDIUM",
                    "LARGE_LAN_FOOTPRINT",
                    f"LAN scan at {ts} found {hosts_up} live hosts — unusually large network footprint.",
                )

            # Rule 7: High-risk ports open on LAN hosts
            scan_results = data.get("scan_results", {})
            HIGH_RISK_PORTS = {21, 23, 445, 3389, 5900}
            risky_hosts = []
            for ip, host_data in scan_results.items():
                open_ports = {p["port"] for p in host_data.get("ports", [])}
                hits = open_ports & HIGH_RISK_PORTS
                if hits:
                    risky_hosts.append(f"{ip}:{sorted(hits)}")
            if risky_hosts:
                add_flag(
                    "HIGH",
                    "HIGH_RISK_PORTS_OPEN",
                    f"High-risk ports (FTP/Telnet/SMB/RDP/VNC) open on: {', '.join(risky_hosts[:5])}.",
                )

    return flags


def _build_gemini_prompt(history: List[Dict[str, Any]], flags: List[Dict[str, str]]) -> str:
    """Build a concise prompt for Gemini from the scan telemetry and heuristic flags."""
    ops_lines = []
    for r in history:
        module = r.get("module", "unknown")
        status = r.get("raw_data", {}).get("status", "unknown")
        targets = r.get("targets", 0)
        ops_lines.append(f"  - {module}: status={status}, entities={targets}")

    flags_lines = (
        "\n".join(f"  [{f['severity']}] {f['rule']}: {f['detail']}" for f in flags)
        or "  None detected."
    )

    ops_text = "\n".join(ops_lines) or "  No operations recorded."

    return (
        "You are a network security analyst reviewing field reconnaissance telemetry.\n\n"
        f"Recent operations ({len(history)} total):\n{ops_text}\n\n"
        f"Heuristic anomaly flags:\n{flags_lines}\n\n"
        "Provide a concise (3-5 sentence) threat assessment and specific recommended "
        "operator actions based on this data. Be direct and technical."
    )


def run(config: dict, callback=None, **kwargs) -> dict:
    module_name = "anomaly_detect"
    logger.info(f"Running {module_name} module...")

    if callback: callback("[*] Initializing Anomaly Detection Engine...")
    if callback: callback(f"[*] Loading last {HISTORY_LOOKBACK} operations from session history...")

    history = _load_recent_history(HISTORY_LOOKBACK)

    if not history:
        msg = "No session history found. Run other modules first to build a baseline."
        if callback: callback(f"[!] {msg}")
        return create_result(
            module_name,
            "partial",
            data={
                "operations_analyzed": 0,
                "anomaly_flags": [],
                "risk_assessment": "No history data available for analysis.",
            },
        )

    if callback: callback(f"[+] Loaded {len(history)} record(s). Running heuristic rule engine...")

    # --- Heuristic pass ---
    flags = _run_heuristics(history)

    if flags:
        if callback: callback(f"\n[!] {len(flags)} anomaly flag(s) raised:")
        for f in flags:
            if callback: callback(f"    [{f['severity']}] {f['rule']}: {f['detail']}")
    else:
        if callback: callback("[+] Heuristic pass clean. No anomalies in recent telemetry.")

    # --- Gemini AI narrative ---
    narrative = "AI analysis unavailable."

    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or config.get("system", {}).get("gemini_api_key")
        or config.get("api_keys", {}).get("google_gemini_key")
    )

    if GEMINI_AVAILABLE and api_key:
        if callback: callback("\n[*] Querying Gemini AI for threat narrative...")
        try:
            genai.configure(api_key=api_key)  # type: ignore
            model = genai.GenerativeModel("gemini-pro")  # type: ignore
            prompt = _build_gemini_prompt(history, flags)
            response = model.generate_content(prompt)  # type: ignore
            narrative = response.text
            if callback: callback(f"[+] AI Threat Assessment:\n{narrative}")
        except Exception as e:
            narrative = f"AI query failed: {e}"
            logger.warning(f"Gemini query failed: {e}")
            if callback: callback(f"[!] Gemini query failed: {e}")
    elif not GEMINI_AVAILABLE:
        if callback: callback("[!] google-generativeai not installed. Skipping AI narrative.")
    else:
        if callback: callback("[!] No Gemini API key in config. Skipping AI narrative.")

    if callback: callback("\n[+] Anomaly detection cycle complete.")
    logger.info(f"{module_name} complete. {len(flags)} flag(s) raised.")

    return create_result(
        module_name=module_name,
        status="success",
        data={
            "operations_analyzed": len(history),
            "anomaly_flags": flags,
            "risk_assessment": narrative,
        },
    )
