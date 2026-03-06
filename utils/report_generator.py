import os
import json
from datetime import datetime

class ReportGenerator:
    """
    Utility class for generating formatted audit reports from scan telemetry.
    Matches the project structure shown in the requested design.
    """
    def __init__(self, output_dir="results"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _json_to_html(self, data, depth=0):
        if isinstance(data, dict):
            if not data: return "<i>Empty Data</i>"
            html = "<table class='data-table'>"
            for k, v in data.items():
                html += f"<tr><th>{k}</th><td>{self._json_to_html(v, depth+1)}</td></tr>"
            html += "</table>"
            return html
        elif isinstance(data, list):
            if not data: return "<i>Empty List</i>"
            # If list of dicts with similar keys, make a multi-column table
            if all(isinstance(x, dict) for x in data) and len(data) > 0:
                keys = []
                for item in data:
                    for k in item.keys():
                        if k not in keys: keys.append(k)
                if len(keys) <= 6:
                    html = "<div style='overflow-x: auto;'><table class='data-table list-table'><tr>"
                    for k in keys: html += f"<th>{k}</th>"
                    html += "</tr>"
                    for item in data:
                        html += "<tr>"
                        for k in keys:
                            html += f"<td>{self._json_to_html(item.get(k, ''), depth+1)}</td>"
                        html += "</tr>"
                    html += "</table></div>"
                    return html
            
            # Otherwise simple list
            html = "<ul>"
            for item in data:
                html += f"<li>{self._json_to_html(item, depth+1)}</li>"
            html += "</ul>"
            return html
        elif isinstance(data, str) and data.startswith("http"):
            return f"<a href='{data}' target='_blank'>{data}</a>"
        else:
            return str(data)

    def generate_html_report(self, data, filename=None):
        """Generates a detailed HTML audit report from the provided telemetry data."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        module_name = data.get('module', 'Unknown')
        status = data.get('status', 'Completed')
        
        # Build the dynamic HTML
        parsed_html = self._json_to_html(data.get('data', data))
        raw_json = json.dumps(data, indent=4)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberDeck Audit Report // {module_name}</title>
    <style>
        :root {{
            --bg-main: #0a0e17;
            --bg-card: #111827;
            --border: #1f2937;
            --text-main: #e5e7eb;
            --text-muted: #9ca3af;
            --accent: #00ffff;
            --success: #10b981;
        }}
        body {{ 
            font-family: 'Inter', system-ui, -apple-system, sans-serif; 
            background-color: var(--bg-main); 
            color: var(--text-main); 
            padding: 2rem; 
            margin: 0;
            line-height: 1.5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ 
            border-bottom: 2px solid var(--border); 
            padding-bottom: 1rem; 
            margin-bottom: 2rem; 
            display: flex; 
            justify-content: space-between; 
            align-items: flex-end; 
        }}
        .header h1 {{ color: var(--accent); margin: 0; font-size: 2.5rem; letter-spacing: -0.05em; }}
        .meta-info {{ color: var(--text-muted); font-family: monospace; font-size: 0.95rem; text-align: right; }}
        .status {{ color: var(--success); font-weight: 600; text-transform: uppercase; }}
        .card {{ 
            background: var(--bg-card); 
            border: 1px solid var(--border); 
            border-radius: 8px; 
            padding: 1.5rem; 
            margin-bottom: 2rem; 
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); 
        }}
        .card h2 {{ margin-top: 0; color: #fff; font-size: 1.25rem; margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
        table.data-table {{ width: 100%; border-collapse: collapse; font-family: monospace; font-size: 0.95rem; border-radius: 6px; overflow: hidden; }}
        table.data-table th, table.data-table td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
        table.data-table th {{ background-color: rgba(255, 255, 255, 0.05); color: var(--accent); font-weight: 500; width: 30%; }}
        table.data-table tr:hover {{ background-color: rgba(255, 255, 255, 0.02); }}
        table.list-table th {{ background-color: rgba(255, 255, 255, 0.05); color: var(--text-muted); text-transform: uppercase; font-size: 0.8rem; width: auto; }}
        ul {{ margin: 0; padding-left: 1.5rem; }}
        li {{ margin-bottom: 0.25rem; }}
        .raw-dump {{ background-color: rgba(0,0,0,0.5); padding: 1rem; border-radius: 6px; border: 1px solid var(--border); overflow-x: auto; font-size: 0.85rem; color: var(--text-muted); }}
        a {{ color: var(--accent); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>CyberDeck OS // Detailed Report</h1>
                <p style="margin: 0.5rem 0 0 0; color: var(--text-muted);">Operation result visualization</p>
            </div>
            <div class="meta-info">
                <p style="margin: 0;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p style="margin: 0.25rem 0 0 0;">Module: <span class="status">{module_name}</span> | Status: <span class="status">{status}</span></p>
            </div>
        </div>

        <div class="card">
            <h2>Analyzed Telemetry</h2>
            {parsed_html}
        </div>

        <div class="card">
            <h2>Raw JSON Dump</h2>
            <pre class="raw-dump">{raw_json}</pre>
        </div>
    </div>
</body>
</html>
"""
        
        try:
            with open(filepath, 'w') as f:
                f.write(html_content)
            return filepath
        except Exception as e:
            print(f"[ReportGenerator] Error saving HTML report: {e}")
            return None

def generate_report(data):
    """Helper function to quickly generate an HTML report."""
    generator = ReportGenerator()
    return generator.generate_html_report(data)
