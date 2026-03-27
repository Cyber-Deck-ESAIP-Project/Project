# pyre-ignore-all-errors
import os
import sys
import json
import time
import urllib.request
import urllib.parse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger        # type: ignore
from utils.result_handler import create_result  # type: ignore

logger = get_logger()

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
RATE_LIMIT_DELAY = 6   # seconds between requests (5 req/30 sec unauthenticated limit)
MAX_RESULTS_PER_QUERY = 5
MAX_SERVICES = 15      # cap unique services to keep runtime reasonable


def _query_nvd(product: str, version: str, callback=None) -> list:
    """Query NVD CVE API for a product+version string. Returns list of CVE dicts."""
    query = f"{product} {version}".strip() if version else product
    params = urllib.parse.urlencode({
        "keywordSearch": query,
        "resultsPerPage": MAX_RESULTS_PER_QUERY,
    })
    url = f"{NVD_API_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CyberDeck-CVE-Matcher/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
    except Exception as e:
        if callback:
            callback(f"    [!] NVD API error for '{query}': {e}")
        return []

    results = []
    for vuln in raw.get("vulnerabilities", []):
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "")

        desc = next(
            (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
            "No description available",
        )

        # Prefer CVSSv3.1, fallback to v3.0, then v2
        score = 0.0
        severity = "UNKNOWN"
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric_list = cve.get("metrics", {}).get(key, [])
            if metric_list:
                m = metric_list[0].get("cvssData", {})
                score = float(m.get("baseScore", 0.0))
                severity = str(m.get("baseSeverity", "UNKNOWN")).upper()
                break

        results.append({
            "cve_id": cve_id,
            "cvss_score": score,
            "severity": severity,
            "description": desc[:220] + ("..." if len(desc) > 220 else ""),
        })

    return sorted(results, key=lambda x: x["cvss_score"], reverse=True)


def run(config: dict, callback=None, **kwargs) -> dict:
    module_name = "cve_matcher"
    logger.info(f"Running {module_name}...")

    mod_config = config.get("modules", {}).get(module_name, {})
    if not mod_config.get("enabled", False):
        if callback:
            callback(f"[-] Module {module_name} disabled.")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    if callback:
        callback("[*] CVE Vulnerability Matcher starting...")
        callback("[*] Reading latest LAN Scan results from history...")

    # Locate history.json
    logs_dir = config.get("system", {}).get("logs_dir", "logs")
    history_path = os.path.join(PROJECT_ROOT, logs_dir, "history.json")

    lan_data = None
    if os.path.exists(history_path):
        try:
            with open(history_path, "r") as f:
                history = json.load(f)
            for entry in reversed(history):
                if entry.get("module") == "LAN Scanning":
                    lan_data = entry.get("raw_data", {}).get("data", {})
                    break
        except Exception as e:
            logger.error(f"Failed to read history.json: {e}")

    if not lan_data:
        msg = "No LAN Scan data found. Run 'LAN Scanning' module first."
        if callback:
            callback(f"[-] {msg}")
        return create_result(module_name, "error", errors=[msg])

    # Extract unique services that have product/version info
    scan_results = lan_data.get("scan_results", {})
    services = []
    seen: set = set()

    for ip, host_data in scan_results.items():
        for port in host_data.get("ports", []):
            product = port.get("product", "").strip()
            version = port.get("version", "").strip()
            if not product:
                continue
            key = f"{product}|{version}"
            if key in seen:
                continue
            seen.add(key)
            services.append({
                "ip": ip,
                "port": port.get("port"),
                "service": port.get("name", ""),
                "product": product,
                "version": version,
            })

    if not services:
        msg = "No services with version info in LAN Scan results. Re-run LAN Scanning first."
        if callback:
            callback(f"[-] {msg}")
        return create_result(
            module_name, "partial",
            data={"services_scanned": 0, "cves_found": 0, "vulnerabilities": [], "severity_summary": {}},
            errors=[msg],
        )

    if len(services) > MAX_SERVICES:
        if callback:
            callback(f"[*] Capping to {MAX_SERVICES} unique services to respect API rate limits.")
        services = services[:MAX_SERVICES]

    estimated = len(services) * RATE_LIMIT_DELAY
    if callback:
        callback(f"[*] {len(services)} unique services to check (~{estimated}s due to NVD rate limits).")
        callback("[*] Querying NVD CVE database...")

    vulnerabilities = []

    for i, svc in enumerate(services):
        label = f"{svc['product']} {svc['version']}".strip()
        if callback:
            callback(f"[>] [{i + 1}/{len(services)}] {label} on {svc['ip']}:{svc['port']}")

        cves = _query_nvd(svc["product"], svc["version"], callback)

        for cve in cves:
            vulnerabilities.append({**svc, **cve})

        if callback:
            found = len(cves)
            callback(f"    [{'!' if found else '+'}] {found} CVE(s) found")

        if i < len(services) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    # Sort by CVSS score descending
    vulnerabilities.sort(key=lambda x: x.get("cvss_score", 0), reverse=True)

    severity_summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for v in vulnerabilities:
        sev = v.get("severity", "UNKNOWN")
        if sev not in severity_summary:
            sev = "UNKNOWN"
        severity_summary[sev] += 1

    total = len(vulnerabilities)

    if callback:
        callback(f"\n[+] CVE Matching complete.")
        callback(f"    Services checked : {len(services)}")
        callback(f"    Total CVEs found : {total}")
        if total:
            callback(
                f"    Critical: {severity_summary['CRITICAL']}  "
                f"High: {severity_summary['HIGH']}  "
                f"Medium: {severity_summary['MEDIUM']}  "
                f"Low: {severity_summary['LOW']}"
            )

    return create_result(module_name, "success", data={
        "services_scanned": len(services),
        "cves_found": total,
        "vulnerabilities": vulnerabilities,
        "severity_summary": severity_summary,
    })
