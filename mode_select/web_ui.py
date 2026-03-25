import os
import sys
import json
from flask import Flask, render_template, jsonify, request, Response

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.event_bus import event_bus
from core.app_state import state
from core.controller import controller
from modules import lan_scan, wifi_audit, bluetooth_recon, pentest_tools, anomaly_detect, dashboard, passive_monitor, arp_monitor, tls_audit, hwmon_telemetry
from utils.report_generator import generate_report

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Maintain an internal state for the API
api_state = {
    "logs": [">> System Ready. CyberDeck Command Center Initialized.\n>> Awaiting deployment directive."],
    "active_module": None,
    "risk_level": 0,
    "ops": 0,
    "entities": 0,
    "lockdown": False
}

# Define the runnable modules mapping
MODULES = {
    "Passive Monitor": passive_monitor.run,
    "ARP Monitor": arp_monitor.run,
    "LAN Scanning": lan_scan.run,
    "WiFi Audit": wifi_audit.run,
    "Bluetooth Recon": bluetooth_recon.run,
    "TLS Audit": tls_audit.run,
    "Pentest Toolkit": pentest_tools.run,
    "Anomaly Detection": anomaly_detect.run,
    "Hardware Monitor": hwmon_telemetry.run,
    "Reports": dashboard.run
}

def log_to_web(msg: str):
    """Callback for controller modules to log to the web UI"""
    api_state["logs"].append(msg)
    # Keep last 100 logs to prevent memory leak
    if len(api_state["logs"]) > 100:
        api_state["logs"] = api_state["logs"][-100:]

# --- Event Bus Subscriptions ---
def on_module_start(name: str):
    api_state["active_module"] = name

def on_module_stop(name: str):
    if api_state["active_module"] == name:
        api_state["active_module"] = None
        log_to_web(f">> Finished execution: {name}")

def on_risk_update(score: int):
    api_state["risk_level"] = score

def on_telemetry_update(telemetry: dict):
    api_state["ops"] = telemetry.get('total_operations', 0)
    api_state["entities"] = telemetry.get('entities_tracked', 0)

event_bus.subscribe("MODULE_STARTED", on_module_start)
event_bus.subscribe("MODULE_STOPPED", on_module_stop)
event_bus.subscribe("RISK_UPDATED", on_risk_update)
event_bus.subscribe("HISTORY_UPDATED", on_telemetry_update)

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html', modules=list(MODULES.keys()))

@app.route('/reports')
def reports():
    # Always rebuild global dashboard summary before rendering reports UI.
    dashboard.run({"system": {"results_dir": "results"}})
    # Always reset reports UI to the global dashboard view.
    return render_template('reports.html', global_report_url='/reports/global')

@app.route('/api/status')
def status():
    # Sync lockdown dynamically from core app state
    api_state["lockdown"] = state.is_locked_down
    return jsonify(api_state)

@app.route('/api/run', methods=['POST'])
def run_module():
    data = request.json
    if not data or 'module' not in data:
        return jsonify({"error": "Module name required"}), 400
        
    module_name = data['module']
    target = data.get('target', '127.0.0.1')
    
    if module_name not in MODULES:
        return jsonify({"error": "Unknown module"}), 404
        
    if state.is_locked_down:
        return jsonify({"error": "System is locked down"}), 403

    func = MODULES[module_name]
    controller.dispatch_module(module_name, func, callback=log_to_web, target=target)
    
    return jsonify({"success": True, "message": f"Started {module_name}"})

@app.route('/api/lockdown', methods=['POST'])
def toggle_lockdown():
    new_state = not state.is_locked_down
    state.set_lockdown(new_state)
    
    if new_state:
        log_to_web(">> EMERGENCY LOCKDOWN ENGAGED. All module dispatch blocked.")
    else:
        log_to_web(">> Lockdown disengaged. System ready.")
        
    return jsonify({"lockdown": new_state})

@app.route('/api/results/list')
def list_results():
    results_dir = os.path.join(PROJECT_ROOT, "results")
    if not os.path.exists(results_dir):
        return jsonify([])

    files = [
        f for f in os.listdir(results_dir)
        if f.endswith('.json') and f != 'baseline.json'
    ]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(results_dir, f)), reverse=True)
    return jsonify(files)

@app.route('/api/html-reports/list')
def list_html_reports():
    results_dir = os.path.join(PROJECT_ROOT, "results")
    if not os.path.exists(results_dir):
        return jsonify([])
    files = [f for f in os.listdir(results_dir) if f.endswith('.html')]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(results_dir, f)), reverse=True)
    return jsonify(files)

@app.route('/results/html/<filename>')
def serve_html_report(filename):
    results_dir = os.path.join(PROJECT_ROOT, "results")
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(results_dir, safe_filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    with open(filepath, 'r') as f:
        return Response(f.read(), mimetype='text/html')

def _generate_html_from_json_report(filename: str) -> Response:
    results_dir = os.path.join(PROJECT_ROOT, "results")
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(results_dir, safe_filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    try:
        with open(filepath, 'r') as f:
            content = json.load(f)
        
        target_html = generate_report(content)
        if target_html and os.path.exists(target_html):
            with open(target_html, 'r') as h:
                return Response(h.read(), mimetype='text/html')
        else:
            return jsonify({"error": "HTML Generation failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _generate_global_dashboard_html() -> Response:
    # Always rebuild dashboard summary from current scan results.
    try:
        report_result = dashboard.run({"system": {"results_dir": "results"}})

        # Enrich with anomaly analysis
        try:
            anomaly_result = anomaly_detect.run(controller.config)
            if anomaly_result.get("status") in ("success", "partial"):
                report_result["data"]["anomaly_analysis"] = anomaly_result.get("data", {})
        except Exception:
            pass  # anomaly analysis is best-effort

        # Regenerate HTML with anomaly data merged in
        html_path = generate_report(report_result)
        if not html_path or not os.path.exists(html_path):
            return jsonify({"error": "Global dashboard generation failed"}), 500

        with open(html_path, 'r') as h:
            return Response(h.read(), mimetype='text/html')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/report/<filename>')
def get_report(filename):
    return _generate_html_from_json_report(filename)

@app.route('/reports/global')
def get_global_report():
    return _generate_global_dashboard_html()

# Backward-compatible API aliases
@app.route('/api/reports/<filename>')
def get_report_api(filename):
    return _generate_html_from_json_report(filename)

@app.route('/api/reports/global')
def get_global_report_api():
    return _generate_global_dashboard_html()

def start_web_ui(port=5000):
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    start_web_ui()
