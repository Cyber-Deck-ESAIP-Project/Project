import os
import json
from utils.result_handler import create_result
from utils.report_generator import generate_report

def run(config, callback=None, **kwargs):
    if callback: callback("[*] Aggregating scan telemetry for executive summary...")
    
    results_dir = config.get("system", {}).get("results_dir", "results")
    history_file = "logs/history.json"
    
    total_ops = 0
    successful_modules = 0
    failed_modules = 0
    entities_found = 0
    modules_run = []
    result_files = []
    
    # 1. Parse History
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
                total_ops = len(history)
                for record in history:
                    module = record.get("module", "unknown")
                    raw_data = record.get("raw_data", {})
                    status = raw_data.get("status", "unknown")
                    
                    if status == "success":
                        successful_modules += 1
                    elif status == "error":
                        failed_modules += 1
                        
                    entities_found += int(record.get("targets", 0))
                    if module not in modules_run:
                        modules_run.append(module)
        except Exception as e:
            if callback: callback(f"[!] Error reading history: {e}")

    # 2. List Result Files
    if os.path.exists(results_dir):
        try:
            files = [f for f in os.listdir(results_dir) if f.endswith(".json")]
            result_files = sorted(files, reverse=True)
        except Exception as e:
            if callback: callback(f"[!] Error listing results: {e}")

    if callback: callback(f"[+] Found {total_ops} operations and {len(result_files)} result files.")

    summary = {
        "total_ops": total_ops,
        "successful_modules": successful_modules,
        "failed_modules": failed_modules,
        "entities_found": entities_found,
        "modules_run": modules_run,
        "result_files": result_files
    }

    # Generate HTML report and notify operator
    result = create_result("dashboard", "success", data=summary)
    html_path = generate_report(result)
    if html_path:
        if callback: callback(f"[+] HTML report saved to: {html_path}")
    else:
        if callback: callback("[!] Warning: HTML report generation failed.")

    return result
