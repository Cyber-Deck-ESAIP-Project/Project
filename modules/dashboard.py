import os
import sys
import json
from datetime import datetime
from typing import Any, Dict, List

# Add the project root to sys.path so 'utils' can be imported regardless of execution context
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.result_handler import create_result  # type: ignore
from utils.report_generator import generate_report  # type: ignore

BASELINE_FILENAME = "baseline.json"


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _normalize_status(value: Any) -> str:
    status = str(value or "unknown").strip().lower()
    if status in {"ok", "passed"}:
        return "success"
    if status in {"failed", "fail"}:
        return "error"
    return status or "unknown"


def _format_timestamp(value: Any) -> str:
    if not value:
        return "Unknown"

    ts_str = str(value).strip()
    if not ts_str:
        return "Unknown"

    parsed = None
    try:
        parsed = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(ts_str, fmt)
                break
            except Exception:
                continue

    if parsed is None:
        return ts_str
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


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


def _extract_error_count(payload: Dict[str, Any]) -> int:
    if "error_count" in payload:
        return _safe_int(payload.get("error_count"))
    errors = payload.get("errors", [])
    return len(errors) if isinstance(errors, list) else 0


def _extract_entities_found(payload: Dict[str, Any], targets: int) -> int:
    direct_keys = ("entities_found", "entity_count", "entities")
    for key in direct_keys:
        if key in payload:
            return _safe_int(payload.get(key))

    data_summary = payload.get("data_summary", {})
    if isinstance(data_summary, dict):
        for key in ("entities_found", "entity_count"):
            if key in data_summary:
                return _safe_int(data_summary.get(key))
        if "list_items" in data_summary:
            return _safe_int(data_summary.get("list_items"))

    return targets


def _make_result_summary(module: str, targets: Any, raw_data: Any) -> Dict[str, Any]:
    payload = raw_data if isinstance(raw_data, dict) else {}
    status = _normalize_status(payload.get("status", "unknown"))
    timestamp = payload.get("timestamp", "unknown")
    error_count = _extract_error_count(payload)
    payload_data = payload.get("data", {})
    data_summary = payload.get("data_summary")
    if not isinstance(data_summary, dict):
        data_summary = _summarize_payload_data(payload_data)

    target_count = _safe_int(targets)
    entities_found = _extract_entities_found(payload, target_count)

    return {
        "module": module,
        "status": status,
        "timestamp": timestamp,
        "targets": target_count,
        "error_count": error_count,
        "entities_found": entities_found,
        "has_data": isinstance(payload_data, dict) and bool(payload_data),
        "data_summary": data_summary,
    }


def _build_scan_row(content: Dict[str, Any], fallback_module: str) -> Dict[str, Any]:
    module_name = str(content.get("module") or fallback_module or "unknown")
    target_count = _safe_int(content.get("targets", content.get("target_count", 0)))
    status = _normalize_status(content.get("status", "unknown"))
    timestamp = _format_timestamp(content.get("timestamp"))
    error_count = _extract_error_count(content)

    data_summary = content.get("data_summary")
    if not isinstance(data_summary, dict):
        data_summary = _summarize_payload_data(content.get("data", {}))

    return {
        "module_name": module_name,
        "status": status,
        "timestamp": timestamp,
        "targets_found": target_count,
        "error_count": error_count,
        "entities_found": _extract_entities_found({**content, "data_summary": data_summary}, target_count),
    }


def _rebuild_breakdown_from_scan_results(scan_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    breakdown: Dict[str, Dict[str, int]] = {}
    for item in scan_results:
        module = item.get("module_name", "unknown")
        status = item.get("status", "unknown")
        if module not in breakdown:
            breakdown[module] = {"runs": 0, "success": 0, "error": 0, "entities": 0}
        breakdown[module]["runs"] += 1
        breakdown[module]["entities"] += _safe_int(item.get("entities_found"))
        if status == "success":
            breakdown[module]["success"] += 1
        elif status == "error":
            breakdown[module]["error"] += 1
    return breakdown


def _build_module_snapshot(scan_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    snapshot: Dict[str, Dict[str, Any]] = {}
    for row in scan_results:
        module = str(row.get("module_name", "unknown"))
        if module not in snapshot:
            snapshot[module] = {
                "runs": 0,
                "success": 0,
                "error": 0,
                "targets_found": 0,
                "error_count": 0,
                "entities_found": 0,
                "last_timestamp": "Unknown",
            }

        module_row = snapshot[module]
        module_row["runs"] += 1
        module_row["targets_found"] += _safe_int(row.get("targets_found"))
        module_row["error_count"] += _safe_int(row.get("error_count"))
        module_row["entities_found"] += _safe_int(row.get("entities_found"))

        status = _normalize_status(row.get("status", "unknown"))
        if status == "success":
            module_row["success"] += 1
        elif status == "error":
            module_row["error"] += 1

        ts = str(row.get("timestamp", "Unknown"))
        if ts and ts != "Unknown" and ts > str(module_row.get("last_timestamp", "Unknown")):
            module_row["last_timestamp"] = ts

    return snapshot


def _build_entity_totals_by_module(module_snapshot: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    return {
        module: _safe_int(stats.get("entities_found", 0))
        for module, stats in module_snapshot.items()
    }


def _build_baseline_payload(scan_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    module_snapshot = _build_module_snapshot(scan_results)
    return {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "module_snapshot": module_snapshot,
        "entity_totals_by_module": _build_entity_totals_by_module(module_snapshot),
        "total_entities": sum(_safe_int(stats.get("entities_found")) for stats in module_snapshot.values()),
        "total_rows": len(scan_results),
    }


def _write_baseline_file(baseline_path: str, baseline_payload: Dict[str, Any]) -> bool:
    try:
        with open(baseline_path, "w") as f:
            json.dump(baseline_payload, f, indent=4)
        return True
    except Exception:
        return False


def _load_baseline_file(baseline_path: str) -> Dict[str, Any]:
    with open(baseline_path, "r") as f:
        loaded = json.load(f)
    return loaded if isinstance(loaded, dict) else {}


def _compare_against_baseline(
    baseline_payload: Dict[str, Any], current_scan_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    current_snapshot = _build_module_snapshot(current_scan_results)
    current_entities = _build_entity_totals_by_module(current_snapshot)

    baseline_snapshot_raw = baseline_payload.get("module_snapshot", {})
    baseline_snapshot = baseline_snapshot_raw if isinstance(baseline_snapshot_raw, dict) else {}

    baseline_entities_raw = baseline_payload.get("entity_totals_by_module", {})
    baseline_entities = baseline_entities_raw if isinstance(baseline_entities_raw, dict) else {}

    all_entity_modules = sorted(set(current_entities.keys()) | set(baseline_entities.keys()))
    new_entities = []
    removed_entities = []

    for module in all_entity_modules:
        current_count = _safe_int(current_entities.get(module, 0))
        baseline_count = _safe_int(baseline_entities.get(module, 0))
        delta = current_count - baseline_count

        if delta > 0:
            new_entities.append({"module": module, "count": delta})
        elif delta < 0:
            removed_entities.append({"module": module, "count": abs(delta)})

    changed_module_results = []
    all_modules = sorted(set(current_snapshot.keys()) | set(baseline_snapshot.keys()))
    fields = ("runs", "success", "error", "targets_found", "error_count", "entities_found")
    for module in all_modules:
        before_raw = baseline_snapshot.get(module, {})
        after_raw = current_snapshot.get(module, {})
        before = before_raw if isinstance(before_raw, dict) else {}
        after = after_raw if isinstance(after_raw, dict) else {}

        changed_fields = {}
        for field in fields:
            previous = _safe_int(before.get(field, 0))
            current = _safe_int(after.get(field, 0))
            if previous != current:
                changed_fields[field] = {"previous": previous, "current": current}

        if changed_fields:
            changed_module_results.append({
                "module": module,
                "changes": changed_fields,
            })

    return {
        "baseline_created_at": str(baseline_payload.get("created_at", "unknown")),
        "new_entities": new_entities,
        "removed_entities": removed_entities,
        "changed_module_results": changed_module_results,
        "summary": {
            "new_entities_total": sum(_safe_int(item.get("count")) for item in new_entities),
            "removed_entities_total": sum(_safe_int(item.get("count")) for item in removed_entities),
            "changed_modules_total": len(changed_module_results),
        },
    }


def run(config, callback=None, **kwargs):
    if callback:
        callback("[*] Aggregating scan telemetry for executive summary...")

    results_dir = config.get("system", {}).get("results_dir", "results")
    history_file = "logs/history.json"
    baseline_path = os.path.join(results_dir, BASELINE_FILENAME)

    os.makedirs(results_dir, exist_ok=True)

    total_ops = 0
    successful_modules = 0
    failed_modules = 0
    entities_found = 0
    modules_run = []
    module_breakdown: Dict[str, Dict[str, int]] = {}
    result_files: List[str] = []

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
                status = _normalize_status(raw_data.get("status", "unknown") if isinstance(raw_data, dict) else "unknown")

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
            files = [
                f for f in os.listdir(results_dir)
                if f.endswith(".json") and f != BASELINE_FILENAME
            ]
            for f in files:
                if f not in result_files:
                    result_files.append(f)
        except Exception as e:
            if callback:
                callback(f"[!] Error listing results: {e}")

    result_files = sorted(result_files, reverse=True)


    # 3. Load and normalize result files for readable dashboard table rows
    scan_results: List[Dict[str, Any]] = []
    if os.path.exists(results_dir):
        for filename in result_files:
            filepath = os.path.join(results_dir, filename)
            try:
                with open(filepath, "r") as f:
                    content = json.load(f)
                    if not isinstance(content, dict):
                        continue
                    fallback_module = filename.rsplit(".", 1)[0]
                    scan_results.append(_build_scan_row(content, fallback_module))
            except Exception as e:
                if callback:
                    callback(f"[!] Could not parse result file {filename}: {e}")

    if total_ops == 0 and scan_results:
        total_ops = len(scan_results)
        successful_modules = sum(1 for row in scan_results if row.get("status") == "success")
        failed_modules = sum(1 for row in scan_results if row.get("status") == "error")
        entities_found = sum(_safe_int(row.get("entities_found")) for row in scan_results)
        modules_run = sorted({str(row.get("module_name", "unknown")) for row in scan_results})
        module_breakdown = _rebuild_breakdown_from_scan_results(scan_results)

    if callback:
        callback(f"[+] Aggregated {len(scan_results)} readable scan rows from {len(result_files)} result files.")

    baseline_comparison: Dict[str, Any]
    if not os.path.exists(baseline_path):
        baseline_payload = _build_baseline_payload(scan_results)
        persisted = _write_baseline_file(baseline_path, baseline_payload)
        baseline_comparison = {
            "baseline_status": "created" if persisted else "create_failed",
            "baseline_file": baseline_path,
            "baseline_created_at": baseline_payload.get("created_at", "unknown"),
            "new_entities": [],
            "removed_entities": [],
            "changed_module_results": [],
            "summary": {
                "new_entities_total": 0,
                "removed_entities_total": 0,
                "changed_modules_total": 0,
            },
        }
        if callback:
            callback("[+] Baseline initialized from current aggregated scan results.")
    else:
        try:
            loaded_baseline = _load_baseline_file(baseline_path)
            baseline_comparison = _compare_against_baseline(loaded_baseline, scan_results)
            baseline_comparison["baseline_status"] = "loaded"
            baseline_comparison["baseline_file"] = baseline_path
            baseline_comparison["compared_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if callback:
                callback("[+] Baseline comparison completed.")
        except Exception as e:
            baseline_comparison = {
                "baseline_status": "load_failed",
                "baseline_file": baseline_path,
                "error": str(e),
                "new_entities": [],
                "removed_entities": [],
                "changed_module_results": [],
                "summary": {
                    "new_entities_total": 0,
                    "removed_entities_total": 0,
                    "changed_modules_total": 0,
                },
            }
            if callback:
                callback(f"[!] Baseline comparison failed: {e}")

    summary = {
        "total_ops": total_ops,
        "successful_modules": successful_modules,
        "failed_modules": failed_modules,
        "entities_found": entities_found,
        "modules_run": modules_run,
        "module_breakdown": module_breakdown,
        "result_files": result_files,
        "scan_results": scan_results,
        "Baseline Comparison": baseline_comparison,
    }

    result = create_result("dashboard", "success", data=summary)
    html_path = generate_report(result)
    if html_path:

        result["data"]["html_report"] = html_path
        if callback:
            callback(f"[+] HTML report saved to: {html_path}")

    else:
        if callback:
            callback("[!] Warning: HTML report generation failed.")

    return result
