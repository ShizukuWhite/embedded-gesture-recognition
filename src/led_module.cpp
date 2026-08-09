// LED control implementation
#include <Arduino.h>
#include "rtos.h"
#include <chrono>
#include <cstring>

#include "led_module.h"
#include "inference_module.h"

// Local helper to drive the built-in RGB LED (active low on Nano 33 BLE Sense).
static void set_led_color(int r, int g, int b) {
    digitalWrite(LEDR, r);
    digitalWrite(LEDG, g);
    digitalWrite(LEDB, b);
}

void led_module_init() {
    pinMode(LEDR, OUTPUT);
    pinMode(LEDG, OUTPUT);
    pinMode(LEDB, OUTPUT);
    set_led_color(HIGH, HIGH, HIGH);
}

void led_control_task() {
    const int OFF = HIGH;
    const int ON = LOW;
    const int GESTURE_LIGHT_DURATION_MS = 500;
    uint32_t last_sequence = 0;
    uint32_t last_update_time = millis();
    bool in_forwarding_mode = false;

    for (;;) {
        int prediction_index = -1;
        float confidence = 0.0f;
        uint32_t sequence = 0;
        uint32_t current_time = millis();

        // Snapshot the latest inference result.
        inference_get_result_with_seq(&prediction_index, &confidence, &sequence);

        // 检测序列号是否更新
        bool sequence_updated = (sequence != last_sequence);

        if (sequence_updated) {
            last_sequence = sequence;
            last_update_time = current_time;  // 更新时间戳
        }

        // 检测超时（可能进入 IDLE_STATE）
        if ((current_time - last_update_time > 1000) && (!in_forwarding_mode)) {
            set_led_color(OFF, OFF, OFF);  // 关闭 LED
            //in_forwarding_mode = false;
            rtos::ThisThread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }

        // 如果序列号没有更新，检查是否在 FORWARDING_MODE
        if (!sequence_updated) {
            if (in_forwarding_mode ) {
                set_led_color(ON, ON, ON);  // 保持白光
            }
            rtos::ThisThread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }

        // 序列号更新了，处理新的手势
        if (confidence > 0.80f && prediction_index != -1) {
            const char* prediction = inference_get_category_name(prediction_index);
            bool is_gesture = (strcmp(prediction, "idle") != 0 && strcmp(prediction, "unknown") != 0);

            if (is_gesture) {
                if (strcmp(prediction, "push") == 0) {
                    // 进入 FORWARDING_MODE，保持白光常亮
                    set_led_color(ON, ON, ON);
                    in_forwarding_mode = true;
                    // 不要关闭 LED，让它保持常亮
                } else {
                    // 其他手势：短暂显示后关闭
                    in_forwarding_mode = false;
                    if (strcmp(prediction, "up") == 0)        set_led_color(OFF, ON, OFF);   // green
                    else if (strcmp(prediction, "down") == 0) set_led_color(ON, ON, OFF);   // yellow
                    else if (strcmp(prediction, "right") == 0)set_led_color(ON, OFF, ON);   // purple
                    else if (strcmp(prediction, "left") == 0) set_led_color(OFF, OFF, ON);  // blue

                    rtos::ThisThread::sleep_for(std::chrono::milliseconds(GESTURE_LIGHT_DURATION_MS));
                    set_led_color(OFF, OFF, OFF);
                }
            } else {
                in_forwarding_mode = false;
                if (strcmp(prediction, "idle") == 0) {
                    set_led_color(ON, OFF, OFF);  // red
                } else { // unknown
                    set_led_color(OFF, OFF, OFF);
                }
            }
        } else {
            set_led_color(OFF, OFF, OFF);
        }

        rtos::ThisThread::sleep_for(std::chrono::milliseconds(100));
    }
}
