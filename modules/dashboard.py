import os
import sys
import json
from datetime import datetime

# Add the project root to sys.path so 'utils' can be imported regardless of execution context
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.result_handler import create_result  # type: ignore
from utils.report_generator import generate_report  # type: ignore

def run(config, callback=None, **kwargs):
    if callback: callback("[*] Aggregating scan telemetry for executive summary...")
    
    results_dir = config.get("system", {}).get("results_dir", "results")
    history_file = "logs/history.json"
    
    os.makedirs(results_dir, exist_ok=True)
    
    total_ops = 0
    successful_modules = 0
    failed_modules = 0
    entities_found = 0
    modules_run = []
    result_files = []
    
    # 1. Parse History and Generate individual JSON files
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
                        
                    # Reconstruct missing result files for the viewer
                    # If this module run successfully generated raw data
                    if "timestamp" in raw_data:
                        # Extract a clean timestamp for the filename
                        try:
                            # format: 2026-03-06T14:23:47.430953
                            ts = raw_data["timestamp"].split('.')[0].replace('T', '_').replace(':', '').replace('-', '')
                        except:
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            
                        # Make filename safe
                        safe_module = module.lower().replace(" ", "_")
                        filename = f"{safe_module}_{ts}.json"
                        filepath = os.path.join(results_dir, filename)
                        
                        # Only write if it doesn't already exist
                        if not os.path.exists(filepath):
                            with open(filepath, 'w') as out_f:
                                json.dump(raw_data, out_f, indent=4)
                        
                        if filename not in result_files:
                            result_files.append(filename)
                            
        except Exception as e:
            if callback: callback(f"[!] Error reading history: {e}")

    # 2. Add any other orphaned json files in the results dir
    if os.path.exists(results_dir):
        try:
            files = [f for f in os.listdir(results_dir) if f.endswith(".json")]
            for f in files:
                if f not in result_files:
                    result_files.append(f)
        except Exception as e:
            if callback: callback(f"[!] Error listing results: {e}")
            
    # Sort files
    result_files = sorted(result_files, reverse=True)

    # 3. Load contents of result files to present them beautifully in the HTML report
    rich_results = []
    if os.path.exists(results_dir):
        for filename in result_files:
            filepath = os.path.join(results_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    content = json.load(f)
                    
                    # Try to parse timestamps cleanly
                    ts_str = content.get("timestamp", "Unknown Date")
                    if ts_str != "Unknown Date":
                        try:
                            # Try parsing typical ISO formats
                            if '.' in ts_str:
                                dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
                            else:
                                dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
                            clean_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            clean_ts = ts_str
                    else:
                        clean_ts = ts_str
                        
                    module_name = content.get("module", filename)
                    
                    # Extract the important nested data
                    actionable_data = content.get("data", {})
                    
                    rich_results.append({
                        "Module": module_name.upper(),
                        "Execution Time": clean_ts,
                        "Status": content.get("status", "Unknown"),
                        "Targets Found": content.get("targets", 0),
                        "Detailed Findings": actionable_data
                    })
            except Exception as e:
                rich_results.append({
                    "File": filename, 
                    "Error": f"Could not parse JSON content: {e}"
                })

    summary = {
        "Executive Overview": {
            "Total Operations": total_ops,
            "Successful Interactions": successful_modules,
            "Failed Interactions": failed_modules,
            "Distinct Target Entities": entities_found,
            "Modules Utilized": ", ".join(modules_run) if modules_run else "None"
        },
        "Detailed Module Telemetry": rich_results
    }

    # Generate HTML report and notify operator
    result = create_result("dashboard", "success", data=summary)
    html_path = generate_report(result)
    if html_path:
        result["data"]["html_report"] = html_path
        if callback: callback(f"[+] HTML report saved to: {html_path}")
    else:
        if callback: callback("[!] Warning: HTML report generation failed.")

    return result
