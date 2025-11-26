#ifndef INFERENCE_MODULE_H
#define INFERENCE_MODULE_H

#include <stdint.h>

#include "rtos.h"

// 推理模块对外接口

/**
 * @brief 初始化IMU传感器
 * @return true 初始化成功
 * @return false 初始化失败
 */
bool inference_module_init();

/**
 * @brief AI推理任务函数（在独立线程中运行）
 * 持续采集IMU数据，运行分类器，并更新预测结果
 */
void inference_task();

/**
 * @brief 获取最新的预测结果（线程安全）
 * @param out_prediction_index 输出参数：预测类别索引
 * @param out_confidence 输出参数：预测置信度
 */
void inference_get_result(int* out_prediction_index, float* out_confidence);

/**
 * @brief 获取带版本号的预测结果快照，方便多个消费者判定“新数据”.
 * @param out_prediction_index 输出预测类别索引
 * @param out_confidence 输出预测置信度
 * @param out_sequence 输出序列号（每次结果发生明显变化时递增）
 */
void inference_get_result_with_seq(int* out_prediction_index,
                                   float* out_confidence,
                                   uint32_t* out_sequence);

/**
 * @brief 清除当前的预测结果（线程安全）
 * 用于避免重复触发相同的预测
 */
void inference_clear_result();

/**
 * @brief 获取互斥锁的引用（供其他模块使用）
 * @return rtos::Mutex& 互斥锁引用
 */
rtos::Mutex& inference_get_mutex();

/**
 * @brief 根据预测索引获取类别名称
 * @param index 预测类别索引
 * @return const char* 类别名称字符串
 */
const char* inference_get_category_name(int index);

#endif
