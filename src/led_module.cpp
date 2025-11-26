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

    for (;;) {
        int prediction_index = -1;
        float confidence = 0.0f;
        uint32_t sequence = 0;

        // Snapshot the latest inference result.
        inference_get_result_with_seq(&prediction_index, &confidence, &sequence);

        if (sequence == last_sequence) {
            // Nothing new to show, yield the CPU briefly.
            rtos::ThisThread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }
        last_sequence = sequence;

        if (confidence > 0.65f && prediction_index != -1) {
            const char* prediction = inference_get_category_name(prediction_index);
            bool is_gesture = (strcmp(prediction, "idle") != 0 && strcmp(prediction, "unknown") != 0);

            if (is_gesture) {
                if (strcmp(prediction, "up") == 0)        set_led_color(OFF, ON, OFF);   // green
                else if (strcmp(prediction, "down") == 0) set_led_color(ON, ON, OFF);   // yellow
                else if (strcmp(prediction, "right") == 0)set_led_color(ON, OFF, ON);   // purple
                else if (strcmp(prediction, "left") == 0) set_led_color(OFF, OFF, ON);  // blue

                rtos::ThisThread::sleep_for(std::chrono::milliseconds(GESTURE_LIGHT_DURATION_MS));
                set_led_color(OFF, OFF, OFF);
            } else {
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
