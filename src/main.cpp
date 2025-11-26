// ==================== 模块化的主程序 ====================
// 使用独立的推理模块和LED控制模块
#include <Arduino.h>
#include "rtos.h"

#include "inference_module.h"
#include "led_module.h"
#include "ble_module.h"

// --- Mbed 线程对象 ---
// 使用相同的优先级 (osPriorityNormal) 实现公平调度
rtos::Thread inferenceThread(osPriorityNormal, 8192);
rtos::Thread ledThread(osPriorityNormal);
rtos::Thread bleThread(osPriorityNormal);

// --- 主程序 ---
void setup() {
    Serial.begin(115200);

    // 初始化推理模块（包括IMU）
    if (!inference_module_init()) {
        Serial.println("Failed to initialize inference module!");
        while (1);
    }

    // 初始化LED模块
    led_module_init();

    // 初始化BLE模块
    if (!ble_module_init()) {
        Serial.println("Failed to initialize BLE module!");
        while (1);
    }

    Serial.println("--- Starting Modularized System ---");

    // 启动线程
    inferenceThread.start(inference_task);
    ledThread.start(led_control_task);
    bleThread.start(ble_task);

    Serial.println("--- System Ready ---");
}

void loop() {
    // 空闲循环 - 所有工作由RTOS线程完成
}
