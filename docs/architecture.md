# 🏗️ CyberDeck OS - System Architecture

This document describes the high-level architecture and data flow of CyberDeck OS v2.0.

## Overview
CyberDeck OS is built on an **Event-Driven MVC** (Model-View-Controller) architecture, designed for extensibility and thread-safe operations on a Raspberry Pi or any Linux host.

## Core Components

### 1. View Layer (`mode_select/`)
- **MainWindow (`main_window.py`)**: The central GUI hub built with Tkinter. It subscribes to events and updates UI elements (Risk Score, Telemetry) in real-time.
- **ReportsWindow (`reports_window.py`)**: A dedicated interface for browsing and analyzing saved scan results.

### 2. Controller Layer (`core/controller.py`)
- The `SystemController` manages module execution. It spawns independent worker threads, handles data collation, and archives results to disk.

### 3. Model & State (`core/app_state.py`)
- A global singleton that maintains the system's "Source of Truth," including active threads, risk scores, and lockdown status.

### 4. Event Bus (`core/event_bus.py`)
- A lightweight Pub/Sub system that allows decoupled communication between the backend logic and the frontend UI.

## Data Flow
1. **Trigger**: User clicks a module in the UI.
2. **Dispatch**: The Controller spawns a thread for the selected module from the `modules/` directory.
3. **Execution**: The module performs its scan (Nmap, Bluetooth, etc.) and returns a standardized JSON payload.
4. **Collation**: The Controller wraps the payload into a `HistoryRecord`.
5. **Persistence**: The record is appended to `logs/history.json`.
6. **Notification**: The Controller publishes a `SCAN_COMPLETED` event.
7. **Update**: UI subscribers (Dashboard, Reports) receive the event and refresh themselves.
