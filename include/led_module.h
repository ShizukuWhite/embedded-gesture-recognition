#ifndef LED_MODULE_H
#define LED_MODULE_H

// LED控制模块对外接口

/**
 * @brief 初始化LED GPIO引脚
 */
void led_module_init();

/**
 * @brief LED控制任务函数（在独立线程中运行）
 * 根据推理结果控制RGB LED的颜色和状态
 */
void led_control_task();

#endif