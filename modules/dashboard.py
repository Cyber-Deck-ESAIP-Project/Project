import os
import sys
import json
from datetime import datetime
from typing import Any, Dict

# Add the project root to sys.path so 'utils' can be imported regardless of execution context
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.result_handler import create_result  # type: ignore
from utils.report_generator import generate_report  # type: ignore


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _summarize_payload_data(data: Any) -> Dict[str, Any]:
    """Return a compact summary of payload data without exposing raw structures."""
    if not isinstance(data, dict) or not data:
        return {
            "fields": 0,
            "list_items": 0,
            "nested_objects": 0,
            "scalar_fields": 0,
        }

    list_items = 0
    nested_objects = 0
    scalar_fields = 0

    for value in data.values():
        if isinstance(value, list):
            list_items += len(value)
        elif isinstance(value, dict):
            nested_objects += 1
        else:
            scalar_fields += 1

    return {
        "fields": len(data),
        "list_items": list_items,
        "nested_objects": nested_objects,
        "scalar_fields": scalar_fields,
    }


def _make_result_summary(module: str, targets: Any, raw_data: Any) -> Dict[str, Any]:
    payload = raw_data if isinstance(raw_data, dict) else {}
    status = payload.get("status", "unknown")
    timestamp = payload.get("timestamp", "unknown")
    errors = payload.get("errors", [])
    payload_data = payload.get("data", {})

    return {
        "module": module,
        "status": status,
        "timestamp": timestamp,
        "targets": _safe_int(targets),
        "error_count": len(errors) if isinstance(errors, list) else 0,
        "has_data": isinstance(payload_data, dict) and bool(payload_data),
        "data_summary": _summarize_payload_data(payload_data),
    }


def run(config, callback=None, **kwargs):
    if callback:
        callback("[*] Aggregating scan telemetry for executive summary...")

    results_dir = config.get("system", {}).get("results_dir", "results")
    history_file = "logs/history.json"

    os.makedirs(results_dir, exist_ok=True)

    total_ops = 0
    successful_modules = 0
    failed_modules = 0
    entities_found = 0
    modules_run = []
    module_breakdown: Dict[str, Dict[str, int]] = {}
    result_files = []

    # 1. Parse history and generate readable summary files
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)

            total_ops = len(history)
            for record in history:
                module = record.get("module", "unknown")
                targets = record.get("targets", 0)
                raw_data = record.get("raw_data", {})
                status = raw_data.get("status", "unknown") if isinstance(raw_data, dict) else "unknown"

                if status == "success":
                    successful_modules += 1
                elif status == "error":
                    failed_modules += 1

                entities_found += _safe_int(targets)

                if module not in modules_run:
                    modules_run.append(module)

                if module not in module_breakdown:
                    module_breakdown[module] = {
                        "runs": 0,
                        "success": 0,
                        "error": 0,
                        "entities": 0,
                    }
                module_breakdown[module]["runs"] += 1
                module_breakdown[module]["entities"] += _safe_int(targets)
                if status == "success":
                    module_breakdown[module]["success"] += 1
                elif status == "error":
                    module_breakdown[module]["error"] += 1

                if isinstance(raw_data, dict) and "timestamp" in raw_data:
                    try:
                        ts = (
                            raw_data["timestamp"]
                            .split(".")[0]
                            .replace("T", "_")
                            .replace(":", "")
                            .replace("-", "")
                        )
                    except Exception:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

                    safe_module = module.lower().replace(" ", "_")
                    filename = f"{safe_module}_{ts}.json"
                    filepath = os.path.join(results_dir, filename)

                    if not os.path.exists(filepath):
                        summary_record = _make_result_summary(module, targets, raw_data)
                        with open(filepath, "w") as out_f:
                            json.dump(summary_record, out_f, indent=4)

                    if filename not in result_files:
                        result_files.append(filename)

        except Exception as e:
            if callback:
                callback(f"[!] Error reading history: {e}")

    # 2. Include orphaned json files in the results dir
    if os.path.exists(results_dir):
        try:
            files = [f for f in os.listdir(results_dir) if f.endswith(".json")]
            for f in files:
                if f not in result_files:
                    result_files.append(f)
        except Exception as e:
            if callback:
                callback(f"[!] Error listing results: {e}")

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

    if callback:
        callback(f"[+] Found {total_ops} operations and {len(result_files)} result files.")

    summary = {
        "total_ops": total_ops,
        "successful_modules": successful_modules,
        "failed_modules": failed_modules,
        "entities_found": entities_found,
        "modules_run": modules_run,
        "module_breakdown": module_breakdown,
        "result_files": result_files,
        
    }

    result = create_result("dashboard", "success", data=summary)
    html_path = generate_report(result)
    if html_path:

        result["data"]["html_report"] = html_path
        if callback: callback(f"[+] HTML report saved to: {html_path}")

        if callback:
            callback(f"[+] HTML report saved to: {html_path}")

    else:
        if callback:
            callback("[!] Warning: HTML report generation failed.")

    return result
