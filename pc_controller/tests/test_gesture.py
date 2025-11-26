import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hypothesis import given, strategies as st, settings
from config_manager import ConfigManager
from gesture_handler import GestureHandler

valid_gestures = st.sampled_from(["left", "right", "up", "down"])
shortcut_strings = st.sampled_from(["right", "left", "up", "down", "none", "ctrl+up"])
valid_shortcuts = st.fixed_dictionaries({
    "left": shortcut_strings, "right": shortcut_strings,
    "up": shortcut_strings, "down": shortcut_strings
})
threshold_st = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
confidence_st = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


class TestShortcutMapping:
    @given(gesture=valid_gestures, confidence=confidence_st,
           threshold=threshold_st, shortcuts=valid_shortcuts)
    @settings(max_examples=100)
    def test_mapping(self, gesture, confidence, threshold, shortcuts):
        config = ConfigManager()
        config.set_gesture_shortcuts(shortcuts)
        config.set_confidence_threshold(threshold)
        handler = GestureHandler(config)
        result = handler.handle_gesture(gesture, confidence)
        expected = shortcuts[gesture]
        if confidence < threshold:
            assert result is None
        elif expected == "none":
            assert result is None
        else:
            assert result == expected


class TestDefaults:
    def test_threshold_070(self):
        config = ConfigManager()
        handler = GestureHandler(config)
        assert handler.handle_gesture("left", 0.69) is None
        assert handler.handle_gesture("left", 0.70) == "right"

    def test_left_to_right(self):
        config = ConfigManager()
        handler = GestureHandler(config)
        assert handler.handle_gesture("left", 0.80) == "right"

    def test_right_to_left(self):
        config = ConfigManager()
        handler = GestureHandler(config)
        assert handler.handle_gesture("right", 0.80) == "left"

    def test_up_none(self):
        config = ConfigManager()
        handler = GestureHandler(config)
        assert handler.handle_gesture("up", 0.80) is None

    def test_down_none(self):
        config = ConfigManager()
        handler = GestureHandler(config)
        assert handler.handle_gesture("down", 0.80) is None

    def test_unknown_none(self):
        config = ConfigManager()
        handler = GestureHandler(config)
        assert handler.handle_gesture("unknown", 0.90) is None
        assert handler.handle_gesture("idle", 0.90) is None
