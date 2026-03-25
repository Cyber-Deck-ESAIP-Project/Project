# pyre-ignore-all-errors
import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add project root to path for local execution and linting context
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger  # type: ignore
from utils.result_handler import create_result  # type: ignore

logger = get_logger()

try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not installed. Hardware telemetry unavailable. Run: pip install psutil")

# WMI is optional, only for Windows
try:
    import wmi  # type: ignore
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


class HardwareTelemetry:
    """
    Collects hardware metrics including CPU, battery, thermal, and power data.
    Designed for portable deployment reliability monitoring.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sampling_interval = config.get("sampling_interval", 2)
        self.sample_count = config.get("sample_count", 30)
        self.cpu_temp_threshold = config.get("cpu_temp_threshold", 80)
        self.battery_threshold = config.get("battery_threshold", 20)
        self.alert_on_throttle = config.get("alert_on_throttle", True)
        self.collect_power_draw = config.get("collect_power_draw", True)
        
        # Data containers
        self.cpu_samples = []
        self.temp_samples = []
        self.battery_samples = []
        self.power_samples = []

    def collect_cpu_metrics(self) -> Optional[Dict[str, Any]]:
        """Collect CPU usage, frequency, and core information."""
        try:
            # Current CPU usage per core
            per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            overall_usage = psutil.cpu_percent(interval=0.1)
            
            # CPU frequency (current and max)
            freq = psutil.cpu_freq()
            
            # CPU count
            cpu_count = psutil.cpu_count(logical=True)
            
            return {
                "usage_percent": overall_usage,
                "usage_per_core": per_cpu,
                "current_freq_mhz": freq.current if freq else 0,
                "max_freq_mhz": freq.max if freq else 0,
                "min_freq_mhz": freq.min if freq else 0,
                "core_count": cpu_count,
            }
        except Exception as e:
            logger.error(f"Failed to collect CPU metrics: {e}")
            return None

    def collect_thermal_metrics(self) -> Optional[Dict[str, Any]]:
        """Collect CPU and system temperature data."""
        try:
            # sensors_temperatures() not available on Windows
            if not hasattr(psutil, 'sensors_temperatures'):
                logger.warning("Thermal sensors not available on this platform")
                return {"current_temp": 0, "thermal_zones": {}}
            
            temps = psutil.sensors_temperatures()
            
            if not temps:
                logger.warning("No thermal sensors detected on this system")
                return {"current_temp": 0, "thermal_zones": {}}
            
            # Extract primary CPU temp (usually called 'coretemp' on Linux or 'CPU Temperature' on Windows)
            primary_temp = 0
            all_zones = {}
            
            for sensor_name, readings in temps.items():
                all_zones[sensor_name] = []
                for reading in readings:
                    all_zones[sensor_name].append({
                        "label": reading.label,
                        "current": reading.current,
                        "high": reading.high,
                        "critical": reading.critical
                    })
                    # Assume first temp of first sensor is primary
                    if primary_temp == 0 and readings:
                        primary_temp = readings[0].current
            
            return {
                "current_temp": primary_temp,
                "thermal_zones": all_zones,
            }
        except Exception as e:
            logger.error(f"Failed to collect thermal metrics: {e}")
            return None

    def collect_battery_metrics(self) -> Optional[Dict[str, Any]]:
        """Collect battery charge, health, and discharge information."""
        try:
            battery = psutil.sensors_battery()
            
            if battery is None:
                logger.warning("No battery detected (plugged-in system or unsupported)")
                return {
                    "charge_percent": 100,
                    "status": "unavailable",
                    "health_percent": 0,
                    "time_remaining_minutes": 0,
                    "discharge_rate_w": 0,
                    "cycles": 0
                }
            
            # Map battery status
            status_map = {0: "high", 1: "low", 2: "critical", 3: "charging"}
            status = status_map.get(battery.percent, "unknown")
            
            return {
                "charge_percent": battery.percent,
                "status": status,
                "plugged_in": battery.power_plugged,
                "seconds_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNKNOWN else 0,
                "time_remaining_minutes": int(battery.secsleft / 60) if battery.secsleft != psutil.POWER_TIME_UNKNOWN else 0,
            }
        except Exception as e:
            logger.error(f"Failed to collect battery metrics: {e}")
            return None

    def collect_power_metrics(self) -> Optional[Dict[str, Any]]:
        """Collect power draw and efficiency metrics."""
        try:
            # Get process-level power info (heuristic)
            processes = psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])
            
            total_cpu_percent = 0
            process_count = 0
            high_drain_processes = []
            
            for proc in processes:
                try:
                    cpu_pct = proc.info['cpu_percent']
                    if cpu_pct and cpu_pct > 10:  # Processes using >10% CPU
                        high_drain_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cpu_percent": cpu_pct
                        })
                        total_cpu_percent += cpu_pct
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                process_count += 1
            
            # Heuristic: Estimate power draw from CPU usage and system metrics
            # Typical laptop: 15-25W at 50% load, gaming: 30-45W
            overall_cpu = psutil.cpu_percent(interval=0.1)
            estimated_power_w = (overall_cpu / 100) * 35  # Assume 35W max for portable deployment
            
            return {
                "estimated_power_w": round(estimated_power_w, 2),
                "overall_cpu_percent": overall_cpu,
                "high_drain_processes": high_drain_processes[:5],  # Top 5
            }
        except Exception as e:
            logger.error(f"Failed to collect power metrics: {e}")
            return None

    def detect_thermal_throttling(self) -> bool:
        """Detect if CPU is being thermally throttled."""
        try:
            # Check if current freq < max freq significantly
            freq = psutil.cpu_freq()
            if not freq:
                return False
            
            throttle_threshold = freq.max * 0.85  # Less than 85% max freq
            if freq.current < throttle_threshold:
                logger.warning(f"Potential thermal throttling detected: {freq.current}MHz < {throttle_threshold}MHz")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to detect thermal throttling: {e}")
            return False

    def calculate_risk_score(self, cpu_data: Dict, thermal_data: Dict, battery_data: Dict, power_data: Dict) -> Dict[str, Any]:
        """Calculate deployment readiness risk score."""
        risk_indicators = {
            "thermal": "OK",
            "battery": "OK",
            "power": "OK",
            "overall": 100  # Deployment readiness score (0-100)
        }
        
        # Thermal assessment
        if thermal_data and thermal_data.get("current_temp", 0) > self.cpu_temp_threshold:
            risk_indicators["thermal"] = "CRITICAL"
            risk_indicators["overall"] -= 40
        elif thermal_data and thermal_data.get("current_temp", 0) > (self.cpu_temp_threshold - 10):
            risk_indicators["thermal"] = "WARNING"
            risk_indicators["overall"] -= 15
        
        # Thermal throttling
        if self.detect_thermal_throttling() and self.alert_on_throttle:
            risk_indicators["thermal"] = "CRITICAL"
            risk_indicators["overall"] -= 30
        
        # Battery assessment
        if battery_data and battery_data.get("status") != "unavailable":
            charge = battery_data.get("charge_percent", 100)
            if charge < self.battery_threshold:
                risk_indicators["battery"] = "CRITICAL"
                risk_indicators["overall"] -= 35
            elif charge < 40:
                risk_indicators["battery"] = "WARNING"
                risk_indicators["overall"] -= 10
        
        # Power draw assessment
        if power_data and self.collect_power_draw:
            power_w = power_data.get("estimated_power_w", 0)
            if power_w > 30:  # High sustained draw
                risk_indicators["power"] = "WARNING"
                risk_indicators["overall"] -= 10
        
        # Ensure score is within bounds
        risk_indicators["overall"] = max(0, min(100, risk_indicators["overall"]))
        
        return risk_indicators

    def sample_metrics(self, callback=None) -> Dict[str, List[Any]]:
        """Collect multiple samples over time."""
        logger.info(f"Starting hardware telemetry sampling for {self.sample_count} samples...")
        
        if callback:
            callback(f"[*] Initializing hardware telemetry collection...")
            callback(f"[*] Sampling interval: {self.sampling_interval}s, Total samples: {self.sample_count}")
        
        for i in range(self.sample_count):
            if callback:
                callback(f"[>] Collecting sample {i + 1}/{self.sample_count}...")
            
            # Collect all metrics
            cpu_data = self.collect_cpu_metrics()
            if cpu_data:
                self.cpu_samples.append(cpu_data)
            
            thermal_data = self.collect_thermal_metrics()
            if thermal_data:
                self.temp_samples.append(thermal_data)
            
            battery_data = self.collect_battery_metrics()
            if battery_data:
                self.battery_samples.append(battery_data)
            
            if self.collect_power_draw:
                power_data = self.collect_power_metrics()
                if power_data:
                    self.power_samples.append(power_data)
            
            # Sleep between samples (except after the last one)
            if i < self.sample_count - 1:
                time.sleep(self.sampling_interval)
        
        if callback:
            callback(f"[+] Hardware telemetry sampling complete. Analyzing results...")
        
        return {
            "cpu": self.cpu_samples,
            "thermal": self.temp_samples,
            "battery": self.battery_samples,
            "power": self.power_samples,
        }

    def aggregate_samples(self, samples: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Aggregate collected samples into statistics."""
        aggregated = {}
        
        # Aggregate CPU data
        if samples["cpu"]:
            cpu_usages = [s.get("usage_percent", 0) for s in samples["cpu"]]
            aggregated["cpu"] = {
                "avg_usage_percent": round(sum(cpu_usages) / len(cpu_usages), 2),
                "max_usage_percent": round(max(cpu_usages), 2),
                "min_usage_percent": round(min(cpu_usages), 2),
                "freq_mhz": samples["cpu"][0].get("current_freq_mhz", 0) if samples["cpu"] else 0,
                "max_freq_mhz": samples["cpu"][0].get("max_freq_mhz", 0) if samples["cpu"] else 0,
                "core_count": samples["cpu"][0].get("core_count", 1) if samples["cpu"] else 1,
            }
        
        # Aggregate thermal data
        if samples["thermal"]:
            temps = [s.get("current_temp", 0) for s in samples["thermal"]]
            aggregated["thermal"] = {
                "avg_temp_c": round(sum(temps) / len(temps), 2),
                "max_temp_c": round(max(temps), 2),
                "min_temp_c": round(min(temps), 2),
                "current_temp_c": samples["thermal"][-1].get("current_temp", 0),  # Latest
                "thermal_zones": samples["thermal"][-1].get("thermal_zones", {}),
            }
        
        # Aggregate battery data
        if samples["battery"]:
            latest_battery = samples["battery"][-1]
            aggregated["battery"] = {
                "current_charge": latest_battery.get("charge_percent", 0),
                "status": latest_battery.get("status", "unknown"),
                "plugged_in": latest_battery.get("plugged_in", False),
                "time_remaining_minutes": latest_battery.get("time_remaining_minutes", 0),
            }
        
        # Aggregate power data
        if samples["power"]:
            power_draws = [s.get("estimated_power_w", 0) for s in samples["power"]]
            top_processes = samples["power"][-1].get("high_drain_processes", [])
            aggregated["power"] = {
                "avg_power_w": round(sum(power_draws) / len(power_draws), 2),
                "max_power_w": round(max(power_draws), 2),
                "min_power_w": round(min(power_draws), 2),
                "current_power_w": samples["power"][-1].get("estimated_power_w", 0),
                "high_drain_processes": top_processes,
            }
        
        return aggregated


def run(config: dict, callback=None, **kwargs) -> dict:
    """
    Standard module contract for CyberDeck OS.
    Collects hardware telemetry and returns structured result.
    """
    module_name = "hwmon_telemetry"
    logger.info(f"Running {module_name} module...")

    mod_config = config.get("modules", {}).get(module_name, {})

    if not mod_config.get("enabled", False):
        if callback:
            callback(f"[-] Module {module_name} disabled.")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    if not PSUTIL_AVAILABLE:
        msg = "psutil library not installed. Cannot collect hardware telemetry. Run: pip install psutil"
        if callback:
            callback(f"[!] {msg}")
        logger.error(msg)
        return create_result(module_name, "error", errors=[msg])

    try:
        # Initialize telemetry collector
        telemetry = HardwareTelemetry(mod_config)
        
        # Start sampling
        start_time = time.time()
        samples = telemetry.sample_metrics(callback=callback)
        elapsed_time = time.time() - start_time
        
        # Aggregate samples
        aggregated = telemetry.aggregate_samples(samples)
        
        # Calculate risk scores
        risk_assessment = telemetry.calculate_risk_score(
            aggregated.get("cpu", {}),
            aggregated.get("thermal", {}),
            aggregated.get("battery", {}),
            aggregated.get("power", {})
        )
        
        # Build result data
        result_data = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(elapsed_time, 2),
            "samples_collected": telemetry.sample_count,
            "sampling_interval_seconds": telemetry.sampling_interval,
            **aggregated,
            "risk_assessment": risk_assessment,
        }
        
        if callback:
            callback(f"\n[+] Hardware Telemetry Summary:")
            callback(f"    CPU Usage: {aggregated.get('cpu', {}).get('avg_usage_percent', 0)}% (avg)")
            callback(f"    Thermal: {aggregated.get('thermal', {}).get('avg_temp_c', 0)}°C (avg)")
            callback(f"    Battery: {aggregated.get('battery', {}).get('current_charge', 'N/A')}%")
            callback(f"    Power Draw: {aggregated.get('power', {}).get('avg_power_w', 0)}W (est.)")
            callback(f"    Deployment Readiness: {risk_assessment.get('overall', 0)}/100")
        
        logger.info(f"Hardware telemetry collection completed successfully")
        return create_result(module_name, "success", data=result_data)

    except Exception as e:
        error_msg = f"Hardware telemetry collection failed: {str(e)}"
        logger.error(error_msg)
        if callback:
            callback(f"[!] {error_msg}")
        return create_result(module_name, "error", errors=[error_msg])
