"""
Gesture Handler Module

Maps gestures to custom keyboard shortcuts and triggers them.
Supports modifier keys (Ctrl, Alt, Shift) + any key combinations.
"""

import time
from typing import Optional, Callable, List, Dict
from pynput.keyboard import Key, Controller, KeyCode

from config_manager import ConfigManager


class GestureHandler:
    """Maps gestures to custom keyboard shortcuts."""
    
    # Map of key names to pynput Key objects
    SPECIAL_KEYS = {
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        "enter": Key.enter,
        "space": Key.space,
        "tab": Key.tab,
        "esc": Key.esc,
        "backspace": Key.backspace,
        "delete": Key.delete,
        "home": Key.home,
        "end": Key.end,
        "pageup": Key.page_up,
        "pagedown": Key.page_down,
        "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
        "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
        "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
    }
    
    MODIFIER_KEYS = {
        "ctrl": Key.ctrl_l,
        "alt": Key.alt_l,
        "shift": Key.shift_l,
        "win": Key.cmd,
    }
    
    # Default cooldown time in seconds
    DEFAULT_COOLDOWN = 2.0
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize GestureHandler with a ConfigManager instance."""
        self._config = config_manager
        self._keyboard = Controller()
        self._action_callback: Optional[Callable[[str, str], None]] = None
        
        # Cooldown time (can be configured)
        self._cooldown_time = self._config.get_cooldown_time()
        
        # State for deduplication
        self._last_action_time: float = 0.0
    
    def set_action_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set a callback to be invoked when an action is triggered."""
        self._action_callback = callback
    
    def set_cooldown_time(self, seconds: float) -> None:
        """Set the cooldown time between actions."""
        self._cooldown_time = max(0.5, min(seconds, 10.0))
    
    def get_cooldown_time(self) -> float:
        """Get the current cooldown time."""
        return self._cooldown_time
    
    def parse_shortcut(self, shortcut_str: str) -> tuple:
        """
        Parse a shortcut string like "ctrl+shift+a" into modifiers and key.
        
        Args:
            shortcut_str: Shortcut string (e.g., "ctrl+up", "alt+tab", "a")
        
        Returns:
            Tuple of (modifiers_list, main_key) or ([], None) if invalid
        """
        if not shortcut_str or shortcut_str.lower() == "none":
            return [], None
        
        parts = [p.strip().lower() for p in shortcut_str.split("+")]
        modifiers = []
        main_key = None
        
        for part in parts:
            if part in self.MODIFIER_KEYS:
                modifiers.append(self.MODIFIER_KEYS[part])
            elif part in self.SPECIAL_KEYS:
                main_key = self.SPECIAL_KEYS[part]
            elif len(part) == 1:
                # Single character key
                main_key = KeyCode.from_char(part)
            else:
                # Unknown key, try as character
                main_key = KeyCode.from_char(part[0]) if part else None
        
        return modifiers, main_key
    
    def execute_shortcut(self, shortcut_str: str) -> bool:
        """
        Execute a keyboard shortcut.
        
        Args:
            shortcut_str: Shortcut string (e.g., "ctrl+up", "right")
        
        Returns:
            True if executed successfully, False otherwise
        """
        modifiers, main_key = self.parse_shortcut(shortcut_str)
        
        if main_key is None:
            return False
        
        try:
            # Press all modifiers
            for mod in modifiers:
                self._keyboard.press(mod)
            
            # Press and release main key
            self._keyboard.press(main_key)
            self._keyboard.release(main_key)
            
            # Release all modifiers (in reverse order)
            for mod in reversed(modifiers):
                self._keyboard.release(mod)
            
            return True
        except Exception as e:
            print(f"[GestureHandler] Shortcut execution error: {e}")
            return False
    
    def handle_gesture(self, gesture: str, confidence: float) -> Optional[str]:
        """
        Process a gesture and determine the shortcut to execute.
        
        Args:
            gesture: The gesture name (left, right, up, down)
            confidence: The confidence value (0.0 - 1.0)
        
        Returns:
            The shortcut string if triggered, None otherwise
        """
        threshold = self._config.get_confidence_threshold()
        
        if confidence < threshold:
            return None
        
        # Get the shortcut for this gesture
        shortcuts = self._config.get_gesture_shortcuts()
        shortcut = shortcuts.get(gesture, "none")
        
        if not shortcut or shortcut.lower() == "none":
            return None
        
        return shortcut
    
    def trigger_action(self, shortcut: str) -> bool:
        """
        Execute the keyboard shortcut.
        
        Args:
            shortcut: The shortcut string to execute
        
        Returns:
            True if action was triggered, False otherwise
        """
        return self.execute_shortcut(shortcut)
    
    def process_gesture(self, gesture: str, confidence: float) -> Optional[str]:
        """
        Full gesture processing: determine shortcut and execute it.
        
        Args:
            gesture: The gesture name
            confidence: The confidence value
        
        Returns:
            The shortcut string if triggered, None otherwise
        """
        shortcut = self.handle_gesture(gesture, confidence)
        
        if shortcut is not None:
            current_time = time.time()
            time_since_last = current_time - self._last_action_time
            
            if time_since_last < self._cooldown_time:
                return None
            
            if self.trigger_action(shortcut):
                self._last_action_time = current_time
                
                if self._action_callback:
                    self._action_callback(gesture, shortcut)
                
                return shortcut
        
        return None
    
    def reset_state(self) -> None:
        """Reset the deduplication state."""
        self._last_action_time = 0.0
    
    @classmethod
    def get_available_keys(cls) -> List[str]:
        """Get list of available special key names."""
        return list(cls.SPECIAL_KEYS.keys())
    
    @classmethod
    def get_available_modifiers(cls) -> List[str]:
        """Get list of available modifier key names."""
        return list(cls.MODIFIER_KEYS.keys())
