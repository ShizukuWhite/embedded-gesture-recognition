# 🖐️ Embedded Gesture Recognition System (基于 TinyML & RTOS)

> 一个基于 Arduino Nano 33 BLE Sense Rev2 的实时手势识别系统，集成了 Edge Impulse 机器学习模型、FreeRTOS 多线程调度以及 BLE 蓝牙低功耗通信。

![Project Status](https://img.shields.io/badge/Status-Prototype-green)
![Platform](https://img.shields.io/badge/Platform-Arduino_Nano_33_BLE_Sense_Rev2-blue)
![RTOS](https://img.shields.io/badge/OS-Mbed_OS%2Frtos-orange)

## 📖 项目简介 (Introduction)

本项目是嵌入式系统毕业设计的一部分。目标是构建一个低功耗、可穿戴的手势交互终端。系统利用板载 IMU (BMI270) 采集运动数据，通过部署在边缘端的神经网络模型（基于 Edge Impulse）实时识别手势，并通过 BLE 蓝牙协议将结果广播给上位机（手机/电脑），实现对外部设备的无线控制。

### ✨ 核心特性 (Key Features)

* **⚡ 模块化架构 (Modular Design)**: 采用高内聚低耦合设计，将推理 (`Inference`)、通信 (`BLE`) 和交互 (`LED`) 拆分为独立模块。
* **🔄 实时操作系统 (RTOS)**: 基于 Mbed OS 的多线程设计。
    * **Inference Thread**: 负责传感器采样与模型推理（高优先级）。
    * **BLE Thread**: 负责蓝牙广播与数据推送（IO 密集型）。
    * **LED Thread**: 负责状态指示（非阻塞延时）。
* **🛡️ 线程安全 (Thread Safety)**: 使用 `rtos::Mutex` 保护共享的预测结果，防止多任务环境下的竞争条件 (Race Condition)。
* **📡 事件驱动通信**: 引入序列号 (`Sequence ID`) 机制，仅在检测到新手势时触发 BLE 通知，大幅降低无效广播功耗。
* **🧠 边缘计算**: 模型完全在微控制器上运行，无需联网即可完成推理。

## 🛠️ 硬件要求 (Hardware)

* [cite_start]**开发板**: Arduino Nano 33 BLE Sense **Rev2** [cite: 23]
    * *注意：Rev2 版本使用 BMI270/BMM150 传感器，与旧版 LSM9DS1 不通用。*
* [cite_start]**传感器**: 板载 6轴 IMU (加速度计 + 陀螺仪) [cite: 34]
* **连接**: Micro-USB 数据线

## ⚙️ 软件依赖 (Dependencies)

在 Arduino IDE 中需安装以下库：

1.  [cite_start]**Arduino_BMI270_BMM150**: 用于驱动 Rev2 的 IMU 传感器 [cite: 34]。
2.  **ArduinoBLE**: 用于蓝牙低功耗通信。
3.  **Edge Impulse Library**: 导出的 C++ 模型库 (本名为 `a5-deminsion_inferencing`)。

## 🏗️ 系统架构 (System Architecture)

系统由三个核心线程并发运行，通过全局受保护状态进行通信：

```mermaid
graph TD
    IMU[IMU Sensor] -->|Sample 62.5Hz| INF_T[Inference Thread]
    INF_T -->|Sliding Window| MODEL[TinyML Model]
    MODEL -->|Update Mutex| STATE["Shared State<br/>(Result + Confidence + Seq)"]
    
    STATE -->|Read Mutex| BLE_T[BLE Thread]
    STATE -->|Read Mutex| LED_T[LED Thread]
    
    BLE_T -->|Notify Changed| PHONE[Smartphone App]
    LED_T -->|Blink Color| RGB[RGB LED]
