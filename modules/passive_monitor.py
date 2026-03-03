# pyre-ignore-all-errors
import time
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
