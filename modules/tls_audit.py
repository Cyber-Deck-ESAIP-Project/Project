# pyre-ignore-all-errors
import os
import sys
import ssl
import socket
import ipaddress
from datetime import datetime, timezone
from typing import List, Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger  # type: ignore
from utils.result_handler import create_result  # type: ignore

logger = get_logger()

TLS_PORT = 443
CONNECT_TIMEOUT = 5  # seconds per host


def _audit_host(host: str) -> Dict[str, Any]:
    """Probe a single host on TLS_PORT and return a structured audit record."""
    result: Dict[str, Any] = {
        "host": host,
        "port": TLS_PORT,
        "reachable": False,
        "tls_version": None,
        "cert_subject": None,
        "cert_issuer": None,
        "cert_expiry": None,
        "days_until_expiry": None,
        "expired": False,
        "self_signed": False,
        "hostname_valid": False,
        "vulnerabilities": [],
    }

    try:
        # Use a permissive context first so we can retrieve cert data even for self-signed certs
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, TLS_PORT), timeout=CONNECT_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls_sock:
                result["reachable"] = True
                result["tls_version"] = tls_sock.version()
                cert = tls_sock.getpeercert()

                if cert:
                    subject = dict(x[0] for x in cert.get("subject", []))
                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    result["cert_subject"] = subject.get("commonName", str(subject))
                    result["cert_issuer"] = issuer.get("commonName", str(issuer))

                    expiry_str = cert.get("notAfter", "")
                    if expiry_str:
                        expiry_dt = datetime.strptime(
                            expiry_str, "%b %d %H:%M:%S %Y %Z"
                        ).replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        result["cert_expiry"] = expiry_dt.strftime("%Y-%m-%d")
                        result["days_until_expiry"] = (expiry_dt - now).days
                        if result["days_until_expiry"] < 0:
                            result["expired"] = True
                            result["vulnerabilities"].append("CERT_EXPIRED")
                        elif result["days_until_expiry"] < 30:
                            result["vulnerabilities"].append("CERT_EXPIRING_SOON")

                    # Self-signed: subject CN == issuer CN
                    if subject == issuer:
                        result["self_signed"] = True
                        result["vulnerabilities"].append("SELF_SIGNED_CERT")

                    # Strict hostname verification via a second connection with the default context
                    try:
                        strict_ctx = ssl.create_default_context()
                        with socket.create_connection(
                            (host, TLS_PORT), timeout=CONNECT_TIMEOUT
                        ) as s2:
                            with strict_ctx.wrap_socket(s2, server_hostname=host):
                                result["hostname_valid"] = True
                    except ssl.SSLCertVerificationError:
                        result["vulnerabilities"].append("HOSTNAME_MISMATCH")
                    except Exception:
                        pass  # network error, not a hostname problem

                # Flag deprecated TLS/SSL versions
                if result["tls_version"] in ("TLSv1", "TLSv1.1", "SSLv2", "SSLv3"):
                    result["vulnerabilities"].append(
                        f"WEAK_TLS_VERSION:{result['tls_version']}"
                    )

    except (socket.timeout, ConnectionRefusedError, OSError):
        pass  # host not reachable on 443 — reachable stays False
    except Exception as e:
        logger.debug(f"TLS audit error on {host}: {e}")

    return result


def run(config: dict, callback=None, **kwargs) -> dict:
    module_name = "tls_audit"
    logger.info(f"Running {module_name} module...")

    mod_config = config.get("modules", {}).get(module_name, {})
    if not mod_config.get("enabled", False):
        if callback: callback(f"[-] Module {module_name} disabled.")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    # Resolve target: GUI footer field takes priority, then config default
    raw_target = kwargs.get("target", "") or mod_config.get("default_target", "")
    targets: List[str] = []

    for part in raw_target.replace(",", " ").split():
        part = part.strip()
        if not part:
            continue
        try:
            network = ipaddress.ip_network(part, strict=False)
            if network.num_addresses > 256:
                if callback: callback(f"[!] Subnet {part} too large (>256 hosts). Skipping.")
                continue
            targets.extend(str(h) for h in network.hosts())
        except ValueError:
            targets.append(part)  # treat as hostname

    if not targets:
        msg = "No target specified. Enter an IP, hostname, or subnet in the TARGET_HOST field."
        if callback: callback(f"[-] {msg}")
        return create_result(module_name, "error", errors=[msg])

    if callback: callback(f"[*] TLS Audit starting. {len(targets)} host(s) to probe on port {TLS_PORT}...")

    tls_results: List[Dict[str, Any]] = []
    vulnerabilities_found = 0

    for host in targets:
        if callback: callback(f"[*] Probing {host}:{TLS_PORT}...")
        audit = _audit_host(host)
        tls_results.append(audit)

        if not audit["reachable"]:
            if callback: callback(f"    [ ] {host} -- port {TLS_PORT} not reachable")
            continue

        vulns = audit["vulnerabilities"]
        if vulns:
            vulnerabilities_found += len(vulns)
            if callback:
                callback(
                    f"    [!] {host} -- TLS:{audit['tls_version']} | "
                    f"Expiry:{audit.get('cert_expiry', 'N/A')} | "
                    f"VULNS: {', '.join(vulns)}"
                )
        else:
            if callback:
                callback(
                    f"    [+] {host} -- TLS:{audit['tls_version']} | "
                    f"Expiry:{audit.get('cert_expiry', 'N/A')} | OK"
                )

    hosts_reachable = sum(1 for r in tls_results if r["reachable"])

    if callback:
        callback(
            f"\n[+] TLS Audit complete. "
            f"{hosts_reachable}/{len(targets)} host(s) reachable on port {TLS_PORT}."
        )
    if vulnerabilities_found:
        if callback: callback(f"[!] {vulnerabilities_found} TLS vulnerability/issue(s) found.")
    else:
        if callback: callback(f"[+] No TLS issues found.")

    logger.info(f"{module_name} complete. {len(targets)} probed, {vulnerabilities_found} issues.")

    return create_result(
        module_name=module_name,
        status="success",
        data={
            "hosts_audited": len(targets),
            "hosts_reachable": hosts_reachable,
            "vulnerabilities_found": vulnerabilities_found,
            "tls_results": tls_results,
        },
    )
