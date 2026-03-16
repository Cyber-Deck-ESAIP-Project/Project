import os
import sys
import time
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger  # type: ignore
from utils.result_handler import create_result  # type: ignore

logger = get_logger()

def _emit(callback, message):
    if callback:
        callback(message)

def _run_cmd(cmd, timeout=5):

    # Execute command safely without interactive stdin.

    return subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout
    )

def _path_exists(path):
    return os.path.exists(path)

def run(config, callback=None, **kwargs):
    module_name = "bluetooth_recon"
    logger.info(f"Running {module_name} module...")

    mod_config = config.get("modules", {}).get(module_name, {})
    interface = mod_config.get("interface", "hci0")
    scan_duration = int(mod_config.get("timeout", 8))

    if not mod_config.get("enabled", False):
        logger.warning(f"Module {module_name} is disabled in config.")
        return create_result(
            module_name,
            "error",
            errors=["Module disabled in config."]
        )

    _emit(callback, f"[{module_name}] Activating local Bluetooth adapter ({interface})...")

    # 1) Check bluetoothctl availability

    if shutil.which("bluetoothctl") is None:
        error_msg = "bluetoothctl is not installed or not available in PATH."
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])

    # 2) Check if kernel exposes Bluetooth subsystem

    _emit(callback, "[*] Checking kernel Bluetooth subsystem...")
    if not _path_exists("/sys/class/bluetooth"):
        error_msg = (
            "No Bluetooth subsystem detected in /sys/class/bluetooth. "
            "The system/VM does not currently expose any Bluetooth hardware."
        )
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(
            module_name,
            "error",
            errors=[
                error_msg,
                "Attach a physical USB Bluetooth dongle to the VM."
            ]
        )

    # 3) Check Bluetooth service status

    _emit(callback, "[*] Checking Bluetooth service status...")
    try:
        service_check = _run_cmd(["systemctl", "is-active", "bluetooth"], timeout=5)
    except subprocess.TimeoutExpired:
        error_msg = "Timed out while checking bluetooth service status."
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])
    except Exception as e:
        error_msg = f"Failed to check bluetooth service status: {str(e)}"
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])

    if service_check.returncode != 0 or service_check.stdout.strip() != "active":
        error_msg = (
            "Bluetooth service is not active. Start it manually with: "
            "sudo systemctl start bluetooth"
        )
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])

    # 4) Check available Bluetooth controllers

    _emit(callback, "[*] Checking available Bluetooth controllers...")
    try:
        ctl_list = _run_cmd(["bluetoothctl", "list"], timeout=5)
    except subprocess.TimeoutExpired:
        error_msg = "Timed out while listing Bluetooth controllers."
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])
    except Exception as e:
        error_msg = f"Failed to query Bluetooth controllers: {str(e)}"
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])

    if ctl_list.returncode != 0:
        error_msg = f"bluetoothctl list failed: {ctl_list.stderr.strip() or 'unknown error'}"
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])

    controllers_output = ctl_list.stdout.strip()
    if not controllers_output:
        error_msg = "No Bluetooth controller detected."
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(
            module_name,
            "error",
            errors=[
                error_msg,
                "This usually means no USB Bluetooth adapter is attached to the guest."
            ]
        )

    _emit(callback, f"[+] Controller detected:\n{controllers_output}")

    # 5) Power on controller

    _emit(callback, "[*] Powering on Bluetooth controller...")
    try:
        power_on = _run_cmd(["bluetoothctl", "power", "on"], timeout=5)
        if power_on.returncode != 0:
            logger.warning(f"Could not power on Bluetooth controller: {power_on.stderr.strip()}")
            _emit(callback, f"[!] Warning: Could not power on controller: {power_on.stderr.strip()}")
    except Exception as e:
        logger.warning(f"Error while powering on controller: {e}")
        _emit(callback, f"[!] Warning: Error while powering on controller: {e}")

    # 6) Start scan

    _emit(callback, "[*] Starting active Bluetooth scan...")
    try:
        scan_on = _run_cmd(["bluetoothctl", "scan", "on"], timeout=5)
        if scan_on.returncode != 0:
            logger.warning(f"Could not start active scan: {scan_on.stderr.strip()}")
            _emit(callback, f"[!] Warning: Could not start active scan: {scan_on.stderr.strip()}")
    except Exception as e:
        logger.warning(f"Error while starting scan: {e}")
        _emit(callback, f"[!] Warning: Error while starting scan: {e}")

    # Allow some discovery time
    wait_time = max(3, min(scan_duration, 10))
    _emit(callback, f"[*] Scanning for nearby Bluetooth devices for {wait_time}s...")
    time.sleep(wait_time)

    # 7) Read discovered devices

    _emit(callback, "[*] Querying discovered Bluetooth devices...")
    try:
        devices_proc = _run_cmd(["bluetoothctl", "devices"], timeout=5)
    except subprocess.TimeoutExpired:
        error_msg = "Timed out while reading discovered Bluetooth devices."
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        try:
            _run_cmd(["bluetoothctl", "scan", "off"], timeout=5)
        except Exception:
            pass
        return create_result(module_name, "error", errors=[error_msg])
    except Exception as e:
        error_msg = f"Failed to read discovered Bluetooth devices: {str(e)}"
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        try:
            _run_cmd(["bluetoothctl", "scan", "off"], timeout=5)
        except Exception:
            pass
        return create_result(module_name, "error", errors=[error_msg])

    # Stop scan
    try:
        _run_cmd(["bluetoothctl", "scan", "off"], timeout=5)
    except Exception:
        pass

    if devices_proc.returncode != 0:
        error_msg = f"bluetoothctl devices failed: {devices_proc.stderr.strip() or 'unknown error'}"
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])

    # 8) Parse results

    scan_results = []

    for line in devices_proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("Device "):
            parts = line.split(" ", 2)
            if len(parts) >= 3:
                mac = parts[1].strip()
                name = parts[2].strip()

                entry = {
                    "mac": mac,
                    "name": name,
                    "rssi": "N/A",
                    "class": "Unknown"
                }
                scan_results.append(entry)
                _emit(callback, f"[+] BT Device Discovered: {name} (MAC: {mac})")

    result_data = {
        "devices_found": len(scan_results),
        "scan_results": scan_results
    }

    _emit(callback, f"[+] Bluetooth spectrum sweep complete. Found {len(scan_results)} devices.")
    _emit(callback, "[+] Scan complete. Correlating threat signatures.")

    logger.info(f"{module_name} completed successfully with {len(scan_results)} devices found.")
    return create_result(module_name, "success", data=result_data)
