import tkinter as tk
from tkinter import scrolledtext, ttk
import json
import os
from typing import Any

class ReportsWindow:
    listbox: Any
    viewer: Any

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
        summary_text = f"Total Ops: {data.get('total_ops', 0)}  |  Entities Found: {data.get('entities_found', 0)}  |  Modules: {', '.join(data.get('modules_run', []))}"
        
        tk.Label(header, text="EXECUTIVE REPORT SUMMARY", bg=TERMINAL_BG, fg=TEXT_CYAN, font=("Courier", 14, "bold")).pack(pady=(10, 5))
        tk.Label(header, text=summary_text, bg=TERMINAL_BG, fg=TEXT_COLOR, font=("Courier", 10)).pack()

        # 2. Main Workspace (Paned)
        paned = tk.PanedWindow(self.window, orient=tk.HORIZONTAL, bg=BG_COLOR, bd=0, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 2a. Left Pane - Result Files List
        list_frame = tk.Frame(paned, bg=TERMINAL_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        paned.add(list_frame, width=300)

        tk.Label(list_frame, text="RESULT FILES", bg=TERMINAL_BG, fg=TEXT_ORANGE, font=("Courier", 11, "bold")).pack(pady=10)
        
        self.listbox = tk.Listbox(list_frame, bg=TERMINAL_BG, fg=TEXT_COLOR, font=("Courier", 10), 
                                 selectbackground=BORDER_COLOR, selectforeground=TEXT_CYAN, bd=0, highlightthickness=0)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        for f in data.get("result_files", []):
            self.listbox.insert(tk.END, f)
            
        self.listbox.bind("<<ListboxSelect>>", self._on_file_select)

        # 2b. Right Pane - Content Viewer
        viewer_frame = tk.Frame(paned, bg=TERMINAL_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        paned.add(viewer_frame)

        tk.Label(viewer_frame, text="FILE CONTENT", bg=TERMINAL_BG, fg=TEXT_GREEN, font=("Courier", 11, "bold")).pack(pady=10)
        
        self.viewer = scrolledtext.ScrolledText(viewer_frame, bg=TERMINAL_BG, fg=TEXT_GREEN, 
                                               font=("Courier", 10), insertbackground=TEXT_GREEN, 
                                               bd=0, highlightthickness=0)
        self.viewer.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.viewer.config(state=tk.DISABLED)

    def _on_file_select(self, event):
        selection = self.listbox.curselection()
        if not selection:
            return
            
        filename = self.listbox.get(selection[0])
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'r') as f:
                content = json.load(f)
                formatted_json = json.dumps(content, indent=4)
                
                self.viewer.config(state=tk.NORMAL)
                self.viewer.delete(1.0, tk.END)
                self.viewer.insert(tk.END, formatted_json)
                self.viewer.config(state=tk.DISABLED)
        except Exception as e:
            self.viewer.config(state=tk.NORMAL)
            self.viewer.delete(1.0, tk.END)
            self.viewer.insert(tk.END, f"Error loading file: {e}")
            self.viewer.config(state=tk.DISABLED)

def show_reports(parent, report_data):
    ReportsWindow(parent, report_data)
