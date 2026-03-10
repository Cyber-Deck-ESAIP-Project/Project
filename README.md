# 🖧 CyberDeck OS v2.0 - Operations Manual

Welcome to the **Event-Driven MVC** evolution of CyberDeck OS. This guide covers setup, module usage, and the current executive reporting pipeline.

## Overview
CyberDeck OS is a modular security operations platform for real-time monitoring, active auditing, and post-scan analytics.

The current implementation adds a reporting workflow centered on:
- An Executive Dashboard for aggregated scan visibility
- Automatic baseline creation from the first aggregated scan set
- Baseline comparison on later runs to detect deltas
- Readable HTML reports instead of raw JSON telemetry dumps
- A web interface for browsing global and per-result reports

## Features
### Core Modules
1. Passive Monitor (`modules/passive_monitor.py`)
2. ARP Monitor (`modules/arp_monitor.py`)
3. LAN Scanner (`modules/lan_scan.py`)
4. 802.11 WiFi Audit (`modules/wifi_audit.py`)
5. Bluetooth Recon (`modules/bluetooth_recon.py`)
6. TLS Audit (`modules/tls_audit.py`)
7. Pentest Tools (`modules/pentest_tools.py`)
8. AI Anomaly Detection (`modules/anomaly_detect.py`)
9. Reports & Analytics (`modules/dashboard.py`)

### Executive Dashboard Features
- Aggregated operations summary across stored scan results
- Module-level breakdown (runs, success, error, entities)
- Normalized scan table for readable historical review
- Built-in baseline comparison block for change tracking
- Web route integration for dashboard and per-file report rendering

## Installation
1. Create and activate a virtual environment.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Start CyberDeck OS:
```bash
source .venv/bin/activate
sudo python3 launcher.py
```

`sudo` is recommended for modules requiring privileged network access (sniffing, scans, Bluetooth).

## Usage
1. Launch from project root:
```bash
source .venv/bin/activate
sudo python3 launcher.py
```
2. Run one or more security modules from the main interface.
3. The browser opens automatically. To go directly to reports:
   `http://127.0.0.1:5050/reports`
   *(Port is set by `config["dashboard"]["port"]`, default 5050)*
4. In the reports page:
- Use the global report view to see the Executive Dashboard.
- Open individual result reports from the available result file list.

## Dashboard & Reports
### Executive Dashboard Metrics
The global dashboard includes:
- Total Operations
- Successful Modules
- Failed Modules
- Entities Found
- Modules Run chips/list
- Module Breakdown table with:
  - Module
  - Runs
  - Success
  - Error
  - Entities
- Scan Results table with:
  - Module Name
  - Status
  - Timestamp
  - Targets Found
  - Error Count
  - Entities Found

### How Reports Are Generated
Report generation is driven by historical data and result files:
1. `modules/dashboard.py` reads `logs/history.json` when available.
2. It creates normalized per-run JSON summary files in `results/` if missing.
3. It also includes existing/orphaned `results/*.json` files (excluding `results/baseline.json`).
4. All result JSON records are normalized into readable dashboard rows.
5. `utils/report_generator.py` renders HTML reports from the normalized payload.
6. `/reports` rebuilds and serves the global dashboard view.
7. `/report/<filename>` renders an individual report from a stored `results/*.json` file.

## Baseline Detection
Baseline logic is implemented in `modules/dashboard.py` using `results/baseline.json`.

### Baseline Creation (First Dashboard Run)
- If `results/baseline.json` does not exist, CyberDeck creates it from the current aggregated scan results.
- Baseline payload includes:
  - `created_at`
  - `module_snapshot` (runs/success/error/targets/error_count/entities/last_timestamp)
  - `entity_totals_by_module`
  - `total_entities`
  - `total_rows`

### Baseline Comparison (Future Runs)
- If baseline exists, current aggregated results are compared against the stored baseline snapshot.
- Comparison output includes:
  - `new_entities` by module
  - `removed_entities` by module
  - `changed_module_results` with changed fields
  - summary totals for new, removed, and changed counts
- These values are rendered in the report under **Baseline Comparison**.

## Documentation
Detailed technical guides are available in `docs/`:
- [Architecture Overview](docs/architecture.md)
- [Installation Guide](docs/installation.md)
- [Development Workflow](docs/workflow.md)
- [User Guide](docs/user_guide.md)

## Deployment (Raspberry Pi)
To turn a Raspberry Pi into an autonomous CyberDeck:
1. `./scripts/setup_env.sh`
2. `./scripts/deploy.sh`

### End of Line.
*Happy Hunting.*
