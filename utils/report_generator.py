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

    def generate_html_report(self, data, filename=None):
        """Generates a basic HTML audit report from the provided data dictionary."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        html_content = f"""
        <html>
        <head>
            <title>CyberDeck Audit Report</title>
            <style>
                body {{ font-family: 'Courier New', Courier, monospace; background-color: #0D1117; color: #C9D1D9; padding: 20px; }}
                h1 {{ color: #00FFFF; border-bottom: 1px solid #30363D; }}
                pre {{ background-color: #010409; padding: 15px; border: 1px solid #30363D; overflow: auto; }}
                .status {{ color: #4ADE80; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>CyberDeck OS // Audit Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Module: <span class="status">{data.get('module', 'Unknown')}</span></p>
            <hr>
            <h2>Raw Telemetry Data</h2>
            <pre>{json.dumps(data, indent=4)}</pre>
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
