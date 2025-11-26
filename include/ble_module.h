#pragma once

/**
 * @brief Initialize the BLE peripheral (services + characteristics).
 * @return true on success, false otherwise.
 */
bool ble_module_init();

/**
 * @brief Continuous BLE task that keeps the stack responsive and pushes
 *        inference results to the connected central device.
 */
void ble_task();
