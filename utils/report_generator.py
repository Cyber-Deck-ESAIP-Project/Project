import os
from datetime import datetime
from html import escape
from typing import Any, Dict


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

    def _build_baseline_comparison_html(self, baseline: Dict[str, Any]) -> str:
        if not isinstance(baseline, dict) or not baseline:
            return ""

        summary = baseline.get("summary", {})
        new_entities = baseline.get("new_entities", [])
        removed_entities = baseline.get("removed_entities", [])
        changed_modules = baseline.get("changed_module_results", [])

        new_rows = []
        for item in new_entities if isinstance(new_entities, list) else []:
            if not isinstance(item, dict):
                continue
            new_rows.append(
                "<tr>"
                f"<td>{self._clean_text(item.get('module', '-'))}</td>"
                f"<td>{self._safe_int(item.get('count', 0))}</td>"
                "</tr>"
            )
        new_table = "".join(new_rows) or "<tr><td colspan='2' class='muted'>No new entities detected.</td></tr>"

        removed_rows = []
        for item in removed_entities if isinstance(removed_entities, list) else []:
            if not isinstance(item, dict):
                continue
            removed_rows.append(
                "<tr>"
                f"<td>{self._clean_text(item.get('module', '-'))}</td>"
                f"<td>{self._safe_int(item.get('count', 0))}</td>"
                "</tr>"
            )
        removed_table = "".join(removed_rows) or "<tr><td colspan='2' class='muted'>No removed entities detected.</td></tr>"

        changed_rows = []
        for item in changed_modules if isinstance(changed_modules, list) else []:
            if not isinstance(item, dict):
                continue
            module_name = self._clean_text(item.get("module", "-"))
            changes = item.get("changes", {})
            if not isinstance(changes, dict) or not changes:
                continue
            changed_fields = ", ".join(self._clean_text(field) for field in sorted(changes.keys()))
            changed_rows.append(
                "<tr>"
                f"<td>{module_name}</td>"
                f"<td>{changed_fields if changed_fields else '-'}</td>"
                "</tr>"
            )
        changed_table = "".join(changed_rows) or "<tr><td colspan='2' class='muted'>No module changes detected.</td></tr>"

        return f"""
        <section class="card">
            <h2>Baseline Comparison</h2>
            <p class="meta-row">
                Baseline Status: <strong>{self._clean_text(baseline.get('baseline_status', 'unknown')).title()}</strong>
                | Baseline Created: {self._clean_text(baseline.get('baseline_created_at', '-'))}
            </p>
            <div class="metric-grid baseline-metrics">
                <div class="metric"><span class="label">New Entities</span><span class="value">{self._safe_int(summary.get('new_entities_total', 0))}</span></div>
                <div class="metric"><span class="label">Removed Entities</span><span class="value">{self._safe_int(summary.get('removed_entities_total', 0))}</span></div>
                <div class="metric"><span class="label">Changed Modules</span><span class="value">{self._safe_int(summary.get('changed_modules_total', 0))}</span></div>
            </div>
            <div class="baseline-grid">
                <div class="table-wrap">
                    <h3>New Entities Since Baseline</h3>
                    <table>
                        <thead><tr><th>Module</th><th>Count</th></tr></thead>
                        <tbody>{new_table}</tbody>
                    </table>
                </div>
                <div class="table-wrap">
                    <h3>Removed Entities Since Baseline</h3>
                    <table>
                        <thead><tr><th>Module</th><th>Count</th></tr></thead>
                        <tbody>{removed_table}</tbody>
                    </table>
                </div>
            </div>
            <div class="table-wrap">
                <h3>Changed Module Results</h3>
                <table>
                    <thead><tr><th>Module</th><th>Changed Fields</th></tr></thead>
                    <tbody>{changed_table}</tbody>
                </table>
            </div>
        </section>
        """

    def _build_anomaly_html(self, anomaly: Dict[str, Any]) -> str:
        if not isinstance(anomaly, dict) or not anomaly:
            return ""

        flags = anomaly.get("anomaly_flags", [])
        ops = self._safe_int(anomaly.get("operations_analyzed", 0))
        narrative = self._clean_text(anomaly.get("risk_assessment", ""))

        severity_color = {"CRITICAL": "#f87171", "HIGH": "#fb923c", "MEDIUM": "#fbbf24", "LOW": "#34d399"}

        flag_rows = []
        for f in flags if isinstance(flags, list) else []:
            if not isinstance(f, dict):
                continue
            sev = str(f.get("severity", "")).upper()
            color = severity_color.get(sev, "#97a8be")
            flag_rows.append(
                "<tr>"
                f"<td style='color:{color};font-weight:bold'>{self._clean_text(sev)}</td>"
                f"<td>{self._clean_text(f.get('rule', '-'))}</td>"
                f"<td>{self._clean_text(f.get('detail', '-'))}</td>"
                "</tr>"
            )
        flag_table = "".join(flag_rows) or (
            "<tr><td colspan='3' class='muted'>No anomalies detected in recent telemetry.</td></tr>"
        )

        narrative_html = (
            f"<div style='margin-top:12px;padding:12px;border:1px solid var(--border);"
            f"border-radius:8px;color:var(--text-muted);font-size:0.9rem;line-height:1.6'>"
            f"{narrative}</div>"
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
                    <tbody>{flag_table}</tbody>
                </table>
            </div>
            {narrative_html}
        </section>
        """

    def _build_dashboard_html(self, data: Dict[str, Any]) -> str:
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        modules = payload.get("modules_run", [])
        breakdown = payload.get("module_breakdown", {})
        scan_results = payload.get("scan_results", [])
        baseline_comparison = payload.get("Baseline Comparison", {})
        anomaly_analysis = payload.get("anomaly_analysis", {})

        modules_html = "".join(f"<span class='chip'>{self._clean_text(module)}</span>" for module in modules)
        if not modules_html:
            modules_html = "<span class='chip chip-empty'>No modules</span>"

        breakdown_rows = []
        for module, stats in sorted(breakdown.items()):
            if not isinstance(stats, dict):
                continue
            breakdown_rows.append(
                "<tr>"
                f"<td>{self._clean_text(module)}</td>"
                f"<td>{self._safe_int(stats.get('runs', 0))}</td>"
                f"<td>{self._safe_int(stats.get('success', 0))}</td>"
                f"<td>{self._safe_int(stats.get('error', 0))}</td>"
                f"<td>{self._safe_int(stats.get('entities', 0))}</td>"
                "</tr>"
            )
        breakdown_table = "".join(breakdown_rows) or (
            "<tr><td colspan='5' class='muted'>No module activity recorded.</td></tr>"
        )

        scan_rows = []
        for row in scan_results if isinstance(scan_results, list) else []:
            if not isinstance(row, dict):
                continue
            scan_rows.append(
                "<tr>"
                f"<td>{self._clean_text(row.get('module_name', '-'))}</td>"
                f"<td>{self._clean_text(row.get('status', '-')).title()}</td>"
                f"<td>{self._clean_text(row.get('timestamp', '-'))}</td>"
                f"<td>{self._safe_int(row.get('targets_found', 0))}</td>"
                f"<td>{self._safe_int(row.get('error_count', 0))}</td>"
                f"<td>{self._safe_int(row.get('entities_found', 0))}</td>"
                "</tr>"
            )
        scan_table = "".join(scan_rows) or (
            "<tr><td colspan='6' class='muted'>No scan results available.</td></tr>"
        )

        baseline_html = self._build_baseline_comparison_html(baseline_comparison)
        anomaly_html = self._build_anomaly_html(anomaly_analysis)

        return f"""
        <section class="card">
            <h2>Executive Summary</h2>
            <div class="metric-grid">
                <div class="metric"><span class="label">Total Operations</span><span class="value">{self._safe_int(payload.get('total_ops', 0))}</span></div>
                <div class="metric"><span class="label">Successful Modules</span><span class="value">{self._safe_int(payload.get('successful_modules', 0))}</span></div>
                <div class="metric"><span class="label">Failed Modules</span><span class="value">{self._safe_int(payload.get('failed_modules', 0))}</span></div>
                <div class="metric"><span class="label">Entities Found</span><span class="value">{self._safe_int(payload.get('entities_found', 0))}</span></div>
            </div>
            <div class="chips">{modules_html}</div>
        </section>

        <section class="card">
            <h2>Module Breakdown</h2>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr><th>Module</th><th>Runs</th><th>Success</th><th>Error</th><th>Entities</th></tr>
                    </thead>
                    <tbody>{breakdown_table}</tbody>
                </table>
            </div>
        </section>

        {baseline_html}

        {anomaly_html}

        <section class="card">
            <h2>Scan Results</h2>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Module Name</th>
                            <th>Status</th>
                            <th>Timestamp</th>
                            <th>Targets Found</th>
                            <th>Error Count</th>
                            <th>Entities Found</th>
                        </tr>
                    </thead>
                    <tbody>{scan_table}</tbody>
                </table>
            </div>
        </section>
        """

    def _build_default_html(self, data: Dict[str, Any]) -> str:
        # Support both create_result() format (nested "data" key)
        # and compact summary format (flat keys at top level).
        payload = data.get("data", {}) if isinstance(data, dict) else {}

        def _get(key, default=None):
            v = data.get(key)
            return v if v is not None else payload.get(key, default)

        timestamp   = self._clean_text(_get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        targets      = self._safe_int(_get('targets', 0))
        error_count  = self._safe_int(_get('error_count', 0))
        entities     = self._safe_int(_get('entities_found', targets))

        # Data summary block (present in compact summary files)
        ds = data.get('data_summary') or payload.get('data_summary') or {}
        summary_html = ""
        if isinstance(ds, dict) and ds:
            summary_html = f"""
            <div class="metric-grid" style="margin-top:12px">
                <div class="metric"><span class="label">Fields</span><span class="value">{self._safe_int(ds.get('fields',0))}</span></div>
                <div class="metric"><span class="label">List Items</span><span class="value">{self._safe_int(ds.get('list_items',0))}</span></div>
                <div class="metric"><span class="label">Nested Objects</span><span class="value">{self._safe_int(ds.get('nested_objects',0))}</span></div>
                <div class="metric"><span class="label">Scalar Fields</span><span class="value">{self._safe_int(ds.get('scalar_fields',0))}</span></div>
            </div>"""

        errors = data.get('errors') or payload.get('errors') or []
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
            <p class="meta-row">Timestamp: {timestamp} | Errors: {error_count}</p>
            {summary_html}
            {errors_html}
        </section>
        """

    def generate_html_report(self, data: Dict[str, Any], filename: str = None) -> str:
        """Generates a readable HTML audit report from telemetry summary data."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.html"

        filepath = os.path.join(self.output_dir, filename)
        module_name = data.get("module", "Unknown") if isinstance(data, dict) else "Unknown"
        status = data.get("status", "Unknown") if isinstance(data, dict) else "Unknown"

        body_html = self._build_dashboard_html(data) if module_name == "dashboard" else self._build_default_html(data)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberDeck Executive Report</title>
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
            background: rgba(255, 255, 255, 0.02);
            padding: 10px 12px;
        }}
        .metric .label {{ display: block; color: var(--text-muted); font-size: 0.85rem; }}
        .metric .value {{ display: block; margin-top: 4px; font-size: 1.2rem; font-weight: 700; color: var(--accent); }}
        .baseline-metrics .metric .value {{ color: #93c5fd; }}
        .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .chip {{
            border: 1px solid var(--border);
            background: rgba(79, 209, 197, 0.12);
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.8rem;
            color: #b6fff9;
        }}
        .chip-empty {{ color: var(--text-muted); background: rgba(255, 255, 255, 0.03); }}
        .table-wrap {{ overflow-x: auto; }}
        .baseline-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 12px;
            margin-bottom: 12px;
        }}
        h3 {{
            margin: 0 0 10px 0;
            font-size: 0.95rem;
            color: var(--text-muted);
            font-weight: 600;
        }}
        table {{ width: 100%; border-collapse: collapse; min-width: 760px; }}
        th, td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            text-align: left;
            font-size: 0.9rem;
            white-space: nowrap;
        }}
        th {{ color: #b6d0ee; font-weight: 600; }}
        td {{ color: var(--text-main); }}
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
    """Helper function to quickly generate an HTML report."""
    generator = ReportGenerator()
    return generator.generate_html_report(data)
