"""
Property-based tests for ConfigManager.

Tests:
- Property 2: Configuration Round-Trip Consistency
- Property 3: Gesture Shortcut Validation
"""

import os
import tempfile
from hypothesis import given, strategies as st, settings

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import ConfigManager


# Strategies for generating test data
valid_gestures = st.sampled_from(["left", "right", "up", "down"])
shortcut_strings = st.sampled_from([
    "right", "left", "up", "down", "none",
    "ctrl+up", "ctrl+down", "alt+tab", "shift+f5",
    "ctrl+shift+s", "space", "enter", "pageup", "pagedown"
])

# Strategy for valid gesture shortcuts
valid_gesture_shortcuts = st.fixed_dictionaries({
    "left": shortcut_strings,
    "right": shortcut_strings,
    "up": shortcut_strings,
    "down": shortcut_strings
})

# Strategy for valid confidence thresholds
valid_threshold = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for complete valid configurations
valid_config = st.fixed_dictionaries({
    "gesture_shortcuts": valid_gesture_shortcuts,
    "confidence_threshold": valid_threshold,
    "last_device_address": st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    "auto_reconnect": st.booleans(),
    "cooldown_time": st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False)
})


class TestConfigRoundTrip:
    """
    **Feature: ble-ppt-controller, Property 2: Configuration Round-Trip Consistency**
    
    *For any* valid configuration (containing gesture shortcuts, confidence threshold, 
    and optional settings), saving the configuration to a file and then loading it back 
    SHALL produce an equivalent configuration object.
    
    **Validates: Requirements 3.4, 3.5, 5.4**
    """
    
    @given(config=valid_config)
    @settings(max_examples=100)
    def test_config_round_trip(self, config):
        """Saving then loading a config should preserve all values."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save config
            manager1 = ConfigManager(temp_path)
            manager1._config = config
            manager1.save()
            
            # Load config in new manager
            manager2 = ConfigManager(temp_path)
            loaded = manager2.load()
            
            # Verify round-trip consistency
            assert loaded["gesture_shortcuts"] == config["gesture_shortcuts"], \
                f"Shortcuts mismatch: {loaded['gesture_shortcuts']} != {config['gesture_shortcuts']}"
            
            assert abs(loaded["confidence_threshold"] - config["confidence_threshold"]) < 1e-9, \
                f"Threshold mismatch: {loaded['confidence_threshold']} != {config['confidence_threshold']}"
            
            assert loaded["last_device_address"] == config["last_device_address"], \
                f"Device address mismatch"
            
            assert loaded["auto_reconnect"] == config["auto_reconnect"], \
                f"Auto reconnect mismatch"
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestShortcutValidation:
    """
    **Feature: ble-ppt-controller, Property 3: Gesture Shortcut Validation**
    
    *For any* gesture shortcut mapping where each gesture maps to a shortcut string,
    the ConfigManager SHALL accept and store the mapping.
    
    **Validates: Requirements 3.2**
    """
    
    @given(shortcuts=valid_gesture_shortcuts)
    @settings(max_examples=100)
    def test_valid_shortcuts_accepted(self, shortcuts):
        """Valid shortcuts should be accepted."""
        manager = ConfigManager()
        result = manager.set_gesture_shortcuts(shortcuts)
        assert result is True, f"Valid shortcuts rejected: {shortcuts}"
        
        stored = manager.get_gesture_shortcuts()
        for gesture, shortcut in shortcuts.items():
            assert stored[gesture] == shortcut, \
                f"Stored shortcut mismatch for {gesture}: {stored[gesture]} != {shortcut}"
    
    def test_invalid_gesture_rejected(self):
        """Shortcuts with invalid gesture keys should be rejected."""
        manager = ConfigManager()
        
        invalid_shortcuts = {"invalid_gesture": "right"}
        result = manager.set_gesture_shortcuts(invalid_shortcuts)
        assert result is False


class TestDefaultValues:
    """Unit tests for default configuration values."""
    
    def test_default_confidence_threshold(self):
        """Default confidence threshold should be 0.70."""
        manager = ConfigManager()
        assert manager.get_confidence_threshold() == 0.70
    
    def test_default_gesture_shortcuts(self):
        """Default shortcuts: left→right, right→left, up→none, down→none."""
        manager = ConfigManager()
        shortcuts = manager.get_gesture_shortcuts()
        
        assert shortcuts["left"] == "right"
        assert shortcuts["right"] == "left"
        assert shortcuts["up"] == "none"
        assert shortcuts["down"] == "none"
    
    def test_missing_config_file_uses_defaults(self):
        """Missing config file should result in default values."""
        manager = ConfigManager("nonexistent_config_12345.json")
        config = manager.load()
        
        assert config["confidence_threshold"] == 0.70
        assert config["gesture_shortcuts"]["left"] == "right"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
