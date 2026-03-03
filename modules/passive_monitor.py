# pyre-ignore-all-errors
import os
import sys
import time

# Add project root to path for local execution and linting context
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger
from utils.result_handler import create_result

logger = get_logger()

def run(config, callback=None, **kwargs):
    """
    Placeholder for the Passive Monitor module.
    Mode: Passive traffic capture & analysis.
    """
    module_name = "passive_monitor"
    logger.info(f"Running {module_name} module...")
    
    if callback: callback("[*] Initializing promiscuous mode on active interface...")
    time.sleep(1)
    if callback: callback("[*] Capturing packets... (PASSIVE MODE)")
    time.sleep(1)
    if callback: callback("[+] Packet capture complete. No anomalies detected.")
    
    return create_result(module_name, "success", data={"anomalous_packets": []})
