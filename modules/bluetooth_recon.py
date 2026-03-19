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

def _get_device_info(mac, timeout=5):
    """Query bluetoothctl info for RSSI and device class/icon."""
    try:
        result = _run_cmd(["bluetoothctl", "info", mac], timeout=timeout)
        if result.returncode != 0:
            return "N/A", "Unknown"
        rssi = "N/A"
        device_class = "Unknown"
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("RSSI:"):
                rssi = line.split(":", 1)[1].strip()
            elif line.startswith("Icon:"):
                device_class = line.split(":", 1)[1].strip().replace("-", " ").title()
            elif line.startswith("Class:") and device_class == "Unknown":
                device_class = line.split(":", 1)[1].strip()
        return rssi, device_class
    except Exception:
        return "N/A", "Unknown"

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

    # 5-7) Single bluetoothctl session: power on → scan on → wait → devices → scan off
    # Using one persistent session is critical — if bluetoothctl exits between
    # "scan on" and "devices", the daemon stops scanning and finds nothing.

    wait_time = max(3, scan_duration)
    _emit(callback, f"[*] Starting active Bluetooth scan for {wait_time}s (single session)...")

    bt_output = ""
    try:
        proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        proc.stdin.write("power on\n")
        proc.stdin.write("scan on\n")
        proc.stdin.flush()

        time.sleep(wait_time)

        proc.stdin.write("devices\n")
        proc.stdin.flush()
        time.sleep(0.5)

        proc.stdin.write("scan off\n")
        proc.stdin.write("quit\n")
        proc.stdin.flush()

        bt_output, _ = proc.communicate(timeout=wait_time + 15)
    except subprocess.TimeoutExpired:
        proc.kill()
        error_msg = "bluetoothctl session timed out during scan."
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])
    except Exception as e:
        error_msg = f"Failed to run bluetoothctl session: {str(e)}"
        logger.error(error_msg)
        _emit(callback, f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])

    # 8) Parse results — collect MACs from both scan events and devices list

    seen_macs = {}
    for line in bt_output.splitlines():
        line = line.strip()
        # "[NEW] Device AA:BB:CC:DD:EE:FF Name" — live discovery during scan
        # "Device AA:BB:CC:DD:EE:FF Name"        — from devices command
        for prefix in ("[NEW] Device ", "Device "):
            if prefix in line:
                after = line[line.index(prefix) + len(prefix):]
                parts = after.split(" ", 1)
                if len(parts) == 2:
                    mac, name = parts[0].strip(), parts[1].strip()
                    if mac not in seen_macs:
                        seen_macs[mac] = name
                break

    scan_results = []
    for mac, name in seen_macs.items():
        rssi, device_class = _get_device_info(mac)
        entry = {
            "mac": mac,
            "name": name,
            "rssi": rssi,
            "class": device_class
        }
        scan_results.append(entry)
        _emit(callback, f"[+] BT Device Discovered: {name} (MAC: {mac}, RSSI: {rssi}, Type: {device_class})")

    result_data = {
        "devices_found": len(scan_results),
        "scan_results": scan_results
    }

    _emit(callback, f"[+] Bluetooth spectrum sweep complete. Found {len(scan_results)} devices.")
    _emit(callback, "[+] Scan complete. Correlating threat signatures.")

    logger.info(f"{module_name} completed successfully with {len(scan_results)} devices found.")
    return create_result(module_name, "success", data=result_data)
