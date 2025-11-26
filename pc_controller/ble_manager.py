"""
BLE Manager Module

Handles BLE device scanning, connection, and data reception.
Optimized for Windows BLE connectivity.
"""

import asyncio
import struct
from typing import Optional, Callable, List
from dataclasses import dataclass

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice


@dataclass
class GestureData:
    """Data received from the BLE device."""
    gesture: str
    confidence: float


class BLEManager:
    """BLE connection and data management."""
    
    # UUIDs matching the Arduino firmware (lowercase for better compatibility)
    SERVICE_UUID = "19b10010-e8f2-537e-4f6c-d104768a1214"
    PREDICTION_UUID = "19b10011-e8f2-537e-4f6c-d104768a1214"
    CONFIDENCE_UUID = "19b10012-e8f2-537e-4f6c-d104768a1214"
    
    TARGET_DEVICE_NAME = "5ClassForwarder"
    
    def __init__(self):
        """Initialize BLEManager."""
        self._client: Optional[BleakClient] = None
        self._gesture_callback: Optional[Callable[[str, float], None]] = None
        self._status_callback: Optional[Callable[[str], None]] = None
        self._connected = False
        self._current_gesture: Optional[str] = None
        self._current_confidence: float = 0.0
        self._reconnect_enabled = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._last_device_address: Optional[str] = None
        self._discovered_devices: List[BLEDevice] = []
    
    def set_gesture_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set callback for gesture data. Signature: callback(gesture, confidence)"""
        self._gesture_callback = callback
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for connection status changes."""
        self._status_callback = callback
    
    def _notify_status(self, status: str) -> None:
        """Notify status change via callback."""
        if self._status_callback:
            self._status_callback(status)
    
    async def scan_devices(self, timeout: float = 10.0) -> List[BLEDevice]:
        """
        Scan for BLE devices with improved discovery.
        
        Args:
            timeout: Scan duration in seconds (default 10s for better discovery)
        
        Returns:
            List of discovered BLE devices
        """
        self._notify_status("Scanning...")
        self._discovered_devices = []
        
        print(f"[BLE] Starting scan for {timeout} seconds...")
        
        def detection_callback(device: BLEDevice, advertisement_data):
            """Callback for each discovered device."""
            # Check by name
            if device.name:
                print(f"[BLE] Found: {device.name} [{device.address}]")
                if self.TARGET_DEVICE_NAME in device.name:
                    if device not in self._discovered_devices:
                        self._discovered_devices.append(device)
                        print(f"[BLE] *** Target device found! ***")
            
            # Also check advertisement local name
            if advertisement_data.local_name:
                if self.TARGET_DEVICE_NAME in advertisement_data.local_name:
                    if device not in self._discovered_devices:
                        self._discovered_devices.append(device)
                        print(f"[BLE] *** Target device found via local name! ***")
        
        # Use scanner with callback for real-time discovery
        scanner = BleakScanner(detection_callback=detection_callback)
        
        try:
            await scanner.start()
            await asyncio.sleep(timeout)
            await scanner.stop()
        except Exception as e:
            print(f"[BLE] Scan error: {e}")
        
        # Also try standard discover as backup
        if not self._discovered_devices:
            print("[BLE] Trying standard discover...")
            try:
                devices = await BleakScanner.discover(timeout=5.0)
                for device in devices:
                    if device.name and self.TARGET_DEVICE_NAME in device.name:
                        self._discovered_devices.append(device)
            except Exception as e:
                print(f"[BLE] Standard discover error: {e}")
        
        print(f"[BLE] Scan complete. Found {len(self._discovered_devices)} target device(s)")
        self._notify_status("Disconnected")
        return self._discovered_devices
    
    async def scan_and_connect(self, timeout: float = 15.0) -> bool:
        """
        Scan for target device and connect automatically.
        
        Args:
            timeout: Total timeout for scan and connect
        
        Returns:
            True if connected successfully
        """
        self._notify_status("Scanning & Connecting...")
        
        print("[BLE] Scanning for target device...")
        
        # Try to find device by name during scan
        device = await BleakScanner.find_device_by_name(
            self.TARGET_DEVICE_NAME,
            timeout=timeout
        )
        
        if device:
            print(f"[BLE] Found device: {device.name} [{device.address}]")
            return await self.connect(device.address)
        
        print("[BLE] Device not found")
        self._notify_status("Device not found")
        return False
    
    async def connect(self, device_address: str) -> bool:
        """
        Connect to a BLE device with improved reliability.
        
        Args:
            device_address: The device's MAC address
        
        Returns:
            True if connection successful, False otherwise
        """
        self._notify_status("Connecting...")
        self._last_device_address = device_address
        
        # Disconnect existing connection first
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except:
                pass
            self._client = None
        
        # Try connection with retries
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"[BLE] Connection attempt {attempt}/{max_attempts}...")
                self._notify_status(f"Connecting ({attempt}/{max_attempts})...")
                
                self._client = BleakClient(
                    device_address,
                    disconnected_callback=self._on_disconnect,
                    timeout=20.0  # Longer timeout for Windows
                )
                
                await self._client.connect()
                
                if self._client.is_connected:
                    print("[BLE] Connected! Subscribing to notifications...")
                    
                    # Small delay before subscribing (helps stability)
                    await asyncio.sleep(0.5)
                    
                    # Subscribe to notifications
                    await self._subscribe_notifications()
                    
                    self._connected = True
                    self._reconnect_attempts = 0
                    self._reconnect_enabled = True
                    self._notify_status("Connected")
                    print("[BLE] Ready to receive gestures")
                    return True
                    
            except Exception as e:
                print(f"[BLE] Connection attempt {attempt} failed: {e}")
                if self._client:
                    try:
                        await self._client.disconnect()
                    except:
                        pass
                    self._client = None
                
                if attempt < max_attempts:
                    await asyncio.sleep(1.0)  # Wait before retry
        
        self._notify_status("Connection failed")
        return False
    
    async def _subscribe_notifications(self) -> None:
        """Subscribe to characteristic notifications."""
        if not self._client or not self._client.is_connected:
            return
        
        try:
            # Subscribe to prediction characteristic
            await self._client.start_notify(
                self.PREDICTION_UUID,
                self._on_prediction_notify
            )
            print("[BLE] Subscribed to prediction notifications")
            
            # Subscribe to confidence characteristic
            await self._client.start_notify(
                self.CONFIDENCE_UUID,
                self._on_confidence_notify
            )
            print("[BLE] Subscribed to confidence notifications")
            
        except Exception as e:
            print(f"[BLE] Notification subscription error: {e}")
            raise
    
    def _on_prediction_notify(self, sender, data: bytearray) -> None:
        """Handle prediction characteristic notification."""
        try:
            # Decode string, strip null bytes
            gesture = data.decode('utf-8').rstrip('\x00').strip()
            self._current_gesture = gesture
            self._check_and_emit_gesture()
        except Exception as e:
            print(f"[BLE] Prediction decode error: {e}")
    
    def _on_confidence_notify(self, sender, data: bytearray) -> None:
        """Handle confidence characteristic notification."""
        try:
            # Decode float (little-endian)
            if len(data) >= 4:
                self._current_confidence = struct.unpack('<f', data[:4])[0]
                self._check_and_emit_gesture()
        except Exception as e:
            print(f"[BLE] Confidence decode error: {e}")
    
    def _check_and_emit_gesture(self) -> None:
        """Emit gesture if we have both prediction and confidence."""
        if self._current_gesture and self._gesture_callback:
            self._gesture_callback(self._current_gesture, self._current_confidence)
    
    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle disconnection event."""
        self._connected = False
        self._notify_status("Disconnected")
        print("[BLE] Disconnected from device")
        
        # Trigger auto-reconnect if enabled
        if self._reconnect_enabled and self._last_device_address:
            asyncio.create_task(self._auto_reconnect())
    
    async def _auto_reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            print("[BLE] Max reconnect attempts reached")
            self._notify_status("Reconnect failed")
            return
        
        self._reconnect_attempts += 1
        delay = min(2 ** self._reconnect_attempts, 10)  # Cap at 10 seconds
        
        print(f"[BLE] Reconnect attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} in {delay}s")
        self._notify_status(f"Reconnecting ({self._reconnect_attempts}/{self._max_reconnect_attempts})...")
        
        await asyncio.sleep(delay)
        
        if not self._connected and self._last_device_address:
            success = await self.connect(self._last_device_address)
            if not success and self._reconnect_attempts < self._max_reconnect_attempts:
                await self._auto_reconnect()
    
    async def disconnect(self) -> None:
        """Disconnect from the current device."""
        self._reconnect_enabled = False  # Disable auto-reconnect for manual disconnect
        
        if self._client:
            try:
                if self._client.is_connected:
                    await self._client.disconnect()
            except Exception as e:
                print(f"[BLE] Disconnect error: {e}")
        
        self._connected = False
        self._client = None
        self._notify_status("Disconnected")
    
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._connected and self._client is not None and self._client.is_connected
    
    def set_auto_reconnect(self, enabled: bool) -> None:
        """Enable or disable auto-reconnect."""
        self._reconnect_enabled = enabled
