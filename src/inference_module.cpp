// AI推理模块实现
#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>
#include "rtos.h"
#include <chrono>
#include <cmath>
#include <string.h>
#include "inference_module.h"
#include "a5-deminsion_inferencing.h"

// ==================== 内部状态（模块私有） ====================

// 互斥锁，用于保护共享的预测结果
static rtos::Mutex g_inference_mutex;

// 系统状态机
enum SystemState {
    INFERENCE_MODE,
    FORWARDING_MODE,
    REFILLING_MODE
};
static SystemState g_current_state = INFERENCE_MODE;

// 最新的预测结果
static volatile int g_prediction_index = -1;
static volatile float g_confidence = 0.0f;
static volatile uint32_t g_result_sequence = 0;

// 滑动窗口缓冲区
static float g_sliding_window[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE] = {0};

// 滑动窗口配置
#define SLIDING_WINDOW_STEP 6  // 每次采集 6 个新数据点（2个样本 × 3轴）
#define PULL_THRESHOLD 2.5f

// ==================== 多数投票机制配置 ====================
#define VOTE_WINDOW_SIZE 5      // 投票窗口大小：最近5次推理结果
#define VOTE_THRESHOLD 3        // 投票阈值：至少3次相同才确认
#define MIN_CONFIDENCE 0.65f    // 最低置信度阈值

// ==================== 冷却机制配置 ====================
#define COOLDOWN_MS 1200        // 冷却时间：1200ms (1.2秒)

// 投票缓冲区
static int g_vote_buffer[VOTE_WINDOW_SIZE];
static int g_vote_index = 0;
static bool g_vote_initialized = false;

// 冷却状态
static uint32_t g_last_confirmed_time = 0;
static bool g_in_cooldown = false;

// ==================== 内部辅助函数 ====================

/**
 * @brief 初始化投票缓冲区
 */
static void init_vote_buffer() {
    for (int i = 0; i < VOTE_WINDOW_SIZE; i++) {
        g_vote_buffer[i] = -1;
    }
    g_vote_index = 0;
    g_vote_initialized = true;
}

/**
 * @brief 检查是否在冷却期
 * @return true 在冷却期，false 不在冷却期
 */
static bool is_in_cooldown() {
    if (!g_in_cooldown) {
        return false;
    }
    
    uint32_t current_time = millis();
    uint32_t elapsed = current_time - g_last_confirmed_time;
    
    if (elapsed >= COOLDOWN_MS) {
        g_in_cooldown = false;
        ei_printf("[Cooldown] Ended (duration: %lu ms)\n", elapsed);
        return false;
    }
    
    return true;
}

/**
 * @brief 启动冷却期
 */
static void start_cooldown() {
    g_last_confirmed_time = millis();
    g_in_cooldown = true;
    ei_printf("[Cooldown] Started (%d ms)\n", COOLDOWN_MS);
}

/**
 * @brief 清空投票缓冲区（用于冷却期结束后重置）
 */
static void clear_vote_buffer() {
    for (int i = 0; i < VOTE_WINDOW_SIZE; i++) {
        g_vote_buffer[i] = -1;
    }
    g_vote_index = 0;
}

/**
 * @brief 多数投票机制：确认手势
 * @param new_prediction 新的预测结果索引
 * @param confidence 置信度
 * @return 确认的手势索引，-1 表示未达到阈值或在冷却期
 */
static int majority_vote_with_cooldown(int new_prediction, float confidence) {
    // 1. 检查是否在冷却期
    if (is_in_cooldown()) {
        return -1;  // 冷却期内，忽略所有推理
    }
    
    // 2. 置信度过滤：低于阈值的预测不参与投票
    if (confidence < MIN_CONFIDENCE) {
        return -1;
    }
    
    // 3. 更新投票缓冲区（循环队列）
    g_vote_buffer[g_vote_index] = new_prediction;
    g_vote_index = (g_vote_index + 1) % VOTE_WINDOW_SIZE;
    
    // 4. 统计每个类别的票数
    int counts[EI_CLASSIFIER_LABEL_COUNT];
    for (int i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
        counts[i] = 0;
    }
    
    for (int i = 0; i < VOTE_WINDOW_SIZE; i++) {
        if (g_vote_buffer[i] >= 0 && g_vote_buffer[i] < EI_CLASSIFIER_LABEL_COUNT) {
            counts[g_vote_buffer[i]]++;
        }
    }
    
    // 5. 找到票数最多的类别
    int max_count = 0;
    int winner = -1;
    for (int i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
        if (counts[i] >= VOTE_THRESHOLD && counts[i] > max_count) {
            max_count = counts[i];
            winner = i;
        }
    }
    
    // 6. 如果确认了手势，处理结果
    if (winner >= 0) {
        const char* label = inference_get_category_name(winner);
        
        // idle 类别：确认但不启动冷却
        if (strcmp(label, "idle") == 0) {
            // idle 状态也需要更新，但不启动冷却
            return winner;
        }
        
        // 非 idle 手势：确认并启动冷却
        ei_printf("[Vote] ✓ Confirmed: %s (votes: %d/%d)\n", 
                  label, max_count, VOTE_WINDOW_SIZE);
        
        // 启动冷却
        start_cooldown();
        
        // 清空投票缓冲区，避免旧数据影响下一次识别
        clear_vote_buffer();
        
        return winner;
    }
    
    return -1;
}

/**
 * @brief 采集指定数量的新IMU数据点（用于滑动窗口）
 * @param buffer 输出缓冲区
 * @param num_samples 要采集的数据点数量（3的倍数：X, Y, Z）
 * @return true 采集成功
 * @return false 采集失败
 */
static bool collect_new_samples(float* buffer, size_t num_samples) {

    //安全检验，防止缓冲区溢出
    if (num_samples % 3 != 0) return false;

    size_t collected = 0;

    while (collected < num_samples) {
        float x, y, z;
        if (IMU.accelerationAvailable()) {
            IMU.readAcceleration(x, y, z);
            buffer[collected++] = x;
            buffer[collected++] = y;
            buffer[collected++] = z;
        }
        // 匹配训练时的采样频率：48Hz = 20.83ms间隔
        // 采用EI库中的时间间隔
        //转成integer类型，因为sleep_for函数需要整数参数
        rtos::ThisThread::sleep_for(std::chrono::milliseconds(static_cast<int>(EI_CLASSIFIER_INTERVAL_MS)));
    }

    return true;
}

/**
 * @brief 滑动窗口：移动数据并添加新样本
 * @param new_data 新采集的数据
 * @param new_data_size 新数据的大小
 */
static void slide_window(const float* new_data, size_t new_data_size) {
    size_t shift_size = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE - new_data_size;
    memmove(g_sliding_window, g_sliding_window + new_data_size, shift_size * sizeof(float));
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
    signal_t signal;
    int err = numpy::signal_from_buffer(buffer, buffer_size, &signal);
    if (err != 0) return false;

    ei_impulse_result_t result = {0};
    err = run_classifier(&signal, &result, false);
    if (err != EI_IMPULSE_OK) return false;

    float max_confidence = 0.0f;
    int max_index = -1;
    for (size_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
        if (result.classification[i].value > max_confidence) {
            max_confidence = result.classification[i].value;
            max_index = i;
        }
    }

    g_inference_mutex.lock();
    g_prediction_index = max_index;
    g_confidence = max_confidence;
    g_result_sequence++;  // 每次推理后递增序列号
    g_inference_mutex.unlock();

    return true;
}

// ==================== 公共接口实现 ====================

bool inference_module_init() {
    if (!IMU.begin()) {
        ei_printf("[Inference] Failed to initialize IMU!\n");
        return false;
    }
    
    // 初始化投票缓冲区
    init_vote_buffer();
    
    ei_printf("[Inference] IMU initialized successfully\n");
    ei_printf("[Inference] Voting: window=%d, threshold=%d, min_conf=%.2f\n",
              VOTE_WINDOW_SIZE, VOTE_THRESHOLD, MIN_CONFIDENCE);
    ei_printf("[Inference] Cooldown: %d ms\n", COOLDOWN_MS);
    return true;
}

void inference_task() {
    rtos::ThisThread::sleep_for(std::chrono::seconds(1));
    ei_printf("[Inference] Task started. State: INFERENCE_MODE\n");

    float new_samples[SLIDING_WINDOW_STEP];

    // 填充初始化窗口
    if (!collect_new_samples(g_sliding_window, EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE)) return;

    for (;;) {
        switch (g_current_state) {
            case INFERENCE_MODE: {
                collect_new_samples(new_samples, SLIDING_WINDOW_STEP);
                slide_window(new_samples, SLIDING_WINDOW_STEP);
                run_inference(g_sliding_window, EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE);

                // 原始推理结果（用于调试）
                const char* raw_label = (g_prediction_index >= 0) ? 
                    ei_classifier_inferencing_categories[g_prediction_index] : "unknown";
                
                // 只在非冷却期显示原始结果
                if (!g_in_cooldown) {
                    ei_printf("[Inference] Raw: %s (%.2f)\n", raw_label, g_confidence);
                }
                
                // 使用多数投票+冷却机制确认手势
                int confirmed_index = majority_vote_with_cooldown(g_prediction_index, g_confidence);
                
                // 只有投票确认的手势才更新全局状态
                if (confirmed_index >= 0) {
                    const char* confirmed_label = inference_get_category_name(confirmed_index);
                    
                    // 更新全局状态
                    g_inference_mutex.lock();
                    g_prediction_index = confirmed_index;
                    g_result_sequence++;
                    g_inference_mutex.unlock();
                    
                    ei_printf("[Inference] >>> CONFIRMED: %s (seq=%lu) <<<\n", 
                              confirmed_label, g_result_sequence);
                    
                    // 检查是否是 push 手势
                    if (strcmp(confirmed_label, "push") == 0) {
                        g_current_state = FORWARDING_MODE;
                        ei_printf("\n>>> !!! PUSH DETECTED !!! Switching to FORWARDING_MODE <<<\n");
                    }
                }
                
                break;
            }

            case FORWARDING_MODE: {
                float ax, ay, az, gx, gy, gz;
                if (IMU.accelerationAvailable()&& IMU.gyroscopeAvailable()) {
                    IMU.readAcceleration(ax, ay, az);
                    IMU.readGyroscope(gx, gy, gz);  
                    float magnitude = sqrt(ax*ax + ay*ay + az*az);
                    
                    if (magnitude > PULL_THRESHOLD) {
                        g_current_state = REFILLING_MODE;
                        ei_printf(">>> Pull detected (Mag: %.2f)! Returning to INFERENCE_MODE <<<\n", magnitude);
                    } else {
                        ei_printf("DATA_RAW: ACC[%.2f,%.2f,%.2f] GYRO[%.2f,%.2f,%.2f]\n", ax, ay, az, gx, gy, gz);
                    }
                }
                rtos::ThisThread::sleep_for(std::chrono::milliseconds(20));
                break;
            }

            case REFILLING_MODE: {
                ei_printf(">>> Refilling Inference Window... <<<\n");
                collect_new_samples(g_sliding_window, EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE);
                g_current_state = INFERENCE_MODE;
                ei_printf(">>> State: INFERENCE_MODE <<<\n");
                break;
            }
        }
        rtos::ThisThread::sleep_for(std::chrono::milliseconds(1));
    }
}
// ... (保留其余公共接口)


void inference_get_result(int* out_prediction_index, float* out_confidence) {
    g_inference_mutex.lock();
    *out_prediction_index = g_prediction_index;
    *out_confidence = g_confidence;
    g_inference_mutex.unlock();
}

void inference_get_result_with_seq(int* out_prediction_index,
                                   float* out_confidence,
                                   uint32_t* out_sequence) {
    g_inference_mutex.lock();
    if (out_prediction_index) {
        *out_prediction_index = g_prediction_index;
    }
    if (out_confidence) {
        *out_confidence = g_confidence;
    }
    if (out_sequence) {
        *out_sequence = g_result_sequence;
    }
    g_inference_mutex.unlock();
}

void inference_clear_result() {
    g_inference_mutex.lock();
    g_prediction_index = -1;
    g_confidence = 0.0f;
    g_result_sequence++;
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
