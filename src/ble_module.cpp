#include <Arduino.h>
#include <ArduinoBLE.h>
#include "rtos.h"
#include <chrono>

#include "ble_module.h"
#include "inference_module.h"

namespace {

// Custom service/characteristic UUIDs (randomly generated).
BLEService g_dataService("19B10010-E8F2-537E-4F6C-D104768A1214");
BLEStringCharacteristic g_predictionCharacteristic(
    "19B10011-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 32);
BLEFloatCharacteristic g_confidenceCharacteristic(
    "19B10012-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);

constexpr std::chrono::milliseconds kBlePollInterval(100);
constexpr float kMinConfidenceToTransmit = 0.55f;

}  // namespace

bool ble_module_init() {
    if (!BLE.begin()) {
        Serial.println("[BLE] Failed to initialize radio");
        return false;
    }

    BLE.setLocalName("5ClassForwarder");
    BLE.setDeviceName("5ClassForwarder");
    BLE.setAdvertisedService(g_dataService);

    g_dataService.addCharacteristic(g_predictionCharacteristic);
    g_dataService.addCharacteristic(g_confidenceCharacteristic);
    BLE.addService(g_dataService);

    g_predictionCharacteristic.writeValue("unknown");
    g_confidenceCharacteristic.writeValue(0.0f);

    BLE.advertise();
    Serial.println("[BLE] Advertising started");
    return true;
}

void ble_task() {
    uint32_t last_published_sequence = 0;

    for (;;) {
        BLEDevice central = BLE.central();
        if (central) {
            Serial.print("[BLE] Connected to central: ");
            Serial.println(central.address());
            last_published_sequence = 0;  // Force first payload for this connection.

            while (central.connected()) {
                BLE.poll();

                int prediction_index = -1;
                float confidence = 0.0f;
                uint32_t sequence = 0;
                inference_get_result_with_seq(&prediction_index, &confidence, &sequence);

                const bool has_new_payload = (sequence != 0) &&
                                             (sequence != last_published_sequence) &&
                                             (prediction_index != -1) &&
                                             (confidence >= kMinConfidenceToTransmit);

                if (has_new_payload) {
                    last_published_sequence = sequence;

                    const char* label = inference_get_category_name(prediction_index);
                    g_predictionCharacteristic.writeValue(label);
                    g_confidenceCharacteristic.writeValue(confidence);

                    Serial.print("[BLE] Published: ");
                    Serial.print(label);
                    Serial.print(" (");
                    Serial.print(confidence, 3);
                    Serial.println(")");
                }

                rtos::ThisThread::sleep_for(kBlePollInterval);
            }

            Serial.println("[BLE] Central disconnected");
            BLE.advertise();
        }

        BLE.poll();
        rtos::ThisThread::sleep_for(kBlePollInterval);
    }
}
