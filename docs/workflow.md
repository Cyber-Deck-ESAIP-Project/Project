# Development Workflow

Guidelines for developing, testing, and contributing to CyberDeck OS v2.0.

---

## Branching Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, production-ready. All deployments pull from here. |
| `feature/<name>` | New modules or GUI features (e.g. `feature/dns-recon`) |
| `fix/<name>` | Bug fixes (e.g. `fix/wifi-parse-crash`) |
| `docs/<name>` | Documentation-only changes |

**Rules:**
- Never commit directly to `main` for significant changes.
- Create a feature branch, test, then merge via pull request.
- `scripts/deploy.sh` on the Pi pulls from `origin/main` — only merge when stable.

---

## Commit Conventions

Format: `<type>: <short description>`

| Type | When to use | Example |
|---|---|---|
| `feat` | New module or significant capability | `feat: Add TLS audit module` |
| `fix` | Bug fix | `fix: Handle missing interface in arp_monitor` |
| `docs` | Documentation only | `docs: Update architecture.md` |
| `refactor` | Code restructure, no behaviour change | `refactor: Extract result helpers to utils` |
| `chore` | Config, deps, scripts, CI | `chore: Remove unused Flask dependency` |

Keep commit messages under 72 characters for the subject line. Use the body for detail.

---

## Adding a New Module

Follow these steps exactly to add a module that works with the full controller/EventBus/RiskEngine pipeline.

### Step 1 — Create `modules/my_module.py`

```python
# pyre-ignore-all-errors
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger       # type: ignore
from utils.result_handler import create_result  # type: ignore

logger = get_logger()

def run(config: dict, callback=None, **kwargs) -> dict:
    module_name = "my_module"
    logger.info(f"Running {module_name}...")

    mod_config = config.get("modules", {}).get(module_name, {})
    if not mod_config.get("enabled", False):
        if callback: callback(f"[-] Module {module_name} disabled.")
        return create_result(module_name, "error", errors=["Module disabled in config."])

    target = kwargs.get("target", "")
    if callback: callback(f"[*] Starting {module_name} on target: {target}...")

    # --- YOUR SCAN LOGIC HERE ---
    scan_data = {"example_key": "example_value"}

    if callback: callback(f"[+] {module_name} complete.")
    return create_result(module_name, "success", data=scan_data)
```

### Step 2 — Add config entry

In `config/config.json` and `config/config.example.json`, add under `"modules"`:
```json
"my_module": {
    "enabled": true,
    "my_setting": "value"
}
```

### Step 3 — Wire into the web dashboard

In `mode_select/web_ui.py`:

1. Add the import at the top:
```python
from modules import ..., my_module
```

2. Add an entry to the `MODULES` dict:
```python
MODULES = {
    ...
    "My Module": my_module.run,
}
```

The dict key is the display name shown in the browser dashboard and stored in history records.

### Step 4 — (Optional) Handle entity count in controller

If your module returns a data key that should count toward the Entities telemetry counter, add a branch in `_extract_target_count()` in `core/controller.py`.

### Step 5 — (Optional) Feed anomaly detection

If your module produces data that should trigger anomaly rules, add a rule in `modules/anomaly_detect.py` that reads your module's output from `logs/history.json`.

### Verification checklist

- [ ] `run()` signature: `(config, callback=None, **kwargs)`
- [ ] Returns `create_result(module_name, status, data=..., errors=...)`
- [ ] Guards `if callback: callback(...)` before every console message
- [ ] Reads config via `config.get("modules", {}).get("my_module", {})`
- [ ] Checks `mod_config.get("enabled", False)` and returns early if False
- [ ] Module name string matches the JSON key in `config.json`
- [ ] Entry added to both `config/config.json` and `config/config.example.json`
- [ ] Import and entry added to `MODULES` dict in `mode_select/web_ui.py`

---

## Module Contract

Every module must implement exactly:

```python
def run(config: dict, callback=None, **kwargs) -> dict:
```

| Parameter | Type | Description |
|---|---|---|
| `config` | `dict` | Full config from `load_config()`. Read your slice with `config.get("modules", {}).get("name", {})`. |
| `callback` | callable or None | Call `callback("text")` to stream output to the GUI console. Always guard with `if callback:`. |
| `**kwargs` | varies | Common keys: `target` (str from GUI field), `target_ip`, `target_ports`. |

**Return value** — always use `create_result()`:

```python
return create_result(
    module_name="my_module",
    status="success",       # "success" | "error" | "partial"
    data={"key": "value"},  # scan payload
    errors=[]               # list of error strings
)
```

The resulting dict shape:
```python
{
    "module":    "my_module",
    "timestamp": "2026-03-05T12:00:00.000000",
    "status":    "success",
    "data":      {...},
    "errors":    []
}
```

The controller validates: `'module' in result and 'status' in result`.

---

## Testing a Module in Isolation

Run any module directly from the CLI without launching the full GUI:

```bash
source .venv/bin/activate
python3 menu.py
```

`menu.py` dynamically discovers all modules in `modules/`, validates the `run()` contract, and presents a numbered menu. Output streams to the terminal via `callback=print`.

Alternatively, test a single module directly:

```bash
python3 -c "
import json
from utils.config_loader import load_config
from modules import my_module
config = load_config('config/config.json')
result = my_module.run(config, callback=print)
print(result)
"
```

---

## Updating Dependencies

To add a new Python dependency:

1. Install it: `pip install package-name`
2. Add it to `requirements.txt` with a pinned version: `package-name==x.y.z`
3. Test that `scripts/setup_env.sh` still runs cleanly on a fresh environment.
4. Document it in `CLAUDE.md` under the Dependencies table.

Avoid adding packages that are only needed by one module if a stdlib alternative exists (e.g. `tls_audit` uses stdlib `ssl` instead of a third-party TLS library).

---

## Deployment (Raspberry Pi)

```bash
# On the Pi — pull latest and restart:
./scripts/deploy.sh

# Check service logs:
sudo journalctl -u cyberdeck.service -f
```

`deploy.sh` does: `git reset --hard origin/main` → `pip install -r requirements.txt` → `systemctl restart cyberdeck.service`.

---

## File Output During Development

| File | Path | Notes |
|---|---|---|
| Daily log | `logs/cyberdeck_YYYYMMDD.log` | All `logger.info/debug/error` calls go here |
| Session history | `logs/history.json` | Appended after every module run |
| Per-scan JSON | `results/<module>_<timestamp>.json` | One file per run |
| HTML report | `results/report_<timestamp>.html` | Generated by Reports module |

All files under `logs/` and `results/` are gitignored. Delete them freely during development.
