// ----------------- 通过同等优先级强制调度的最终代码 -----------------
#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>
#include "rtos.h"
#include <chrono>

#include "a5-deminsion_inferencing.h"

// --- 全局变量 ---
volatile int g_latest_prediction_index = -1;
volatile float g_latest_confidence = 0.0;

// --- Mbed 线程对象 ---
// 【关键修复】将两个线程的优先级设置为完全相同 (osPriorityNormal)
rtos::Thread inferenceThread(osPriorityNormal, 8192);
rtos::Thread ledThread(osPriorityNormal); // <--- 从 osPriorityLow 改为 osPriorityNormal

/**
 * @brief 任务1：AI推理
 */
void inference_task() {
    rtos::ThisThread::sleep_for(std::chrono::seconds(1));

    for (;;) {
        signal_t signal;
        float buffer[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE] = {0};
        size_t buf_idx = 0;

        while (buf_idx < EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) {
            float x, y, z;
            if (IMU.accelerationAvailable()) {
                IMU.readAcceleration(x, y, z);
                buffer[buf_idx++] = x;
                buffer[buf_idx++] = y;
                buffer[buf_idx++] = z;
            }
            rtos::ThisThread::sleep_for(std::chrono::milliseconds(10));
        }

        int err = numpy::signal_from_buffer(buffer, EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE, &signal);
        if (err != 0) continue;
        
        ei_impulse_result_t result = {0};
        err = run_classifier(&signal, &result, false);
        if (err != EI_IMPULSE_OK) continue;

        ei_printf("--- Predictions ---\n");
        for (size_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
            ei_printf("  %s: %.5f\n", result.classification[i].label, result.classification[i].value);
        }
        
        float max_confidence = 0;
        int max_index = -1;
        for (size_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
            if (result.classification[i].value > max_confidence) {
                max_confidence = result.classification[i].value;
                max_index = i;
            }
        }
        
        g_latest_prediction_index = max_index;
        g_latest_confidence = max_confidence;
        
        // 这个延时现在不是必须的了，但保留着也没坏处
        rtos::ThisThread::sleep_for(std::chrono::milliseconds(1));
    }
}

/**
 * @brief 辅助函数：设置颜色
 */
void set_led_color(int r, int g, int b) {
    digitalWrite(LEDR, r);
    digitalWrite(LEDG, g);
    digitalWrite(LEDB, b);
}

/**
 * @brief 任务2：控制RGB LED
 */
void led_control_task() {
    const int OFF = HIGH;
    const int ON = LOW;

    for (;;) {
        // 这次我们应该能看到这条打印了
        ei_printf("[LED Task] Running, checking confidence: %.2f\n", g_latest_confidence);

        if (g_latest_confidence > 0.65 && g_latest_prediction_index != -1) {
            const char* prediction = ei_classifier_inferencing_categories[g_latest_prediction_index];
            if (strcmp(prediction, "up") == 0)       set_led_color(OFF, ON, OFF);
            else if (strcmp(prediction, "down") == 0)  set_led_color(ON, ON, OFF);
            else if (strcmp(prediction, "left") == 0)  set_led_color(OFF, OFF, ON);
            else if (strcmp(prediction, "right") == 0) set_led_color(ON, OFF, ON);
            else if (strcmp(prediction, "idle") == 0)  set_led_color(ON, OFF, OFF);
            else if (strcmp(prediction,"unknown")==0) set_led_color(OFF, OFF, OFF);
        } else {
            set_led_color(OFF, OFF, OFF);
        }
        rtos::ThisThread::sleep_for(std::chrono::milliseconds(100));
    }
}

// --- 主程序 ---
void setup() {
    Serial.begin(115200);

    if (!IMU.begin()) {
        ei_printf("Failed to initialize IMU!\n");
        while (1);
    }
    
    pinMode(LEDR, OUTPUT);
    pinMode(LEDG, OUTPUT);
    pinMode(LEDB, OUTPUT);
    set_led_color(HIGH, HIGH, HIGH);

    ei_printf("--- Starting Threads with EQUAL priority ---\n");

    // 注意：不再需要 set_priority() 了，因为已经在声明时设置好了
    inferenceThread.start(inference_task);
    ledThread.start(led_control_task);
}

void loop() {
    // 空
}