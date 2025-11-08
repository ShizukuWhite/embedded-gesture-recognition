# 基于TinyML的实时手势识别控制器（V2.0 模块化RTOS版）

本项目是一个基于Arduino Nano 33 BLE Sense和Edge Impulse的高性能、模块化手势识别控制器。

此 `README.md` 描述的是 `feature/modularization` 分支下的代码架构。此分支代表了项目从“功能原型”到“专业级工程”的重大重构，实现了一个多线程、线程安全、高性能的嵌入式AI系统。

## ✨ 核心特性

* **高精度AI模型：** 基于1D CNN，在测试集上实现了 **98.5%** 的出色准确率，可精准识别`up`, `down`, `left`, `right`, `idle`等多个手势。
* **专业模块化架构：** 代码被完全重构，解耦为**主入口 (`main.cpp`)**、**AI推理模块 (`inference_module`)** 和**LED控制模块 (`led_module`)** 三个独立单元。
* **实时操作系统 (RTOS)：** 采用Mbed OS (`rtos.h`)，将AI推理和LED控制分配到两个独立的线程中，确保了AI计算不会阻塞用户界面的实时响应。
* **高性能滑动窗口：** `inference_task` 实现了高频“滑动窗口”推理机制，完美解决了“离线训练”与“在线推理”的数据不一致问题，极大提升了真实设备上的识别率和响应速度。
* **100%线程安全与封装：** 模块间的数据共享不再依赖不安全的`extern`全局变量。所有共享数据（如预测结果和互斥锁）均被`inference_module` 封装为`static`。模块间通信**完全通过公共API**（如 `inference_get_result()`）进行，从架构上杜绝了数据竞态。
* **健壮的事件逻辑：** `led_module` 采用“消费-清除”模型，在显示一次手势结果后，会主动调用 `inference_clear_result()` 清除该事件，防止了因旧数据导致的重复触发，逻辑严谨。

## 🛠️ 硬件与软件栈

* **硬件平台：** Arduino Nano 33 BLE Sense (nRF52840, BMI270 IMU)
* **AI 平台：** Edge Impulse
* **开发环境：** Visual Studio Code + PlatformIO
* **核心框架：** Arduino, Mbed OS (RTOS)


## 📁 工程结构

本项目的代码遵循PlatformIO的标准模块化规范，实现了高度的“关注点分离”。源代码与第三方库被严格隔离，业务逻辑被清晰地解耦到独立的模块中。

* `📁 include/`：存放所有模块的“公开接口” (.h)
    * `📄 led_module.h`：[LED模块接口] 声明LED控制任务和初始化函数。
    * `📄 inference_module.h`：[AI模块接口] 声明AI推理任务和线程安全的API。
* `📁 lib/`：存放所有第三方库
    * `📁 Bosch_BMI270/`：（IMU驱动库）
    * `📁 a5-deminsion_inferencing/`：（Edge Impulse模型库）
* `📁 src/`：存放所有模块的“具体实现” (.cpp)
    * `🚀 main.cpp`：[项目主入口] 负责初始化、定义线程对象和启动RTOS。
    * `💡 led_module.cpp`：[LED模块实现] 包含LED控制线程的完整逻辑，调用API获取数据。
    * `🧠 inference_module.cpp`：[AI模块实现] 包含AI推理线程、滑动窗口和线程安全API的实现。
* `📄 platformio.ini`：PlatformIO 项目配置文件。



## ⚙️ 工作原理解释（模块化架构）

本系统的工作流程被清晰地划分为三个独立的部分：

1.  **`main.cpp` (指挥中心)**
    * 作为项目入口，`main.cpp` 的职责被极大简化。
    * 它**不包含任何业务逻辑**。
    * 它唯一的任务就是：初始化串口，调用 `inference_module_init()` 和 `led_module_init()` 完成硬件初始化，然后启动 `inferenceThread` 和 `ledThread` 两个RTOS线程。

2.  **`inference_module` (AI大脑)**
    * **`inference_task`** 在一个独立线程中高频运行。
    * 它内部维护一个`static`的滑动窗口缓冲区 `g_sliding_window`。
    * 它持续地采集少量新IMU数据，更新缓冲区，并对这个完整的窗口运行 `run_classifier()`。
    * 所有推理结果（`g_prediction_index`, `g_confidence`）和互斥锁 `g_inference_mutex` 都被封装为`static`，**对外部完全隐藏**。
    * 它只对外暴露 `inference_get_result()` 和 `inference_clear_result()` 两个线程安全的API，供其他模块消费数据。

3.  **`led_module` (用户界面)**
    * **`led_control_task`** 在另一个独立线程中以较低频率（如10Hz）运行。
    * 它不需要知道互斥锁或AI模块的复杂实现。它只做一件事：调用 `inference_get_result()` 来获取最新的手势。
    * 如果识别到有效手势，它会点亮对应颜色的LED，保持一段时间，然后调用 `inference_clear_result()` 来“清除”这个手势事件。
    * 这种“消费-清除”模式 保证了手势只会被触发一次，避免了重复闪灯，逻辑非常健壮。

## 🚀 如何构建

1.  克隆这个 `feature/modularization` 分支。
2.  确保您已经将从Edge Impulse下载的模型库（例如 `a5-deminsion_inferencing`）解压并放置在 `lib/` 文件夹中。
3.  使用 PlatformIO Build & Upload。

## 🌟 未来展望

* **实现低功耗设计：** 在当前专业架构的基础上，引入Bosch官方驱动库，实现真正的中断唤醒和微安级深度睡眠。
* **添加BLE蓝牙通信：** 创建第三个RTOS线程 `ble_task`，将识别到的手势结果通过蓝牙发送出去，实现对PC（PPT控制）或手机（音乐控制）的无线遥控。