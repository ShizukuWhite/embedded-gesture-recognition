"""
BLE PPT Controller - Main Entry Point

A PC application that receives gesture recognition results from Arduino Nano 33 BLE
and converts them to PowerPoint slide navigation commands.
"""

import asyncio
import threading
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import ConfigManager
from gesture_handler import GestureHandler
from ble_manager import BLEManager
from gui import MainWindow


def run_async_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Run the asyncio event loop in a separate thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def main():
    """Main entry point for the BLE PPT Controller application."""
    print("BLE PPT Controller")
    print("==================")
    print("Starting application...")
    
    # Determine config path (same directory as script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    # Initialize components
    config_manager = ConfigManager(config_path)
    config_manager.load()
    
    gesture_handler = GestureHandler(config_manager)
    ble_manager = BLEManager()
    
    # Set auto-reconnect from config
    ble_manager.set_auto_reconnect(config_manager.get_auto_reconnect())
    
    # Create GUI
    window = MainWindow(config_manager, gesture_handler, ble_manager)
    
    # Create and start asyncio event loop in separate thread
    loop = asyncio.new_event_loop()
    window.set_event_loop(loop)
    
    async_thread = threading.Thread(target=run_async_loop, args=(loop,), daemon=True)
    async_thread.start()
    
    # Add startup log entry
    window.add_log_entry("Application started")
    window.add_log_entry("Click 'Scan' to find BLE devices")
    
    print("GUI started. Close the window to exit.")
    
    # Run tkinter main loop (blocks until window closed)
    try:
        window.run()
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        loop.call_soon_threadsafe(loop.stop)
        print("Application closed.")


if __name__ == "__main__":
    main()
