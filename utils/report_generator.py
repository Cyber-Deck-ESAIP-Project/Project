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

    def _build_dashboard_html(self, data: Dict[str, Any]) -> str:
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        modules = payload.get("modules_run", [])
        breakdown = payload.get("module_breakdown", {})
        scan_results = payload.get("scan_results", [])

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
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        return f"""
        <section class="card">
            <h2>Operation Summary</h2>
            <div class="table-wrap">
                <table>
                    <tbody>
                        <tr><th>Module</th><td>{self._clean_text(data.get('module', 'Unknown'))}</td></tr>
                        <tr><th>Status</th><td>{self._clean_text(data.get('status', 'Unknown')).title()}</td></tr>
                        <tr><th>Timestamp</th><td>{self._clean_text(payload.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))}</td></tr>
                        <tr><th>Targets Found</th><td>{self._safe_int(payload.get('targets', 0))}</td></tr>
                        <tr><th>Error Count</th><td>{self._safe_int(payload.get('error_count', 0))}</td></tr>
                        <tr><th>Entities Found</th><td>{self._safe_int(payload.get('entities_found', payload.get('targets', 0)))}</td></tr>
                    </tbody>
                </table>
            </div>
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
