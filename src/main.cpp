// ==================== 模块化的主程序 ====================
// 使用独立的推理模块和LED控制模块
#include <Arduino.h>
#include "rtos.h"

#include "inference_module.h"
#include "led_module.h"

// --- Mbed 线程对象 ---
// 两个线程使用相同的优先级 (osPriorityNormal) 实现公平调度
rtos::Thread inferenceThread(osPriorityNormal, 8192);
rtos::Thread ledThread(osPriorityNormal);

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

    Serial.println("--- Starting Modularized System ---");

    // 启动两个线程
    inferenceThread.start(inference_task);
    ledThread.start(led_control_task);

    Serial.println("--- System Ready ---");
}

void loop() {
    // 空闲循环 - 所有工作由RTOS线程完成
}