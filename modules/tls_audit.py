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

DEFAULT_PORTS = [443, 8443]
CONNECT_TIMEOUT = 5  # seconds per host


def _audit_host(host: str, port: int) -> Dict[str, Any]:
    """Probe a single host on the given port and return a structured audit record."""
    result: Dict[str, Any] = {
        "host": host,
        "port": port,
        "reachable": False,
        "tls_version": None,
        "cipher_suite": None,
        "cipher_bits": None,
        "cert_subject": None,
        "cert_issuer": None,
        "cert_expiry": None,
        "days_until_expiry": None,
        "sans": [],
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

        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls_sock:
                result["reachable"] = True
                result["tls_version"] = tls_sock.version()
                cipher_info = tls_sock.cipher()   # (name, protocol, bits) or None
                if cipher_info:
                    result["cipher_suite"] = cipher_info[0]
                    result["cipher_bits"] = cipher_info[2]
                cert = tls_sock.getpeercert()

                if cert:
                    subject = dict(x[0] for x in cert.get("subject", []))
                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    result["cert_subject"] = subject.get("commonName", str(subject))
                    result["cert_issuer"] = issuer.get("commonName", str(issuer))
                    result["sans"] = [
                        value for rtype, value in cert.get("subjectAltName", [])
                        if rtype in ("DNS", "IP Address")
                    ]

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
                            (host, port), timeout=CONNECT_TIMEOUT
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

                # Flag weak cipher suites
                _weak_markers = ("RC4", "NULL", "EXPORT", "DES", "anon", "ADH", "AECDH")
                if result["cipher_suite"] and any(
                    m in result["cipher_suite"] for m in _weak_markers
                ):
                    result["vulnerabilities"].append("WEAK_CIPHER")

    except (socket.timeout, ConnectionRefusedError, OSError):
        pass  # host not reachable on this port — reachable stays False
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
    # Ignore localhost/loopback — meaningless for TLS audit
    _invalid = {"127.0.0.1", "localhost", ""}
    raw_target = kwargs.get("target", "").strip()
    if raw_target in _invalid:
        raw_target = mod_config.get("default_target", "").strip()
    if raw_target in _invalid:
        msg = "No valid target specified. Enter an IP or hostname in the TARGET_HOST field (not 127.0.0.1)."
        if callback: callback(f"[-] {msg}")
        return create_result(module_name, "error", errors=[msg])
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

    ports: List[int] = mod_config.get("ports", DEFAULT_PORTS)
    if callback: callback(f"[*] TLS Audit starting. {len(targets)} host(s) x {len(ports)} port(s)...")

    tls_results: List[Dict[str, Any]] = []
    vulnerabilities_found = 0

    for host in targets:
        for port in ports:
            if callback: callback(f"[*] Probing {host}:{port}...")
            audit = _audit_host(host, port)
            tls_results.append(audit)

            if not audit["reachable"]:
                if callback: callback(f"    [ ] {host}:{port} -- not reachable")
                continue

            vulns = audit["vulnerabilities"]
            cipher_label = (
                f"{audit['cipher_suite']}/{audit['cipher_bits']}b"
                if audit.get("cipher_suite") else "?"
            )
            if vulns:
                vulnerabilities_found += len(vulns)
                if callback:
                    callback(
                        f"    [!] {host}:{audit['port']} -- TLS:{audit['tls_version']} | "
                        f"Cipher:{cipher_label} | "
                        f"Expiry:{audit.get('cert_expiry', 'N/A')} | "
                        f"VULNS: {', '.join(vulns)}"
                    )
            else:
                if callback:
                    callback(
                        f"    [+] {host}:{audit['port']} -- TLS:{audit['tls_version']} | "
                        f"Cipher:{cipher_label} | "
                        f"Expiry:{audit.get('cert_expiry', 'N/A')} | OK"
                    )

    probes_total = len(tls_results)
    probes_reachable = sum(1 for r in tls_results if r["reachable"])

    if callback:
        callback(
            f"\n[+] TLS Audit complete. "
            f"{probes_reachable}/{probes_total} probe(s) reachable "
            f"({len(targets)} host(s) x {len(ports)} port(s))."
        )
    if vulnerabilities_found:
        if callback: callback(f"[!] {vulnerabilities_found} TLS vulnerability/issue(s) found.")
    else:
        if callback: callback(f"[+] No TLS issues found.")

    logger.info(
        f"{module_name} complete. "
        f"{probes_total} probe(s) across {len(targets)} host(s), "
        f"{vulnerabilities_found} issue(s)."
    )

    return create_result(
        module_name=module_name,
        status="success",
        data={
            "hosts_audited": len(targets),
            "ports_scanned": ports,
            "probes_total": probes_total,
            "probes_reachable": probes_reachable,
            "vulnerabilities_found": vulnerabilities_found,
            "tls_results": tls_results,
        },
    )
