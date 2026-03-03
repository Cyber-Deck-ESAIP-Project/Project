import json
import os
from datetime import datetime
from utils.logger import get_logger

logger = get_logger()

def create_result(module_name, status, data=None, errors=None):
    """
    Creates a standard result dictionary according to the contract.
    Valid statuses: 'success', 'error', 'partial'
    """
    if status not in ["success", "error", "partial"]:
        logger.warning(f"Invalid status '{status}' passed to create_result by {module_name}")
        status = "error"
        if errors is None:
            errors = ["Invalid status provided"]
        else:
            errors.append("Invalid status provided")

    return {
        "module": module_name,
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "data": data if data is not None else {},
        "errors": errors if errors is not None else []
    }

def save_result(result, results_dir="results"):
    """
    Saves a result dictionary to a JSON file.
    """
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    module_name = result.get("module", "unknown")
    filename = f"{module_name}_{timestamp}.json"
    filepath = os.path.join(results_dir, filename)

    try:
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=4)
        logger.info(f"Result saved to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save result: {e}")
        return None
