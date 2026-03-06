import tkinter as tk
from tkinter import scrolledtext
import json
import os
import webbrowser
import subprocess
import sys

# Add project root to sys.path so we can import utils
if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.report_generator import generate_report # type: ignore
from typing import Any


class ReportsWindow:
    listbox: Any
    viewer: Any
    html_path: Any
    result_files: list[str]
    btn_html: Any

    def __init__(self, parent, report_data):
        self.window = tk.Toplevel(parent)
        self.window.title("CyberDeck // Executive Summary & Reports")
        self.window.geometry("900x700")
        self.window.configure(bg="#0D1117")

        self.report_data = report_data
        self.results_dir = "results"

        self._setup_ui()

    def _setup_ui(self):
        # Theme Constants
        BG_COLOR = "#0D1117"
        TERMINAL_BG = "#010409"
        TEXT_COLOR = "#C9D1D9"
        TEXT_CYAN = "#00FFFF"
        TEXT_GREEN = "#4ADE80"
        TEXT_ORANGE = "#F59E0B"
        BORDER_COLOR = "#30363D"

        # 1. Header Area
        header = tk.Frame(self.window, bg=TERMINAL_BG, height=80, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill=tk.X, padx=10, pady=10)
        header.pack_propagate(False)

        data = self.report_data.get("data", {})
<<<<<<< HEAD
        
        # Handle the new structured payload from dashboard
        if "Executive Overview" in data:
            exec_data = data["Executive Overview"]
            ops = exec_data.get("Total Operations", 0)
            entities = exec_data.get("Distinct Target Entities", 0)
            modules = exec_data.get("Modules Utilized", "")
            
            # The files are now embedded in the Detailed Module Telemetry or need to be extracted from the directory
            self.result_files = []
            if os.path.exists(self.results_dir):
                self.result_files = [f for f in os.listdir(self.results_dir) if f.endswith(".json")]
                self.result_files = sorted(self.result_files, reverse=True)
        else:
            # Fallback for old format
            ops = data.get('total_ops', 0)
            entities = data.get('entities_found', 0)
            modules = ', '.join(data.get('modules_run', []))
            self.result_files = data.get("result_files", [])

        summary_text = f"Total Ops: {ops}  |  Entities Found: {entities}  |  Modules: {modules}"
        
=======
        summary_text = (
            f"Total Ops: {data.get('total_ops', 0)}  |  "
            f"Entities Found: {data.get('entities_found', 0)}  |  "
            f"Modules: {', '.join(data.get('modules_run', []))}"
        )

>>>>>>> 4f6b9a2 (Improve dashboard UI: remove raw JSON output and display formatted summary)
        tk.Label(header, text="EXECUTIVE REPORT SUMMARY", bg=TERMINAL_BG, fg=TEXT_CYAN, font=("Courier", 14, "bold")).pack(pady=(10, 5))
        tk.Label(header, text=summary_text, bg=TERMINAL_BG, fg=TEXT_COLOR, font=("Courier", 10)).pack()

        self.html_path = data.get("html_report")
        
        # Always create the Open HTML button, we will disable/enable it based on selection/availability
        self.btn_html = tk.Button(header, text="[ OPEN HTML ]", bg=TERMINAL_BG, fg=TEXT_GREEN,
                            activebackground=TEXT_GREEN, activeforeground=TERMINAL_BG,
                            bd=0, highlightthickness=0, font=("Courier", 10, "bold"),
                            command=self._open_html_report)
        self.btn_html.place(relx=0.98, rely=0.5, anchor=tk.E)

        # 2. Main Workspace (Paned)
        paned = tk.PanedWindow(self.window, orient=tk.HORIZONTAL, bg=BG_COLOR, bd=0, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 2a. Left Pane - Result Files List
        list_frame = tk.Frame(paned, bg=TERMINAL_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        paned.add(list_frame, width=300)

        tk.Label(list_frame, text="RESULT FILES", bg=TERMINAL_BG, fg=TEXT_ORANGE, font=("Courier", 11, "bold")).pack(pady=10)

        self.listbox = tk.Listbox(
            list_frame,
            bg=TERMINAL_BG,
            fg=TEXT_COLOR,
            font=("Courier", 10),
            selectbackground=BORDER_COLOR,
            selectforeground=TEXT_CYAN,
            bd=0,
            highlightthickness=0,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
<<<<<<< HEAD
        
        for f in self.result_files:
=======

        for f in data.get("result_files", []):
>>>>>>> 4f6b9a2 (Improve dashboard UI: remove raw JSON output and display formatted summary)
            self.listbox.insert(tk.END, f)

        self.listbox.bind("<<ListboxSelect>>", self._on_file_select)

        # 2b. Right Pane - Content Viewer
        viewer_frame = tk.Frame(paned, bg=TERMINAL_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        paned.add(viewer_frame)

        tk.Label(viewer_frame, text="FILE SUMMARY", bg=TERMINAL_BG, fg=TEXT_GREEN, font=("Courier", 11, "bold")).pack(pady=10)

        self.viewer = scrolledtext.ScrolledText(
            viewer_frame,
            bg=TERMINAL_BG,
            fg=TEXT_GREEN,
            font=("Courier", 10),
            insertbackground=TEXT_GREEN,
            bd=0,
            highlightthickness=0,
        )
        self.viewer.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.viewer.config(state=tk.DISABLED)

    def _format_report_summary(self, content):
        module = content.get("module", "unknown")
        status = content.get("status", "unknown")
        timestamp = content.get("timestamp", "unknown")
        targets = content.get("targets", 0)
        data_summary = content.get("data_summary", {})
        errors = content.get("errors", [])

        lines = [
            f"Module: {module}",
            f"Status: {status}",
            f"Timestamp: {timestamp}",
            f"Targets: {targets}",
            "",
            "Data Overview:",
            f"- Field count: {data_summary.get('fields', 0)}",
            f"- List items total: {data_summary.get('list_items', 0)}",
            f"- Nested objects: {data_summary.get('nested_objects', 0)}",
            f"- Scalar fields: {data_summary.get('scalar_fields', 0)}",
        ]

        if isinstance(errors, list) and errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {err}" for err in errors)

        return "\n".join(lines)

    def _on_file_select(self, event):
        selection = self.listbox.curselection()
        if not selection:
            return

        filename = self.listbox.get(selection[0])
        filepath = os.path.join(self.results_dir, filename)

        try:
            with open(filepath, "r") as f:
                content = json.load(f)
                formatted_summary = self._format_report_summary(content)

                self.viewer.config(state=tk.NORMAL)
                self.viewer.delete(1.0, tk.END)
                self.viewer.insert(tk.END, formatted_summary)
                self.viewer.config(state=tk.DISABLED)
        except Exception as e:
            self.viewer.config(state=tk.NORMAL)
            self.viewer.delete(1.0, tk.END)
            self.viewer.insert(tk.END, f"Error loading file: {e}")
            self.viewer.config(state=tk.DISABLED)

<<<<<<< HEAD
    def _open_html_report(self):
        target_html = None
        
        # 1. Check if a specific JSON file is selected in the listbox
        selection = self.listbox.curselection()
        if selection:
            filename = self.listbox.get(selection[0])
            filepath = os.path.join(self.results_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        content = json.load(f)
                    
                    # Generate a fresh HTML report for this specific file
                    target_html = generate_report(content)
                except Exception as e:
                    print(f"Failed to generate specific report for {filename}: {e}")
        
        # 2. Fallback to the global dashboard HTML report
        if not target_html and hasattr(self, 'html_path') and self.html_path:
            target_html = self.html_path

        if target_html and os.path.exists(target_html):
            abs_path = os.path.abspath(target_html)
            
            # Since the app usually runs as sudo, running webbrowser directly might 
            # fail to launch the user's browser (e.g., Firefox blocks root execution).
            # We try to drop privileges to the SUDO_USER if available.
            sudo_user = os.environ.get("SUDO_USER")
            
            success = False
            if sudo_user:
                try:
                    # Try using xdg-open as the original user
                    subprocess.Popen(['sudo', '-u', sudo_user, 'xdg-open', abs_path], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    success = True
                except Exception as e:
                    print(f"Failed to open browser via sudo -u {sudo_user}: {e}")
            
            # Fallback to standard webbrowser module
            if not success:
                try:
                    webbrowser.open(f"file://{abs_path}")
                except Exception as e:
                    print(f"Failed to open browser via webbrowser: {e}")
=======
>>>>>>> 4f6b9a2 (Improve dashboard UI: remove raw JSON output and display formatted summary)

def show_reports(parent, report_data):
    ReportsWindow(parent, report_data)
