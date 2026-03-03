# pyre-ignore-all-errors
import os
import sys
import tkinter as tk
from tkinter import scrolledtext
import functools
from typing import Any, Optional, Callable, cast

# Add project root to sys.path for linter context
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.event_bus import event_bus
from core.app_state import state
from modules import lan_scan, wifi_audit, bluetooth_recon, pentest_tools, anomaly_detect, dashboard, passive_monitor
from mode_select.reports_window import show_reports

# Theme Constants
BG_COLOR = "#0D1117"
TERMINAL_BG = "#010409"
TEXT_COLOR = "#C9D1D9"
TEXT_CYAN = "#00FFFF"
TEXT_GREEN = "#4ADE80"
TEXT_RED = "#FF4444"
TEXT_ORANGE = "#F59E0B"
BORDER_COLOR = "#30363D"

class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CyberDeck_OS_v2.0 // Unified Command Center")
        self.root.geometry("1400x900")
        self.root.configure(bg=BG_COLOR)
        self.active_module: Optional[str] = cast(Optional[str], None)
        
        # Explicitly initialize attributes for IDE static analysis
        self.lbl_status: Any = None
        self.btn_modules: dict = {}
        self.console: Any = None
        self.lbl_ops: Any = None
        self.lbl_entities: Any = None
        self.lbl_risk: Any = None
        self.ent_target: Any = None

        self._setup_layout()
        self._setup_event_subscriptions()
        self._log_to_console(">> System Ready. CyberDeck Command Center Initialized.\n>> Awaiting deployment directive.")

    def _setup_layout(self):
        # 1. Header Strip
        header = tk.Frame(self.root, bg=TERMINAL_BG, height=60, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill=tk.X, padx=10, pady=10)
        header.pack_propagate(False)

        tk.Label(header, text="CYBERDECK OS v2.0", bg=TERMINAL_BG, fg=TEXT_CYAN, font=("Courier", 18, "bold")).pack(side=tk.LEFT, padx=20)
        
        self.lbl_status = tk.Label(header, text="[ SYSTEM IDLE ]", bg=TERMINAL_BG, fg=TEXT_GREEN, font=("Courier", 14, "bold"))
        self.lbl_status.pack(side=tk.RIGHT, padx=20)

        # 2. Main Workspace
        workspace = tk.Frame(self.root, bg=BG_COLOR)
        workspace.pack(fill=tk.BOTH, expand=True, padx=10)

        # 2a. Sidebar (Modules)
        sidebar = tk.Frame(workspace, bg=TERMINAL_BG, width=250, highlightbackground=BORDER_COLOR, highlightthickness=1)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, pady=(0, 10))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="DEPLOY MODULES", bg=TERMINAL_BG, fg=TEXT_CYAN, font=("Courier", 12, "bold")).pack(pady=15)

        modules = [
            ("Passive Monitor", passive_monitor.run),
            ("LAN Scanning", lan_scan.run),
            ("WiFi Audit", wifi_audit.run),
            ("Bluetooth Recon", bluetooth_recon.run),
            ("Pentest Toolkit", pentest_tools.run),
            ("Anomaly Detection", anomaly_detect.run),
            ("Reports", dashboard.run)
        ]

        for name, func in modules:
            btn = tk.Button(sidebar, text=f"[ {name.upper()} ]", bg=TERMINAL_BG, fg=TEXT_COLOR, 
                               activebackground=BG_COLOR, activeforeground=TEXT_CYAN,
                               bd=0, highlightthickness=0, font=("Courier", 11, "bold"),
                               command=(lambda n=name, f=func: lambda: self._execute_module(n, f))(name, func))
            btn.pack(fill=tk.X, padx=10, pady=5, ipady=10)
            self.btn_modules[name] = btn

        # 2b. Central Console
        console_frame = tk.Frame(workspace, bg=TERMINAL_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        console_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        tk.Label(console_frame, text="OPERATIONAL STREAM", bg=TERMINAL_BG, fg=TEXT_COLOR, font=("Courier", 10, "bold")).pack(pady=5)
        
        self.console = scrolledtext.ScrolledText(console_frame, bg=TERMINAL_BG, fg=TEXT_GREEN, 
                                                 font=("Courier", 11), insertbackground=TEXT_GREEN, 
                                                 bd=0, highlightthickness=0)
        self.console.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 2c. Info Pane (Right)
        info_pane = tk.Frame(workspace, bg=TERMINAL_BG, width=300, highlightbackground=BORDER_COLOR, highlightthickness=1)
        info_pane.pack(side=tk.LEFT, fill=tk.Y, pady=(0, 10))
        info_pane.pack_propagate(False)

        tk.Label(info_pane, text="TELEMETRY", bg=TERMINAL_BG, fg=TEXT_ORANGE, font=("Courier", 12, "bold")).pack(pady=15)
        
        self.lbl_ops = tk.Label(info_pane, text="Total Ops: 0", bg=TERMINAL_BG, fg=TEXT_COLOR, font=("Courier", 11))
        self.lbl_ops.pack(fill=tk.X, padx=10, pady=5)
        
        self.lbl_entities = tk.Label(info_pane, text="Entities: 0", bg=TERMINAL_BG, fg=TEXT_COLOR, font=("Courier", 11))
        self.lbl_entities.pack(fill=tk.X, padx=10, pady=5)
        
        self.lbl_risk = tk.Label(info_pane, text="Risk Level: 0", bg=TERMINAL_BG, fg=TEXT_GREEN, font=("Courier", 11, "bold"))
        self.lbl_risk.pack(fill=tk.X, padx=10, pady=20)

        # Footer Target Entry
        footer = tk.Frame(self.root, bg=TERMINAL_BG, height=40, highlightbackground=BORDER_COLOR, highlightthickness=1)
        footer.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(footer, text="TARGET_HOST:", bg=TERMINAL_BG, fg=TEXT_COLOR, font=("Courier", 11)).pack(side=tk.LEFT, padx=(20, 10))
        self.ent_target = tk.Entry(footer, bg=BG_COLOR, fg=TEXT_CYAN, font=("Courier", 11), insertbackground=TEXT_CYAN, bd=0)
        self.ent_target.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.ent_target.insert(0, "127.0.0.1")

    def _setup_event_subscriptions(self):
        event_bus.subscribe("MODULE_STARTED", self._on_module_start)
        event_bus.subscribe("MODULE_STOPPED", self._on_module_stop)
        event_bus.subscribe("RISK_UPDATED", self._on_risk_update)
        event_bus.subscribe("HISTORY_UPDATED", self._on_telemetry_update)
        event_bus.subscribe("SCAN_COMPLETED", self._on_scan_completed)

    def _log_to_console(self, msg: str):
        def _write(*args: Any):
            if self.console:
                self.console.config(state=tk.NORMAL)
                self.console.insert(tk.END, f"{msg}\n")
                self.console.see(tk.END)
                self.console.config(state=tk.DISABLED)
        try: self.root.after(0, _write)
        except: pass

    def _execute_module(self, name: str, func):
        target = self.ent_target.get() if self.ent_target else "127.0.0.1"
        from core.controller import controller
        controller.dispatch_module(name, func, callback=self._log_to_console, target=target)

    def _on_module_start(self, name: str):
        self.active_module = name
        def _update(*args):
            if self.lbl_status:
                self.lbl_status.config(text=f"[ SCANNING: {name.upper()} ]", fg=TEXT_ORANGE)
            for n, btn in self.btn_modules.items():
                btn.config(state=tk.DISABLED)
        self.root.after(0, _update)

    def _on_module_stop(self, name: str):
        if self.active_module == name:
            self.active_module = None
            def _update(*args):
                if self.lbl_status:
                    self.lbl_status.config(text="[ SYSTEM IDLE ]", fg=TEXT_GREEN)
                for n, btn in self.btn_modules.items():
                    btn.config(state=tk.NORMAL)
            self.root.after(0, _update)
            self._log_to_console(f">> Finished execution: {name}")

    def _on_risk_update(self, score: int):
        color = TEXT_GREEN if score < 40 else (TEXT_ORANGE if score < 75 else TEXT_RED)
        def _update(*args):
            if self.lbl_risk:
                self.lbl_risk.config(text=f"Risk Level: {score}", fg=color)
        self.root.after(0, _update)

    def _on_telemetry_update(self, telemetry: dict):
        ops = telemetry.get('total_operations', 0)
        entities = telemetry.get('entities_tracked', 0)
        def _update(*args):
            if self.lbl_ops:
                self.lbl_ops.config(text=f"Total Ops: {ops}")
            if self.lbl_entities:
                self.lbl_entities.config(text=f"Entities: {entities}")
        self.root.after(0, _update)

    def _on_scan_completed(self, history_record: dict):
        module_name = history_record.get("module")
        if module_name == "Reports":
            payload = history_record.get("raw_data", {})
            if payload.get("status") == "success":
                def _open_reports(*args):
                    show_reports(self.root, payload)
                self.root.after(0, _open_reports)

def start_ui():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()

