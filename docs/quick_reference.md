# 手势识别系统 - 快速参考

## 配置参数速查表

### 当前配置（平衡模式）

```cpp
// src/inference_module.cpp
#define VOTE_WINDOW_SIZE 5      // 投票窗口：5次推理
#define VOTE_THRESHOLD 3        // 投票阈值：至少3次
#define MIN_CONFIDENCE 0.65f    // 最低置信度：0.65
#define COOLDOWN_MS 1200        // 冷却时间：1.2秒
```

## 常见问题快速解决

### 问题 1：手势识别太慢

**症状**：需要做很长时间的手势才能识别

**解决方案**：
```cpp
#define VOTE_WINDOW_SIZE 3      // 减小窗口
#define VOTE_THRESHOLD 2        // 降低阈值
#define COOLDOWN_MS 800         // 缩短冷却
```

### 问题 2：经常误触发

**症状**：没做手势也会触发，或者识别错误

**解决方案**：
```cpp
#define VOTE_WINDOW_SIZE 7      // 增大窗口
#define VOTE_THRESHOLD 5        // 提高阈值
#define MIN_CONFIDENCE 0.70f    // 提高置信度
#define COOLDOWN_MS 1800        // 延长冷却
```

### 问题 3：一次手势触发多次

**症状**：做一个手势，PPT 翻了好几页

**解决方案**：
```cpp
#define COOLDOWN_MS 2000        // 延长冷却到2秒
```

或者在 PC 端增加冷却时间（`pc_controller/config.json`）：
```json
{
  "cooldown_time": 3.0
}
```

### 问题 4：手势间隔太长

**症状**：做完一个手势后，要等很久才能做下一个

**解决方案**：
```cpp
#define COOLDOWN_MS 800         // 缩短冷却到0.8秒
```

## 调试技巧

### 1. 查看串口输出

```bash
pio device monitor
```

关键输出：
- `[Inference] Raw:` - 原始推理结果
- `[Vote] ✓ Confirmed:` - 投票确认
- `[Cooldown] Started` - 冷却开始
- `[Cooldown] Ended` - 冷却结束

### 2. 分析识别问题

如果看到：
```
[Inference] Raw: left (0.45)   ← 置信度太低
[Inference] Raw: left (0.72)
[Inference] Raw: right (0.68)  ← 不稳定
[Inference] Raw: left (0.70)
```

说明：
- 手势不够清晰
- 动作速度不合适
- 需要重新训练模型

### 3. 测试不同配置

创建测试配置文件：

**快速模式** (`test_fast.h`)：
```cpp
#define VOTE_WINDOW_SIZE 3
#define VOTE_THRESHOLD 2
#define MIN_CONFIDENCE 0.60f
#define COOLDOWN_MS 600
```

**稳定模式** (`test_stable.h`)：
```cpp
#define VOTE_WINDOW_SIZE 7
#define VOTE_THRESHOLD 5
#define MIN_CONFIDENCE 0.75f
#define COOLDOWN_MS 2000
```

## 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 推理频率 | ~10 Hz | 每秒约10次推理 |
| 投票延迟 | 100-200ms | 从开始到确认 |
| 冷却时间 | 1200ms | 手势间最小间隔 |
| 总响应时间 | ~1.3s | 从手势开始到触发 |
| 内存占用 | 28 bytes | 投票+冷却状态 |

## 编译和上传

```bash
# 编译
pio run

# 上传到开发板
pio run --target upload

# 查看串口输出
pio device monitor

# 一键完成（上传+监视）
pio run --target upload && pio device monitor
```

## PC 端配置

配置文件：`pc_controller/config.json`

```json
{
  "gesture_mapping": {
    "left": "right",      // 向左手势 → 右箭头（下一页）
    "right": "left",      // 向右手势 → 左箭头（上一页）
    "up": "none",
    "down": "none"
  },
  "confidence_threshold": 0.70,
  "cooldown_time": 2.0,   // PC 端冷却：2秒
  "auto_reconnect": true
}
```

## 推荐配置组合

### PPT 演示（推荐）

```cpp
// 嵌入式端
#define VOTE_WINDOW_SIZE 5
#define VOTE_THRESHOLD 3
#define MIN_CONFIDENCE 0.70f
#define COOLDOWN_MS 1500
```

```json
// PC 端
{
  "confidence_threshold": 0.70,
  "cooldown_time": 2.5
}
```

### 快速测试

```cpp
// 嵌入式端
#define VOTE_WINDOW_SIZE 3
#define VOTE_THRESHOLD 2
#define MIN_CONFIDENCE 0.60f
#define COOLDOWN_MS 800
```

```json
// PC 端
{
  "confidence_threshold": 0.60,
  "cooldown_time": 1.5
}
```

### 演示/答辩（最稳定）

```cpp
// 嵌入式端
#define VOTE_WINDOW_SIZE 7
#define VOTE_THRESHOLD 5
#define MIN_CONFIDENCE 0.75f
#define COOLDOWN_MS 2000
```

```json
// PC 端
{
  "confidence_threshold": 0.75,
  "cooldown_time": 3.0
}
```
