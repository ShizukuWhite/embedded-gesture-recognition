// AI推理模块实现
#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>
#include "rtos.h"
#include <chrono>
#include "inference_module.h"
#include "a5-deminsion_inferencing.h"

// ==================== 内部状态（模块私有） ====================

// 互斥锁，用于保护共享的预测结果
static rtos::Mutex g_inference_mutex;

// 最新的预测结果
static volatile int g_prediction_index = -1;
static volatile float g_confidence = 0.0f;

// 滑动窗口缓冲区
static float g_sliding_window[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE] = {0};

// 滑动窗口配置
#define SLIDING_WINDOW_STEP 6  // 每次采集 6 个新数据点（2个样本 × 3轴）

// ==================== 内部辅助函数 ====================

/**
 * @brief 采集指定数量的新IMU数据点（用于滑动窗口）
 * @param buffer 输出缓冲区
 * @param num_samples 要采集的数据点数量（3的倍数：X, Y, Z）
 * @return true 采集成功
 * @return false 采集失败
 */
static bool collect_new_samples(float* buffer, size_t num_samples) {
    size_t collected = 0;

    while (collected < num_samples) {
        float x, y, z;
        if (IMU.accelerationAvailable()) {
            IMU.readAcceleration(x, y, z);
            buffer[collected++] = x;
            buffer[collected++] = y;
            buffer[collected++] = z;
        }
        rtos::ThisThread::sleep_for(std::chrono::milliseconds(10));
    }

    return true;
}

/**
 * @brief 滑动窗口：移动数据并添加新样本
 * @param new_data 新采集的数据
 * @param new_data_size 新数据的大小
 */
static void slide_window(const float* new_data, size_t new_data_size) {
    // 将旧数据向左移动（丢弃最旧的数据）
    size_t shift_size = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE - new_data_size;
    memmove(g_sliding_window, g_sliding_window + new_data_size, shift_size * sizeof(float));

    // 在窗口末尾添加新数据
    memcpy(g_sliding_window + shift_size, new_data, new_data_size * sizeof(float));
}

/**
 * @brief 运行分类器并更新预测结果
 * @param buffer 输入数据缓冲区
 * @param buffer_size 缓冲区大小
 * @return true 推理成功
 * @return false 推理失败
 */
static bool run_inference(float* buffer, size_t buffer_size) {
    // 准备信号数据
    signal_t signal;
    int err = numpy::signal_from_buffer(buffer, buffer_size, &signal);
    if (err != 0) {
        ei_printf("[Inference] Failed to create signal from buffer\n");
        return false;
    }

    // 运行分类器
    ei_impulse_result_t result = {0};
    err = run_classifier(&signal, &result, false);
    if (err != EI_IMPULSE_OK) {
        ei_printf("[Inference] Classifier failed (err: %d)\n", err);
        return false;
    }

    // 打印预测结果
    ei_printf("--- Predictions ---\n");
    for (size_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
        ei_printf("  %s: %.5f\n", result.classification[i].label, result.classification[i].value);
    }

    // 找到置信度最高的类别
    float max_confidence = 0.0f;
    int max_index = -1;
    for (size_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
        if (result.classification[i].value > max_confidence) {
            max_confidence = result.classification[i].value;
            max_index = i;
        }
    }

    // 使用互斥锁更新共享变量
    g_inference_mutex.lock();
    g_prediction_index = max_index;
    g_confidence = max_confidence;
    g_inference_mutex.unlock();

    return true;
}

// ==================== 公共接口实现 ====================

bool inference_module_init() {
    if (!IMU.begin()) {
        ei_printf("[Inference] Failed to initialize IMU!\n");
        return false;
    }

    ei_printf("[Inference] IMU initialized successfully\n");
    return true;
}

void inference_task() {
    // 等待1秒让系统稳定
    rtos::ThisThread::sleep_for(std::chrono::seconds(1));

    ei_printf("[Inference] Task started with sliding window mode\n");
    ei_printf("[Inference] Window size: %d, Step: %d\n",
              EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE, SLIDING_WINDOW_STEP);

    // 临时缓冲区用于存放新采集的数据
    float new_samples[SLIDING_WINDOW_STEP];

    // 第一次：填充整个滑动窗口
    ei_printf("[Inference] Filling initial window...\n");
    if (!collect_new_samples(g_sliding_window, EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE)) {
        ei_printf("[Inference] Failed to initialize window\n");
        return;
    }
    ei_printf("[Inference] Initial window ready, starting continuous inference\n");

    for (;;) {
        // 采集新的样本数据
        if (!collect_new_samples(new_samples, SLIDING_WINDOW_STEP)) {
            ei_printf("[Inference] Failed to collect new samples\n");
            rtos::ThisThread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }

        // 滑动窗口：移动数据并添加新样本
        slide_window(new_samples, SLIDING_WINDOW_STEP);

        // 使用滑动窗口运行推理
        if (!run_inference(g_sliding_window, EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE)) {
            ei_printf("[Inference] Inference failed\n");
            rtos::ThisThread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }

        // 短暂休眠，让其他线程有机会运行
        rtos::ThisThread::sleep_for(std::chrono::milliseconds(1));
    }
}

void inference_get_result(int* out_prediction_index, float* out_confidence) {
    g_inference_mutex.lock();
    *out_prediction_index = g_prediction_index;
    *out_confidence = g_confidence;
    g_inference_mutex.unlock();
}

void inference_clear_result() {
    g_inference_mutex.lock();
    g_prediction_index = -1;
    g_confidence = 0.0f;
    g_inference_mutex.unlock();
}

rtos::Mutex& inference_get_mutex() {
    return g_inference_mutex;
}

const char* inference_get_category_name(int index) {
    if (index >= 0 && index < EI_CLASSIFIER_LABEL_COUNT) {
        return ei_classifier_inferencing_categories[index];
    }
    return "unknown";
}
