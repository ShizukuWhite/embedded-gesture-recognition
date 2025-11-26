"""
BLE Scan Test Script - 用于诊断 BLE 扫描问题
"""

import asyncio
from bleak import BleakScanner


async def scan_all_devices():
    """扫描所有 BLE 设备（不过滤）"""
    print("正在扫描所有 BLE 设备...")
    print("请确保：")
    print("  1. 开发板已上电并运行")
    print("  2. Windows 蓝牙已开启")
    print("  3. 开发板未被其他设备连接")
    print()
    
    devices = await BleakScanner.discover(timeout=10.0)
    
    print(f"\n找到 {len(devices)} 个设备：")
    print("-" * 60)
    
    for device in devices:
        name = device.name or "(无名称)"
        print(f"  名称: {name}")
        print(f"  地址: {device.address}")
        
        # 检查是否是我们的目标设备
        if device.name and "5Class" in device.name:
            print(f"  *** 这是目标设备! ***")
        print()
    
    if not devices:
        print("未找到任何设备！")
        print("\n可能的原因：")
        print("  1. Windows 蓝牙未开启")
        print("  2. 需要以管理员权限运行")
        print("  3. 蓝牙适配器不支持 BLE")
        print("  4. 开发板未在广播")


async def scan_with_callback():
    """使用回调方式扫描，可以看到实时发现的设备"""
    print("\n使用回调方式扫描（实时显示）...")
    
    def detection_callback(device, advertisement_data):
        name = device.name or "(无名称)"
        print(f"  发现: {name} [{device.address}]")
        if advertisement_data.local_name:
            print(f"         广播名称: {advertisement_data.local_name}")
    
    scanner = BleakScanner(detection_callback=detection_callback)
    
    await scanner.start()
    await asyncio.sleep(10.0)
    await scanner.stop()


if __name__ == "__main__":
    print("=" * 60)
    print("BLE 扫描诊断工具")
    print("=" * 60)
    
    asyncio.run(scan_all_devices())
    asyncio.run(scan_with_callback())
