import os
from datetime import datetime
from html import escape
from typing import Any, Dict, List


class ReportGenerator:
    """Utility class for generating formatted audit reports from scan telemetry."""

    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return "-"
        text = str(value).strip()
        return escape(text) if text else "-"

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _header_card(self, data: Dict[str, Any]) -> str:
        module  = self._clean_text(data.get("module", "Unknown"))
        status  = self._clean_text(data.get("status", "Unknown")).title()
        ts      = self._clean_text(data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        errors  = data.get("errors") or []
        err_count = len(errors) if isinstance(errors, list) else 0
        status_color = "var(--success)" if status.lower() == "success" else "var(--danger)"
        return f"""
        <section class="card">
            <div class="metric-grid">
                <div class="metric"><span class="label">Module</span><span class="value" style="font-size:1rem">{module}</span></div>
                <div class="metric"><span class="label">Status</span><span class="value" style="font-size:1rem;color:{status_color}">{status}</span></div>
                <div class="metric"><span class="label">Timestamp</span><span class="value" style="font-size:0.95rem">{ts}</span></div>
                <div class="metric"><span class="label">Errors</span><span class="value" style="color:{'var(--danger)' if err_count else 'var(--success)'}">{err_count}</span></div>
            </div>
        </section>
        """

    def _errors_card(self, data: Dict[str, Any]) -> str:
        errors = data.get("errors") or []
        if not isinstance(errors, list) or not errors:
            return ""
        rows = "".join(f"<tr><td>{self._clean_text(e)}</td></tr>" for e in errors)
        return f"""
        <section class="card" style="border-color:#f87171">
            <h2 style="color:#f87171">Errors</h2>
            <div class="table-wrap"><table><tbody>{rows}</tbody></table></div>
        </section>"""

    # ------------------------------------------------------------------
    # WiFi Audit
    # ------------------------------------------------------------------

    def _build_wifi_html(self, data: Dict[str, Any]) -> str:
        payload   = data.get("data", {})
        networks  = payload.get("scan_results", [])
        n_found   = self._safe_int(payload.get("networks_found", len(networks)))
        n_rogue   = self._safe_int(payload.get("rogue_aps_detected", 0))
        weak      = sum(1 for n in networks if isinstance(n, dict) and n.get("flags"))

        rows = []
        for ap in networks if isinstance(networks, list) else []:
            if not isinstance(ap, dict):
                continue
            flags = ap.get("flags", [])
            flags_str = " | ".join(flags) if flags else "OK"
            row_color = ""
            if "OPEN_NETWORK" in flags or "WEAK_CRYPTO" in flags:
                row_color = "style='color:#fbbf24'"
            rows.append(
                f"<tr {row_color}>"
                f"<td>{self._clean_text(ap.get('ssid', 'Hidden'))}</td>"
                f"<td><code>{self._clean_text(ap.get('bssid', '-'))}</code></td>"
                f"<td>{self._clean_text(ap.get('rssi', '-'))}</td>"
                f"<td>{self._clean_text(ap.get('crypto', '-'))}</td>"
                f"<td style='color:{\"#f87171\" if flags else \"#34d399\"}'>{self._clean_text(flags_str)}</td>"
                "</tr>"
            )
        table = "".join(rows) or "<tr><td colspan='5' class='muted'>No networks found.</td></tr>"

        return self._header_card(data) + f"""
        <section class="card">
            <h2>WiFi Scan Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Networks Found</span><span class="value">{n_found}</span></div>
                <div class="metric"><span class="label">Vulnerable / Open</span><span class="value" style="color:{'#f87171' if weak else '#34d399'}">{weak}</span></div>
                <div class="metric"><span class="label">Rogue APs</span><span class="value" style="color:{'#f87171' if n_rogue else '#34d399'}">{n_rogue}</span></div>
            </div>
        </section>
        <section class="card">
            <h2>Access Points</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>SSID</th><th>BSSID</th><th>Signal</th><th>Security</th><th>Flags</th></tr></thead>
                    <tbody>{table}</tbody>
                </table>
            </div>
        </section>
        """ + self._errors_card(data)

    # ------------------------------------------------------------------
    # LAN Scan
    # ------------------------------------------------------------------

    def _build_lan_html(self, data: Dict[str, Any]) -> str:
        payload      = data.get("data", {})
        hosts_up     = self._safe_int(payload.get("hosts_up", 0))
        scan_results = payload.get("scan_results", {})

        host_cards = []
        if isinstance(scan_results, dict):
            for ip, info in scan_results.items():
                if not isinstance(info, dict):
                    continue
                ports = info.get("ports", [])
                port_rows = "".join(
                    f"<tr>"
                    f"<td>{self._clean_text(p.get('port', '-'))}</td>"
                    f"<td>{self._clean_text(p.get('name', '-'))}</td>"
                    f"<td>{self._clean_text(p.get('product', '-'))} {self._clean_text(p.get('version', ''))}</td>"
                    f"<td style='color:#34d399'>open</td>"
                    f"</tr>"
                    for p in ports if isinstance(p, dict)
                ) or "<tr><td colspan='4' class='muted'>No open ports detected.</td></tr>"

                host_cards.append(f"""
                <section class="card" style="border-color:#1f3a5a">
                    <h2 style="font-size:1rem">
                        {self._clean_text(ip)}
                        <span style="font-size:0.85rem;color:var(--text-muted);margin-left:8px">
                            {self._clean_text(info.get('hostname',''))}
                        </span>
                    </h2>
                    <p class="meta-row">
                        MAC: <strong>{self._clean_text(info.get('mac','-'))}</strong>
                        &nbsp;|&nbsp; Vendor: <strong>{self._clean_text(info.get('vendor','-'))}</strong>
                    </p>
                    <div class="table-wrap">
                        <table style="min-width:400px">
                            <thead><tr><th>Port</th><th>Service</th><th>Version</th><th>State</th></tr></thead>
                            <tbody>{port_rows}</tbody>
                        </table>
                    </div>
                </section>""")

        if not host_cards:
            host_cards = ["<section class='card'><p class='muted'>No active hosts found.</p></section>"]

        return self._header_card(data) + f"""
        <section class="card">
            <h2>LAN Scan Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Hosts Up</span><span class="value">{hosts_up}</span></div>
            </div>
        </section>
        """ + "".join(host_cards) + self._errors_card(data)

    # ------------------------------------------------------------------
    # TLS Audit
    # ------------------------------------------------------------------

    def _build_tls_html(self, data: Dict[str, Any]) -> str:
        payload     = data.get("data", {})
        audited     = self._safe_int(payload.get("hosts_audited", 0))
        reachable   = self._safe_int(payload.get("hosts_reachable", 0))
        vuln_count  = self._safe_int(payload.get("vulnerabilities_found", 0))
        tls_results = payload.get("tls_results", [])

        rows = []
        for r in tls_results if isinstance(tls_results, list) else []:
            if not isinstance(r, dict):
                continue
            vulns = r.get("vulnerabilities", [])
            vulns_str = ", ".join(vulns) if vulns else "None"
            vuln_color = "#f87171" if vulns else "#34d399"
            days = r.get("days_until_expiry")
            days_str = str(days) if days is not None else "-"
            if isinstance(days, int) and days < 0:
                days_str = f"<span style='color:#f87171'>{days} (EXPIRED)</span>"
            elif isinstance(days, int) and days < 30:
                days_str = f"<span style='color:#fbbf24'>{days}</span>"
            reach_icon = "✓" if r.get("reachable") else "✗"
            reach_color = "#34d399" if r.get("reachable") else "#f87171"
            rows.append(
                f"<tr>"
                f"<td>{self._clean_text(r.get('host','-'))}</td>"
                f"<td style='color:{reach_color}'>{reach_icon}</td>"
                f"<td>{self._clean_text(r.get('tls_version','-'))}</td>"
                f"<td>{self._clean_text(r.get('cert_subject','-'))}</td>"
                f"<td>{self._clean_text(r.get('cert_expiry','-'))}</td>"
                f"<td>{days_str}</td>"
                f"<td style='color:{vuln_color}'>{self._clean_text(vulns_str)}</td>"
                "</tr>"
            )
        table = "".join(rows) or "<tr><td colspan='7' class='muted'>No hosts audited.</td></tr>"

        return self._header_card(data) + f"""
        <section class="card">
            <h2>TLS Audit Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Hosts Audited</span><span class="value">{audited}</span></div>
                <div class="metric"><span class="label">Reachable</span><span class="value">{reachable}</span></div>
                <div class="metric"><span class="label">Issues Found</span><span class="value" style="color:{'#f87171' if vuln_count else '#34d399'}">{vuln_count}</span></div>
            </div>
        </section>
        <section class="card">
            <h2>Certificate Details</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Host</th><th>Reachable</th><th>TLS Version</th><th>Subject CN</th><th>Expiry</th><th>Days Left</th><th>Vulnerabilities</th></tr></thead>
                    <tbody>{table}</tbody>
                </table>
            </div>
        </section>
        """ + self._errors_card(data)

    # ------------------------------------------------------------------
    # ARP Monitor
    # ------------------------------------------------------------------

    def _build_arp_html(self, data: Dict[str, Any]) -> str:
        payload    = data.get("data", {})
        duration   = self._safe_int(payload.get("monitored_seconds", 0))
        total_pkts = self._safe_int(payload.get("total_arp_packets", 0))
        unique     = self._safe_int(payload.get("unique_hosts", 0))
        arp_table  = payload.get("arp_table", {})
        conflicts  = payload.get("conflict_events", [])

        arp_rows = "".join(
            f"<tr><td><code>{self._clean_text(ip)}</code></td><td><code>{self._clean_text(mac)}</code></td></tr>"
            for ip, mac in sorted(arp_table.items()) if isinstance(arp_table, dict)
        ) or "<tr><td colspan='2' class='muted'>No ARP entries recorded.</td></tr>"

        conflict_rows = []
        for c in conflicts if isinstance(conflicts, list) else []:
            if not isinstance(c, dict):
                continue
            conflict_rows.append(
                f"<tr style='color:#f87171'>"
                f"<td>{self._clean_text(c.get('timestamp','-'))}</td>"
                f"<td><code>{self._clean_text(c.get('ip','-'))}</code></td>"
                f"<td><code>{self._clean_text(c.get('original_mac','-'))}</code></td>"
                f"<td><code>{self._clean_text(c.get('new_mac','-'))}</code></td>"
                f"<td>{self._clean_text(c.get('reason','-'))}</td>"
                "</tr>"
            )
        conflict_table = "".join(conflict_rows) or "<tr><td colspan='5' class='muted'>No conflicts detected.</td></tr>"

        return self._header_card(data) + f"""
        <section class="card">
            <h2>ARP Monitor Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Duration</span><span class="value">{duration}s</span></div>
                <div class="metric"><span class="label">ARP Packets</span><span class="value">{total_pkts}</span></div>
                <div class="metric"><span class="label">Unique Hosts</span><span class="value">{unique}</span></div>
                <div class="metric"><span class="label">Conflicts</span><span class="value" style="color:{'#f87171' if conflicts else '#34d399'}">{len(conflicts) if isinstance(conflicts,list) else 0}</span></div>
            </div>
        </section>
        <section class="card" style="{'border-color:#f87171' if conflicts else ''}">
            <h2 style="{'color:#f87171' if conflicts else ''}">MAC Conflict Events</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Time</th><th>IP</th><th>Original MAC</th><th>New MAC</th><th>Reason</th></tr></thead>
                    <tbody>{conflict_table}</tbody>
                </table>
            </div>
        </section>
        <section class="card">
            <h2>ARP Table Snapshot</h2>
            <div class="table-wrap">
                <table style="min-width:300px">
                    <thead><tr><th>IP Address</th><th>MAC Address</th></tr></thead>
                    <tbody>{arp_rows}</tbody>
                </table>
            </div>
        </section>
        """ + self._errors_card(data)

    # ------------------------------------------------------------------
    # Bluetooth Recon
    # ------------------------------------------------------------------

    def _build_bluetooth_html(self, data: Dict[str, Any]) -> str:
        payload  = data.get("data", {})
        devices  = payload.get("scan_results", [])
        n_found  = self._safe_int(payload.get("devices_found", len(devices) if isinstance(devices, list) else 0))

        rows = "".join(
            f"<tr>"
            f"<td><code>{self._clean_text(d.get('mac','-'))}</code></td>"
            f"<td>{self._clean_text(d.get('name','Unknown'))}</td>"
            f"<td>{self._clean_text(d.get('rssi','N/A'))}</td>"
            "</tr>"
            for d in (devices if isinstance(devices, list) else []) if isinstance(d, dict)
        ) or "<tr><td colspan='3' class='muted'>No Bluetooth devices discovered.</td></tr>"

        return self._header_card(data) + f"""
        <section class="card">
            <h2>Bluetooth Recon Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Devices Found</span><span class="value">{n_found}</span></div>
            </div>
        </section>
        <section class="card">
            <h2>Discovered Devices</h2>
            <div class="table-wrap">
                <table style="min-width:300px">
                    <thead><tr><th>MAC Address</th><th>Name</th><th>RSSI</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </section>
        """ + self._errors_card(data)

    # ------------------------------------------------------------------
    # Pentest Toolkit
    # ------------------------------------------------------------------

    def _build_pentest_html(self, data: Dict[str, Any]) -> str:
        payload    = data.get("data", {})
        target_ip  = self._clean_text(payload.get("target_ip", "-"))
        msf_ver    = self._clean_text(payload.get("msf_version", "-"))
        matches    = payload.get("matches", [])

        rank_color = {"excellent": "#34d399", "great": "#4fd1c5", "normal": "#fbbf24", "low": "#f87171"}

        rows = "".join(
            f"<tr>"
            f"<td>{self._clean_text(m.get('port','-'))}</td>"
            f"<td>{self._clean_text(m.get('service','-'))}</td>"
            f"<td><code style='font-size:0.82rem'>{self._clean_text(m.get('module','-'))}</code></td>"
            f"<td style='color:{rank_color.get(str(m.get(\"rank\",\"\")).lower(),\"#97a8be\")}'>{self._clean_text(m.get('rank','-')).title()}</td>"
            f"<td>{self._clean_text(m.get('description','-'))}</td>"
            "</tr>"
            for m in (matches if isinstance(matches, list) else []) if isinstance(m, dict)
        ) or "<tr><td colspan='5' class='muted'>No exploit matches found for this target.</td></tr>"

        return self._header_card(data) + f"""
        <section class="card">
            <h2>Pentest Toolkit Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Target IP</span><span class="value" style="font-size:1rem">{target_ip}</span></div>
                <div class="metric"><span class="label">MSF Version</span><span class="value" style="font-size:0.9rem">{msf_ver}</span></div>
                <div class="metric"><span class="label">Exploit Matches</span><span class="value" style="color:{'#f87171' if matches else '#34d399'}">{len(matches) if isinstance(matches,list) else 0}</span></div>
            </div>
        </section>
        <section class="card">
            <h2>Exploit Module Matches</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Port</th><th>Service</th><th>Module</th><th>Rank</th><th>Description</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </section>
        """ + self._errors_card(data)

    # ------------------------------------------------------------------
    # Anomaly Detection
    # ------------------------------------------------------------------

    def _build_anomaly_detect_html(self, data: Dict[str, Any]) -> str:
        payload = data.get("data", {})
        return self._header_card(data) + self._build_anomaly_html(payload)

    # ------------------------------------------------------------------
    # Passive Monitor
    # ------------------------------------------------------------------

    def _build_passive_html(self, data: Dict[str, Any]) -> str:
        payload     = data.get("data", {})
        total_pkts  = self._safe_int(payload.get("total_packets_captured", 0))
        anomalous   = payload.get("anomalous_packets", [])
        scanners    = payload.get("scanners_detected", [])
        arp_snap    = payload.get("arp_table_snapshot", {})

        anomaly_rows = "".join(
            f"<tr><td>{self._clean_text(p.get('timestamp','-'))}</td>"
            f"<td>{self._clean_text(p.get('protocol','-'))}</td>"
            f"<td><code>{self._clean_text(p.get('src','-'))}</code></td>"
            f"<td><code>{self._clean_text(p.get('dst','-'))}</code></td>"
            f"<td>{self._clean_text(p.get('reason','-'))}</td></tr>"
            for p in (anomalous if isinstance(anomalous, list) else []) if isinstance(p, dict)
        ) or "<tr><td colspan='5' class='muted'>No anomalous packets.</td></tr>"

        scanner_rows = "".join(
            f"<tr><td><code>{self._clean_text(s if isinstance(s, str) else s.get('ip','-'))}</code></td></tr>"
            for s in (scanners if isinstance(scanners, list) else [])
        ) or "<tr><td class='muted'>No port scanners detected.</td></tr>"

        arp_rows = "".join(
            f"<tr><td><code>{self._clean_text(ip)}</code></td><td><code>{self._clean_text(mac)}</code></td></tr>"
            for ip, mac in sorted(arp_snap.items()) if isinstance(arp_snap, dict)
        ) or "<tr><td colspan='2' class='muted'>No ARP entries.</td></tr>"

        return self._header_card(data) + f"""
        <section class="card">
            <h2>Passive Monitor Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Packets Captured</span><span class="value">{total_pkts}</span></div>
                <div class="metric"><span class="label">Anomalous Packets</span><span class="value" style="color:{'#f87171' if anomalous else '#34d399'}">{len(anomalous) if isinstance(anomalous,list) else 0}</span></div>
                <div class="metric"><span class="label">Scanners Detected</span><span class="value" style="color:{'#f87171' if scanners else '#34d399'}">{len(scanners) if isinstance(scanners,list) else 0}</span></div>
            </div>
        </section>
        <section class="card">
            <h2>Anomalous Packets</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Time</th><th>Protocol</th><th>Source</th><th>Destination</th><th>Reason</th></tr></thead>
                    <tbody>{anomaly_rows}</tbody>
                </table>
            </div>
        </section>
        <section class="card">
            <h2>Port Scanners Detected</h2>
            <div class="table-wrap">
                <table style="min-width:200px"><thead><tr><th>Source IP</th></tr></thead><tbody>{scanner_rows}</tbody></table>
            </div>
        </section>
        <section class="card">
            <h2>ARP Table Snapshot</h2>
            <div class="table-wrap">
                <table style="min-width:300px">
                    <thead><tr><th>IP Address</th><th>MAC Address</th></tr></thead>
                    <tbody>{arp_rows}</tbody>
                </table>
            </div>
        </section>
        """ + self._errors_card(data)

    # ------------------------------------------------------------------
    # Baseline comparison  (global dashboard)
    # ------------------------------------------------------------------

    def _build_baseline_comparison_html(self, baseline: Dict[str, Any]) -> str:
        if not isinstance(baseline, dict) or not baseline:
            return ""

        summary          = baseline.get("summary", {})
        new_entities     = baseline.get("new_entities", [])
        removed_entities = baseline.get("removed_entities", [])
        changed_modules  = baseline.get("changed_module_results", [])

        new_rows = "".join(
            f"<tr><td>{self._clean_text(i.get('module','-'))}</td><td>{self._safe_int(i.get('count',0))}</td></tr>"
            for i in (new_entities if isinstance(new_entities, list) else []) if isinstance(i, dict)
        ) or "<tr><td colspan='2' class='muted'>No new entities detected.</td></tr>"

        removed_rows = "".join(
            f"<tr><td>{self._clean_text(i.get('module','-'))}</td><td>{self._safe_int(i.get('count',0))}</td></tr>"
            for i in (removed_entities if isinstance(removed_entities, list) else []) if isinstance(i, dict)
        ) or "<tr><td colspan='2' class='muted'>No removed entities detected.</td></tr>"

        changed_rows = "".join(
            f"<tr><td>{self._clean_text(i.get('module','-'))}</td>"
            f"<td>{', '.join(self._clean_text(f) for f in sorted(i.get('changes', {}).keys()))}</td></tr>"
            for i in (changed_modules if isinstance(changed_modules, list) else [])
            if isinstance(i, dict) and isinstance(i.get('changes'), dict) and i.get('changes')
        ) or "<tr><td colspan='2' class='muted'>No module changes detected.</td></tr>"

        return f"""
        <section class="card">
            <h2>Baseline Comparison</h2>
            <p class="meta-row">
                Baseline Status: <strong>{self._clean_text(baseline.get('baseline_status','unknown')).title()}</strong>
                | Baseline Created: {self._clean_text(baseline.get('baseline_created_at','-'))}
            </p>
            <div class="metric-grid baseline-metrics">
                <div class="metric"><span class="label">New Entities</span><span class="value">{self._safe_int(summary.get('new_entities_total',0))}</span></div>
                <div class="metric"><span class="label">Removed Entities</span><span class="value">{self._safe_int(summary.get('removed_entities_total',0))}</span></div>
                <div class="metric"><span class="label">Changed Modules</span><span class="value">{self._safe_int(summary.get('changed_modules_total',0))}</span></div>
            </div>
            <div class="baseline-grid">
                <div class="table-wrap">
                    <h3>New Entities Since Baseline</h3>
                    <table><thead><tr><th>Module</th><th>Count</th></tr></thead><tbody>{new_rows}</tbody></table>
                </div>
                <div class="table-wrap">
                    <h3>Removed Entities Since Baseline</h3>
                    <table><thead><tr><th>Module</th><th>Count</th></tr></thead><tbody>{removed_rows}</tbody></table>
                </div>
            </div>
            <div class="table-wrap">
                <h3>Changed Module Results</h3>
                <table><thead><tr><th>Module</th><th>Changed Fields</th></tr></thead><tbody>{changed_rows}</tbody></table>
            </div>
        </section>
        """

    # ------------------------------------------------------------------
    # Anomaly section (shared by dashboard and anomaly_detect module)
    # ------------------------------------------------------------------

    def _build_anomaly_html(self, anomaly: Dict[str, Any]) -> str:
        if not isinstance(anomaly, dict) or not anomaly:
            return ""

        flags     = anomaly.get("anomaly_flags", [])
        ops       = self._safe_int(anomaly.get("operations_analyzed", 0))
        narrative = self._clean_text(anomaly.get("risk_assessment", ""))

        severity_color = {"CRITICAL": "#f87171", "HIGH": "#fb923c", "MEDIUM": "#fbbf24", "LOW": "#34d399"}

        flag_rows = "".join(
            (lambda sev, color: (
                f"<tr>"
                f"<td style='color:{color};font-weight:bold'>{self._clean_text(sev)}</td>"
                f"<td>{self._clean_text(f.get('rule','-'))}</td>"
                f"<td>{self._clean_text(f.get('detail','-'))}</td>"
                "</tr>"
            ))(str(f.get("severity","")).upper(), severity_color.get(str(f.get("severity","")).upper(), "#97a8be"))
            for f in (flags if isinstance(flags, list) else []) if isinstance(f, dict)
        ) or "<tr><td colspan='3' class='muted'>No anomalies detected in recent telemetry.</td></tr>"

        narrative_html = (
            f"<div style='margin-top:12px;padding:12px;border:1px solid var(--border);"
            f"border-radius:8px;color:var(--text-muted);font-size:0.9rem;line-height:1.6'>{narrative}</div>"
            if narrative and narrative not in ("-", "AI analysis unavailable.")
            else ""
        )

        return f"""
        <section class="card">
            <h2>Anomaly Analysis</h2>
            <p class="meta-row">Operations analysed: <strong>{ops}</strong></p>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Severity</th><th>Rule</th><th>Detail</th></tr></thead>
                    <tbody>{flag_rows}</tbody>
                </table>
            </div>
            {narrative_html}
        </section>
        """

    # ------------------------------------------------------------------
    # Global dashboard
    # ------------------------------------------------------------------

    def _build_dashboard_html(self, data: Dict[str, Any]) -> str:
        payload    = data.get("data", {}) if isinstance(data, dict) else {}
        modules    = payload.get("modules_run", [])
        breakdown  = payload.get("module_breakdown", {})
        scan_results = payload.get("scan_results", [])
        baseline_comparison = payload.get("Baseline Comparison", {})
        anomaly_analysis    = payload.get("anomaly_analysis", {})

        modules_html = "".join(
            f"<span class='chip'>{self._clean_text(m)}</span>" for m in modules
        ) or "<span class='chip chip-empty'>No modules</span>"

        breakdown_rows = "".join(
            f"<tr>"
            f"<td>{self._clean_text(module)}</td>"
            f"<td>{self._safe_int(s.get('runs',0))}</td>"
            f"<td>{self._safe_int(s.get('success',0))}</td>"
            f"<td style='color:{'#f87171' if self._safe_int(s.get('error',0)) else 'inherit'}'>{self._safe_int(s.get('error',0))}</td>"
            f"<td>{self._safe_int(s.get('entities',0))}</td>"
            "</tr>"
            for module, s in sorted(breakdown.items()) if isinstance(s, dict)
        ) or "<tr><td colspan='5' class='muted'>No module activity recorded.</td></tr>"

        scan_rows = "".join(
            f"<tr>"
            f"<td>{self._clean_text(r.get('module_name','-'))}</td>"
            f"<td style='color:{'#34d399' if str(r.get('status','')).lower()=='success' else '#f87171'}'>"
            f"{self._clean_text(r.get('status','-')).title()}</td>"
            f"<td>{self._clean_text(r.get('timestamp','-'))}</td>"
            f"<td>{self._safe_int(r.get('targets_found',0))}</td>"
            f"<td>{self._safe_int(r.get('error_count',0))}</td>"
            f"<td>{self._safe_int(r.get('entities_found',0))}</td>"
            "</tr>"
            for r in (scan_results if isinstance(scan_results, list) else []) if isinstance(r, dict)
        ) or "<tr><td colspan='6' class='muted'>No scan results available.</td></tr>"

        baseline_html = self._build_baseline_comparison_html(baseline_comparison)
        anomaly_html  = self._build_anomaly_html(anomaly_analysis)

        return f"""
        <section class="card">
            <h2>Executive Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Total Operations</span><span class="value">{self._safe_int(payload.get('total_ops',0))}</span></div>
                <div class="metric"><span class="label">Successful Modules</span><span class="value" style="color:#34d399">{self._safe_int(payload.get('successful_modules',0))}</span></div>
                <div class="metric"><span class="label">Failed Modules</span><span class="value" style="color:{'#f87171' if self._safe_int(payload.get('failed_modules',0)) else '#34d399'}">{self._safe_int(payload.get('failed_modules',0))}</span></div>
                <div class="metric"><span class="label">Entities Found</span><span class="value">{self._safe_int(payload.get('entities_found',0))}</span></div>
            </div>
            <div class="chips">{modules_html}</div>
        </section>

        <section class="card">
            <h2>Module Breakdown</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Module</th><th>Runs</th><th>Success</th><th>Error</th><th>Entities</th></tr></thead>
                    <tbody>{breakdown_rows}</tbody>
                </table>
            </div>
        </section>

        {baseline_html}
        {anomaly_html}

        <section class="card">
            <h2>Scan Results</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Module</th><th>Status</th><th>Timestamp</th><th>Targets Found</th><th>Error Count</th><th>Entities Found</th></tr></thead>
                    <tbody>{scan_rows}</tbody>
                </table>
            </div>
        </section>
        """

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _build_default_html(self, data: Dict[str, Any]) -> str:
        module = (data.get("module") or "").lower()
        dispatch = {
            "wifi_audit":       self._build_wifi_html,
            "lan_scan":         self._build_lan_html,
            "tls_audit":        self._build_tls_html,
            "arp_monitor":      self._build_arp_html,
            "bluetooth_recon":  self._build_bluetooth_html,
            "pentest_tools":    self._build_pentest_html,
            "anomaly_detect":   self._build_anomaly_detect_html,
            "passive_monitor":  self._build_passive_html,
        }
        if module in dispatch:
            return dispatch[module](data)
        return self._build_generic_html(data)

    def _build_generic_html(self, data: Dict[str, Any]) -> str:
        """Fallback renderer for unknown module types."""
        payload     = data.get("data", {}) if isinstance(data, dict) else {}

        def _get(key, default=None):
            v = data.get(key)
            return v if v is not None else payload.get(key, default)

        timestamp  = self._clean_text(_get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        targets    = self._safe_int(_get("targets", 0))
        entities   = self._safe_int(_get("entities_found", targets))
        errors     = data.get("errors") or payload.get("errors") or []
        err_count  = len(errors) if isinstance(errors, list) else 0

        errors_html = ""
        if isinstance(errors, list) and errors:
            rows = "".join(f"<tr><td>{self._clean_text(e)}</td></tr>" for e in errors)
            errors_html = f"""
            <div class="table-wrap" style="margin-top:12px">
                <h3>Errors</h3>
                <table><tbody>{rows}</tbody></table>
            </div>"""

        return f"""
        <section class="card">
            <h2>Operation Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Module</span><span class="value" style="font-size:1rem">{self._clean_text(data.get('module','Unknown'))}</span></div>
                <div class="metric"><span class="label">Status</span><span class="value" style="font-size:1rem">{self._clean_text(data.get('status','Unknown')).title()}</span></div>
                <div class="metric"><span class="label">Targets Found</span><span class="value">{targets}</span></div>
                <div class="metric"><span class="label">Entities Found</span><span class="value">{entities}</span></div>
            </div>
            <p class="meta-row">Timestamp: {timestamp} | Errors: {err_count}</p>
            {errors_html}
        </section>
        """

    # ------------------------------------------------------------------
    # HTML output
    # ------------------------------------------------------------------

    def generate_html_report(self, data: Dict[str, Any], filename: str = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.html"

        filepath    = os.path.join(self.output_dir, filename)
        module_name = data.get("module", "Unknown") if isinstance(data, dict) else "Unknown"
        status      = data.get("status", "Unknown") if isinstance(data, dict) else "Unknown"

        body_html = self._build_dashboard_html(data) if module_name == "dashboard" else self._build_default_html(data)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberDeck Report — {self._clean_text(module_name)}</title>
    <style>
        :root {{
            --bg-main: #09111f;
            --bg-panel: #0f1a2f;
            --bg-header: #14233d;
            --border: #1f3a5a;
            --text-main: #e2ebf6;
            --text-muted: #97a8be;
            --accent: #4fd1c5;
            --danger: #f87171;
            --success: #34d399;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 24px;
            color: var(--text-main);
            background: radial-gradient(circle at top, #12213a 0%, var(--bg-main) 48%);
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }}
        .container {{ max-width: 1280px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(120deg, var(--bg-header), #183459);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px 24px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0; font-size: 1.9rem; letter-spacing: 0.03em; }}
        .meta {{ margin-top: 8px; color: var(--text-muted); font-size: 0.95rem; }}
        .meta-row {{ color: var(--text-muted); margin: 0 0 14px 0; font-size: 0.92rem; }}
        .card {{
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        h2 {{ margin: 0 0 14px 0; font-size: 1.1rem; }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px;
            margin-bottom: 14px;
        }}
        .metric {{
            border: 1px solid var(--border);
            border-radius: 10px;
            background: rgba(255,255,255,0.02);
            padding: 10px 12px;
        }}
        .metric .label {{ display: block; color: var(--text-muted); font-size: 0.85rem; }}
        .metric .value {{ display: block; margin-top: 4px; font-size: 1.2rem; font-weight: 700; color: var(--accent); }}
        .baseline-metrics .metric .value {{ color: #93c5fd; }}
        .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .chip {{
            border: 1px solid var(--border);
            background: rgba(79,209,197,0.12);
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.8rem;
            color: #b6fff9;
        }}
        .chip-empty {{ color: var(--text-muted); background: rgba(255,255,255,0.03); }}
        .table-wrap {{ overflow-x: auto; }}
        .baseline-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 12px;
            margin-bottom: 12px;
        }}
        h3 {{ margin: 0 0 10px 0; font-size: 0.95rem; color: var(--text-muted); font-weight: 600; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 400px; }}
        th, td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            text-align: left;
            font-size: 0.9rem;
        }}
        th {{ color: #b6d0ee; font-weight: 600; white-space: nowrap; }}
        td {{ color: var(--text-main); }}
        code {{ font-family: monospace; font-size: 0.85rem; color: #93c5fd; }}
        .muted {{ color: var(--text-muted); text-align: center; }}
        @media (max-width: 720px) {{
            body {{ padding: 14px; }}
            .header h1 {{ font-size: 1.4rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>CyberDeck Executive Dashboard</h1>
            <p class="meta">
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
                Module: {self._clean_text(module_name)} |
                Status: {self._clean_text(status).title()}
            </p>
        </header>
        {body_html}
    </div>
</body>
</html>
"""
        try:
            with open(filepath, "w") as f:
                f.write(html_content)
            return filepath
        except Exception as e:
            print(f"[ReportGenerator] Error saving HTML report: {e}")
            return None


def generate_report(data: Dict[str, Any]) -> str:
    generator = ReportGenerator()
    return generator.generate_html_report(data)
