"""
GUI Module

Main window and settings dialog using tkinter.
Supports Chinese/English language switching and custom keyboard shortcuts.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
from datetime import datetime
from typing import Optional, List, Dict

from config_manager import ConfigManager
from gesture_handler import GestureHandler
from ble_manager import BLEManager


# Language strings
LANG_EN = {
    "title": "BLE Gesture Controller",
    "connection": "BLE Connection",
    "status": "Status:",
    "disconnected": "Disconnected",
    "connected": "Connected",
    "scanning": "Scanning...",
    "connecting": "Connecting...",
    "devices": "Devices:",
    "scan": "Scan (10s)",
    "auto_connect": "Auto Connect",
    "connect": "Connect",
    "disconnect": "Disconnect",
    "current_gesture": "Current Gesture",
    "confidence": "Confidence:",
    "shortcut_mapping": "Gesture → Shortcut Mapping",
    "left": "Left gesture:",
    "right": "Right gesture:",
    "up": "Up gesture:",
    "down": "Down gesture:",
    "confidence_threshold": "Confidence Threshold:",
    "cooldown": "Cooldown (seconds):",
    "save_settings": "Save Settings",
    "log": "Log",
    "lang_switch": "中文",
    "no_devices": "No devices found - try Auto Connect",
    "scan_complete": "Scan complete: Found {0} device(s)",
    "scan_none": "Scan complete: No devices found",
    "select_device": "Please select a device first",
    "settings_saved": "Settings saved successfully!",
    "auto_connect_fail": "Auto connect failed - device not found",
    "starting_scan": "Starting 10 second scan...",
    "auto_connecting": "Auto connecting (scanning for 15s)...",
    "shortcut_hint": "Examples: right, ctrl+up, alt+tab, shift+f5",
    "shortcut_help": "Shortcut Help",
    "help_text": """Shortcut Format:
• Single key: right, left, up, down, space, enter, f5
• With modifier: ctrl+right, alt+tab, shift+f5
• Multiple modifiers: ctrl+shift+s, ctrl+alt+delete

Available modifiers: ctrl, alt, shift, win
Available keys: up, down, left, right, enter, space, tab, esc,
backspace, delete, home, end, pageup, pagedown, f1-f12,
or any letter/number (a-z, 0-9)

Set to 'none' to disable a gesture.""",
}

LANG_ZH = {
    "title": "BLE 手势控制器",
    "connection": "BLE 连接",
    "status": "状态：",
    "disconnected": "未连接",
    "connected": "已连接",
    "scanning": "扫描中...",
    "connecting": "连接中...",
    "devices": "设备列表：",
    "scan": "扫描 (10秒)",
    "auto_connect": "自动连接",
    "connect": "连接",
    "disconnect": "断开",
    "current_gesture": "当前手势",
    "confidence": "置信度：",
    "shortcut_mapping": "手势 → 快捷键映射",
    "left": "向左手势：",
    "right": "向右手势：",
    "up": "向上手势：",
    "down": "向下手势：",
    "confidence_threshold": "置信度阈值：",
    "cooldown": "冷却时间（秒）：",
    "save_settings": "保存设置",
    "log": "日志",
    "lang_switch": "English",
    "no_devices": "未找到设备 - 请尝试自动连接",
    "scan_complete": "扫描完成：找到 {0} 个设备",
    "scan_none": "扫描完成：未找到设备",
    "select_device": "请先选择一个设备",
    "settings_saved": "设置保存成功！",
    "auto_connect_fail": "自动连接失败 - 未找到设备",
    "starting_scan": "开始扫描（10秒）...",
    "auto_connecting": "自动连接中（扫描15秒）...",
    "shortcut_hint": "示例: right, ctrl+up, alt+tab, shift+f5",
    "shortcut_help": "快捷键帮助",
    "help_text": """快捷键格式：
• 单个按键: right, left, up, down, space, enter, f5
• 带修饰键: ctrl+right, alt+tab, shift+f5
• 多个修饰键: ctrl+shift+s, ctrl+alt+delete

可用修饰键: ctrl, alt, shift, win
可用按键: up, down, left, right, enter, space, tab, esc,
backspace, delete, home, end, pageup, pagedown, f1-f12,
或任意字母/数字 (a-z, 0-9)

设置为 'none' 可禁用该手势。""",
}


class MainWindow:
    """Main application window using tkinter."""
    
    def __init__(self, config_manager: ConfigManager, gesture_handler: GestureHandler, ble_manager: BLEManager):
        """Initialize the main window."""
        self._config = config_manager
        self._gesture_handler = gesture_handler
        self._ble_manager = ble_manager
        
        self._root = tk.Tk()
        self._root.geometry("550x750")
        self._root.resizable(True, True)
        
        self._devices: List = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Language setting
        self._lang = LANG_EN
        self._is_english = True
        
        self._setup_ui()
        self._setup_callbacks()
        self._update_language()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_frame = ttk.Frame(self._root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Language Switch Button ===
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 5))
        
        self._lang_btn = ttk.Button(lang_frame, text="中文", command=self._toggle_language)
        self._lang_btn.pack(side=tk.RIGHT)
        
        self._help_btn = ttk.Button(lang_frame, text="?", width=3, command=self._show_help)
        self._help_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # === Connection Section ===
        self._conn_frame = ttk.LabelFrame(main_frame, text="BLE Connection", padding="5")
        self._conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        status_frame = ttk.Frame(self._conn_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        self._status_text_label = ttk.Label(status_frame, text="Status:")
        self._status_text_label.pack(side=tk.LEFT)
        self._status_label = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self._status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self._devices_label = ttk.Label(self._conn_frame, text="Devices:")
        self._devices_label.pack(anchor=tk.W)
        
        device_frame = ttk.Frame(self._conn_frame)
        device_frame.pack(fill=tk.X, pady=(0, 5))
        
        self._device_listbox = tk.Listbox(device_frame, height=3)
        self._device_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        scrollbar = ttk.Scrollbar(device_frame, orient=tk.VERTICAL, command=self._device_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._device_listbox.config(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(self._conn_frame)
        btn_frame.pack(fill=tk.X)
        
        self._scan_btn = ttk.Button(btn_frame, text="Scan (10s)", command=self._on_scan)
        self._scan_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self._auto_connect_btn = ttk.Button(btn_frame, text="Auto Connect", command=self._on_auto_connect)
        self._auto_connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self._connect_btn = ttk.Button(btn_frame, text="Connect", command=self._on_connect)
        self._connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self._disconnect_btn = ttk.Button(btn_frame, text="Disconnect", command=self._on_disconnect, state=tk.DISABLED)
        self._disconnect_btn.pack(side=tk.LEFT)
        
        # === Gesture Display Section ===
        self._gesture_frame = ttk.LabelFrame(main_frame, text="Current Gesture", padding="5")
        self._gesture_frame.pack(fill=tk.X, pady=(0, 10))
        
        self._gesture_label = ttk.Label(self._gesture_frame, text="--", font=("Arial", 24, "bold"))
        self._gesture_label.pack()
        
        self._confidence_label = ttk.Label(self._gesture_frame, text="Confidence: --")
        self._confidence_label.pack()
        
        self._action_label = ttk.Label(self._gesture_frame, text="", foreground="green", font=("Arial", 12))
        self._action_label.pack()
        
        # === Shortcut Mapping Section ===
        self._settings_frame = ttk.LabelFrame(main_frame, text="Gesture → Shortcut Mapping", padding="5")
        self._settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Hint label
        self._hint_label = ttk.Label(self._settings_frame, text="Examples: right, ctrl+up, alt+tab", 
                                     foreground="gray", font=("Arial", 9))
        self._hint_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Shortcut entries
        self._shortcut_vars = {}
        self._shortcut_labels = {}
        
        shortcuts = self._config.get_gesture_shortcuts()
        gesture_labels = {"left": "Left gesture:", "right": "Right gesture:", 
                         "up": "Up gesture:", "down": "Down gesture:"}
        
        for gesture in ["left", "right", "up", "down"]:
            row = ttk.Frame(self._settings_frame)
            row.pack(fill=tk.X, pady=2)
            
            label = ttk.Label(row, text=gesture_labels[gesture], width=14)
            label.pack(side=tk.LEFT)
            self._shortcut_labels[gesture] = label
            
            var = tk.StringVar(value=shortcuts.get(gesture, "none"))
            self._shortcut_vars[gesture] = var
            
            entry = ttk.Entry(row, textvariable=var, width=25)
            entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Threshold slider
        threshold_frame = ttk.Frame(self._settings_frame)
        threshold_frame.pack(fill=tk.X, pady=(10, 0))
        
        self._threshold_text_label = ttk.Label(threshold_frame, text="Confidence Threshold:")
        self._threshold_text_label.pack(side=tk.LEFT)
        
        self._threshold_var = tk.DoubleVar(value=self._config.get_confidence_threshold())
        self._threshold_label = ttk.Label(threshold_frame, text=f"{self._threshold_var.get():.2f}")
        self._threshold_label.pack(side=tk.RIGHT)
        
        self._threshold_slider = ttk.Scale(
            threshold_frame, from_=0.5, to=1.0, 
            variable=self._threshold_var, orient=tk.HORIZONTAL,
            command=self._on_threshold_change
        )
        self._threshold_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Cooldown slider
        cooldown_frame = ttk.Frame(self._settings_frame)
        cooldown_frame.pack(fill=tk.X, pady=(10, 0))
        
        self._cooldown_text_label = ttk.Label(cooldown_frame, text="Cooldown (seconds):")
        self._cooldown_text_label.pack(side=tk.LEFT)
        
        self._cooldown_var = tk.DoubleVar(value=self._config.get_cooldown_time())
        self._cooldown_label = ttk.Label(cooldown_frame, text=f"{self._cooldown_var.get():.1f}s")
        self._cooldown_label.pack(side=tk.RIGHT)
        
        self._cooldown_slider = ttk.Scale(
            cooldown_frame, from_=0.5, to=5.0, 
            variable=self._cooldown_var, orient=tk.HORIZONTAL,
            command=self._on_cooldown_change
        )
        self._cooldown_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Save button
        self._save_btn = ttk.Button(self._settings_frame, text="Save Settings", command=self._on_save_settings)
        self._save_btn.pack(pady=(10, 0))
        
        # === Log Section ===
        self._log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        self._log_frame.pack(fill=tk.BOTH, expand=True)
        
        self._log_text = tk.Text(self._log_frame, height=8, state=tk.DISABLED)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = ttk.Scrollbar(self._log_frame, orient=tk.VERTICAL, command=self._log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.config(yscrollcommand=log_scrollbar.set)
    
    def _show_help(self) -> None:
        """Show shortcut help dialog."""
        messagebox.showinfo(self._lang["shortcut_help"], self._lang["help_text"])
    
    def _toggle_language(self) -> None:
        """Toggle between English and Chinese."""
        self._is_english = not self._is_english
        self._lang = LANG_EN if self._is_english else LANG_ZH
        self._update_language()
    
    def _update_language(self) -> None:
        """Update all UI text to current language."""
        self._root.title(self._lang["title"])
        self._lang_btn.config(text=self._lang["lang_switch"])
        
        self._conn_frame.config(text=self._lang["connection"])
        self._status_text_label.config(text=self._lang["status"])
        self._devices_label.config(text=self._lang["devices"])
        self._scan_btn.config(text=self._lang["scan"])
        self._auto_connect_btn.config(text=self._lang["auto_connect"])
        self._connect_btn.config(text=self._lang["connect"])
        self._disconnect_btn.config(text=self._lang["disconnect"])
        
        self._gesture_frame.config(text=self._lang["current_gesture"])
        
        self._settings_frame.config(text=self._lang["shortcut_mapping"])
        self._hint_label.config(text=self._lang["shortcut_hint"])
        self._threshold_text_label.config(text=self._lang["confidence_threshold"])
        self._cooldown_text_label.config(text=self._lang["cooldown"])
        self._save_btn.config(text=self._lang["save_settings"])
        
        gesture_labels = {"left": self._lang["left"], "right": self._lang["right"],
                        "up": self._lang["up"], "down": self._lang["down"]}
        for gesture in ["left", "right", "up", "down"]:
            self._shortcut_labels[gesture].config(text=gesture_labels[gesture])
        
        self._log_frame.config(text=self._lang["log"])
    
    def _setup_callbacks(self) -> None:
        """Set up callbacks for BLE and gesture events."""
        self._ble_manager.set_status_callback(self._on_status_change)
        self._ble_manager.set_gesture_callback(self._on_gesture_received)
        self._gesture_handler.set_action_callback(self._on_action_triggered)
    
    def _on_status_change(self, status: str) -> None:
        """Handle BLE status change."""
        self._root.after(0, lambda: self._update_status(status))
    
    def _update_status(self, status: str) -> None:
        """Update status label."""
        if status == "Connected":
            display_status = self._lang["connected"]
            self._status_label.config(foreground="green")
            self._connect_btn.config(state=tk.DISABLED)
            self._disconnect_btn.config(state=tk.NORMAL)
            self._scan_btn.config(state=tk.DISABLED)
            self._auto_connect_btn.config(state=tk.DISABLED)
        elif "Scanning" in status or "Reconnecting" in status or "Connecting" in status:
            display_status = self._lang["scanning"] if "Scanning" in status else self._lang["connecting"]
            self._status_label.config(foreground="orange")
            self._scan_btn.config(state=tk.DISABLED)
            self._auto_connect_btn.config(state=tk.DISABLED)
            self._connect_btn.config(state=tk.DISABLED)
        else:
            display_status = self._lang["disconnected"]
            self._status_label.config(foreground="red")
            self._connect_btn.config(state=tk.NORMAL)
            self._disconnect_btn.config(state=tk.DISABLED)
            self._scan_btn.config(state=tk.NORMAL)
            self._auto_connect_btn.config(state=tk.NORMAL)
        
        self._status_label.config(text=display_status)
        self.add_log_entry(f"{self._lang['status']} {display_status}")
    
    def _on_gesture_received(self, gesture: str, confidence: float) -> None:
        """Handle gesture received from BLE."""
        self._root.after(0, lambda: self._update_gesture(gesture, confidence))
        self._gesture_handler.process_gesture(gesture, confidence)
    
    def _update_gesture(self, gesture: str, confidence: float) -> None:
        """Update gesture display."""
        self._gesture_label.config(text=gesture.upper())
        self._confidence_label.config(text=f"{self._lang['confidence']} {confidence:.2%}")
    
    def _on_action_triggered(self, gesture: str, shortcut: str) -> None:
        """Handle action triggered by gesture."""
        self._root.after(0, lambda: self._show_action(gesture, shortcut))
    
    def _show_action(self, gesture: str, shortcut: str) -> None:
        """Show action feedback."""
        self._action_label.config(text=f"→ {shortcut.upper()}")
        self.add_log_entry(f"'{gesture}' → [{shortcut}]")
        self._root.after(1500, lambda: self._action_label.config(text=""))
    
    def _on_threshold_change(self, value: str) -> None:
        """Handle threshold slider change."""
        val = float(value)
        self._threshold_label.config(text=f"{val:.2f}")
    
    def _on_cooldown_change(self, value: str) -> None:
        """Handle cooldown slider change."""
        val = float(value)
        self._cooldown_label.config(text=f"{val:.1f}s")
        self._gesture_handler.set_cooldown_time(val)
    
    def _on_save_settings(self) -> None:
        """Save current settings."""
        shortcuts = {}
        for gesture, var in self._shortcut_vars.items():
            shortcuts[gesture] = var.get().strip().lower()
        
        self._config.set_gesture_shortcuts(shortcuts)
        self._config.set_confidence_threshold(self._threshold_var.get())
        self._config.set_cooldown_time(self._cooldown_var.get())
        self._config.save()
        
        self._gesture_handler.set_cooldown_time(self._cooldown_var.get())
        
        self.add_log_entry(f"{self._lang['save_settings']}")
        messagebox.showinfo(self._lang["save_settings"], self._lang["settings_saved"])
    
    def _on_scan(self) -> None:
        """Handle scan button click."""
        if self._loop:
            self.add_log_entry(self._lang["starting_scan"])
            asyncio.run_coroutine_threadsafe(self._do_scan(), self._loop)
    
    async def _do_scan(self) -> None:
        """Perform BLE scan."""
        self._devices = await self._ble_manager.scan_devices(timeout=10.0)
        self._root.after(0, self._update_device_list)
    
    def _on_auto_connect(self) -> None:
        """Handle auto connect button click."""
        if self._loop:
            self.add_log_entry(self._lang["auto_connecting"])
            asyncio.run_coroutine_threadsafe(self._do_auto_connect(), self._loop)
    
    async def _do_auto_connect(self) -> None:
        """Scan for target device and connect automatically."""
        success = await self._ble_manager.scan_and_connect(timeout=15.0)
        if not success:
            self._root.after(0, lambda: self.add_log_entry(self._lang["auto_connect_fail"]))
    
    def _update_device_list(self) -> None:
        """Update device listbox."""
        self._device_listbox.delete(0, tk.END)
        
        if not self._devices:
            self._device_listbox.insert(tk.END, self._lang["no_devices"])
            self.add_log_entry(self._lang["scan_none"])
        else:
            for device in self._devices:
                self._device_listbox.insert(tk.END, f"{device.name} ({device.address})")
            self.add_log_entry(self._lang["scan_complete"].format(len(self._devices)))
    
    def _on_connect(self) -> None:
        """Handle connect button click."""
        selection = self._device_listbox.curselection()
        if not selection:
            messagebox.showwarning(self._lang["connect"], self._lang["select_device"])
            return
        
        idx = selection[0]
        if idx < len(self._devices):
            device = self._devices[idx]
            if self._loop:
                asyncio.run_coroutine_threadsafe(self._ble_manager.connect(device.address), self._loop)
    
    def _on_disconnect(self) -> None:
        """Handle disconnect button click."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._ble_manager.disconnect(), self._loop)
    
    def add_log_entry(self, message: str) -> None:
        """Add an entry to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        
        self._log_text.config(state=tk.NORMAL)
        self._log_text.insert(tk.END, entry)
        self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)
    
    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio event loop for async operations."""
        self._loop = loop
    
    def run(self) -> None:
        """Start the main window event loop."""
        self._root.mainloop()
    
    def get_root(self) -> tk.Tk:
        """Get the root Tk instance."""
        return self._root
