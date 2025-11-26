"""
Configuration Manager Module

Handles loading, saving, and managing application configuration.
Supports custom keyboard shortcuts for each gesture.
"""

import json
import os
from typing import Optional


class ConfigManager:
    """Configuration persistence and management."""
    
    VALID_GESTURES = {"left", "right", "up", "down"}
    
    # Default shortcuts for each gesture
    DEFAULT_CONFIG = {
        "gesture_shortcuts": {
            "left": "right",      # Left gesture -> Right arrow (next slide)
            "right": "left",      # Right gesture -> Left arrow (prev slide)
            "up": "none",         # Up gesture -> no action
            "down": "none"        # Down gesture -> no action
        },
        "confidence_threshold": 0.70,
        "cooldown_time": 2.0,
        "last_device_address": None,
        "auto_reconnect": True
    }
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize ConfigManager with the specified config file path."""
        self._config_path = config_path
        self._config = self._deep_copy(self.DEFAULT_CONFIG)
    
    def _deep_copy(self, obj):
        """Create a deep copy of a dict/list structure."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        return obj
    
    def load(self) -> dict:
        """Load configuration from file. Returns default config if file missing/corrupted."""
        if not os.path.exists(self._config_path):
            self._config = self._deep_copy(self.DEFAULT_CONFIG)
            return self._config
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            self._config = self._deep_copy(self.DEFAULT_CONFIG)
            if isinstance(loaded, dict):
                # Load gesture shortcuts
                if "gesture_shortcuts" in loaded and isinstance(loaded["gesture_shortcuts"], dict):
                    for gesture in self.VALID_GESTURES:
                        if gesture in loaded["gesture_shortcuts"]:
                            self._config["gesture_shortcuts"][gesture] = str(loaded["gesture_shortcuts"][gesture])
                
                # Legacy support: convert old gesture_mapping to shortcuts
                if "gesture_mapping" in loaded and isinstance(loaded["gesture_mapping"], dict):
                    legacy_map = {"next": "right", "previous": "left", "up": "up", "down": "down", "none": "none"}
                    for gesture in self.VALID_GESTURES:
                        if gesture in loaded["gesture_mapping"]:
                            old_action = loaded["gesture_mapping"][gesture]
                            if old_action in legacy_map:
                                self._config["gesture_shortcuts"][gesture] = legacy_map[old_action]
                
                if "confidence_threshold" in loaded:
                    threshold = loaded["confidence_threshold"]
                    if isinstance(threshold, (int, float)) and 0.0 <= threshold <= 1.0:
                        self._config["confidence_threshold"] = float(threshold)
                
                if "last_device_address" in loaded:
                    self._config["last_device_address"] = loaded["last_device_address"]
                
                if "auto_reconnect" in loaded:
                    self._config["auto_reconnect"] = bool(loaded["auto_reconnect"])
                
                if "cooldown_time" in loaded:
                    cooldown = loaded["cooldown_time"]
                    if isinstance(cooldown, (int, float)) and 0.5 <= cooldown <= 10.0:
                        self._config["cooldown_time"] = float(cooldown)
        
        except (json.JSONDecodeError, IOError):
            self._config = self._deep_copy(self.DEFAULT_CONFIG)
        
        return self._config
    
    def save(self, config: Optional[dict] = None) -> None:
        """Save configuration to file."""
        if config is not None:
            self._config = config
        
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def get_gesture_shortcuts(self) -> dict:
        """Get the current gesture-to-shortcut mapping."""
        return self._deep_copy(self._config["gesture_shortcuts"])
    
    def set_gesture_shortcut(self, gesture: str, shortcut: str) -> bool:
        """
        Set shortcut for a specific gesture.
        
        Args:
            gesture: The gesture name (left, right, up, down)
            shortcut: The shortcut string (e.g., "ctrl+up", "right", "none")
        
        Returns:
            True if set successfully, False if invalid gesture
        """
        if gesture not in self.VALID_GESTURES:
            return False
        self._config["gesture_shortcuts"][gesture] = shortcut
        return True
    
    def set_gesture_shortcuts(self, shortcuts: dict) -> bool:
        """
        Set all gesture shortcuts at once.
        
        Args:
            shortcuts: Dict mapping gestures to shortcut strings
        
        Returns:
            True if all valid, False otherwise
        """
        if not isinstance(shortcuts, dict):
            return False
        
        for gesture, shortcut in shortcuts.items():
            if gesture not in self.VALID_GESTURES:
                return False
        
        for gesture in self.VALID_GESTURES:
            if gesture in shortcuts:
                self._config["gesture_shortcuts"][gesture] = str(shortcuts[gesture])
        return True
    
    # Legacy compatibility methods
    def get_gesture_mapping(self) -> dict:
        """Legacy method - returns shortcuts as mapping."""
        return self.get_gesture_shortcuts()
    
    def set_gesture_mapping(self, mapping: dict) -> bool:
        """Legacy method - sets shortcuts from mapping."""
        return self.set_gesture_shortcuts(mapping)
    
    def validate_mapping(self, mapping: dict) -> bool:
        """Validate that a mapping contains only valid gestures."""
        if not isinstance(mapping, dict):
            return False
        for gesture in mapping.keys():
            if gesture not in self.VALID_GESTURES:
                return False
        return True
    
    def get_confidence_threshold(self) -> float:
        """Get the current confidence threshold."""
        return self._config["confidence_threshold"]
    
    def set_confidence_threshold(self, threshold: float) -> bool:
        """Set confidence threshold. Returns True if valid, False otherwise."""
        if not isinstance(threshold, (int, float)) or threshold < 0.0 or threshold > 1.0:
            return False
        self._config["confidence_threshold"] = float(threshold)
        return True
    
    def get_last_device_address(self) -> Optional[str]:
        """Get the last connected device address."""
        return self._config.get("last_device_address")
    
    def set_last_device_address(self, address: Optional[str]) -> None:
        """Set the last connected device address."""
        self._config["last_device_address"] = address
    
    def get_auto_reconnect(self) -> bool:
        """Get auto-reconnect setting."""
        return self._config.get("auto_reconnect", True)
    
    def set_auto_reconnect(self, enabled: bool) -> None:
        """Set auto-reconnect setting."""
        self._config["auto_reconnect"] = bool(enabled)
    
    def get_cooldown_time(self) -> float:
        """Get cooldown time between actions in seconds."""
        return self._config.get("cooldown_time", 2.0)
    
    def set_cooldown_time(self, seconds: float) -> bool:
        """Set cooldown time. Returns True if valid, False otherwise."""
        if not isinstance(seconds, (int, float)) or seconds < 0.5 or seconds > 10.0:
            return False
        self._config["cooldown_time"] = float(seconds)
        return True
    
    def get_config(self) -> dict:
        """Get the full configuration dictionary."""
        return self._deep_copy(self._config)
