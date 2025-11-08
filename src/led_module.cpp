//LED的控制实现模块代码
#include <Arduino.h>
#include "rtos.h"
#include <chrono>
#include "led_module.h"
#include "inference_module.h"


//内部函数，用static修饰，防止外部调用,
static void set_led_color(int r , int g , int b){
    digitalWrite(LEDR, r);
    digitalWrite(LEDG, g);
    digitalWrite(LEDB, b);
}


//公共函数
void led_module_init(){
    pinMode(LEDR, OUTPUT);
    pinMode(LEDG, OUTPUT);
    pinMode(LEDB, OUTPUT);
    set_led_color(HIGH,HIGH,HIGH);
}

//控制LED任务
void led_control_task() {
    const int OFF = HIGH;
    const int ON = LOW;
    const int GESTURE_LIGHT_DURATION_MS = 500;//亮灯时间

    for (;;) {

        int prediction_index = 0;
        float confidence = 0.0;

        // 从推理模块获取最新结果（线程安全）
        inference_get_result(&prediction_index, &confidence);


        if (confidence > 0.65 && prediction_index != -1) {
            const char* prediction = inference_get_category_name(prediction_index);
            bool is_gesture = (strcmp(prediction,"idle")!=0&&strcmp(prediction,"unknown")!=0); //如果不是静止和未知，则认为是手势

            if (is_gesture) {
                //当识别到手势，根据预测点灯
                //Serial.print("[LED Task] Gesture Detected: ");
                //Serial.println(prediction); //串口打印出概率
                if (strcmp(prediction, "up") == 0)       set_led_color(OFF, ON, OFF); //绿色
                else if (strcmp(prediction, "down") == 0)  set_led_color(ON, ON, OFF); //黄色
                else if (strcmp(prediction, "right") == 0) set_led_color(ON, OFF, ON); //紫色
                else if (strcmp(prediction, "left") == 0)  set_led_color(OFF, OFF, ON); //蓝色

                rtos::ThisThread::sleep_for(std::chrono::milliseconds(GESTURE_LIGHT_DURATION_MS)); //通过睡眠的方式来让灯闪烁更久
                set_led_color(OFF, OFF, OFF);

                
                inference_clear_result(); //在一次闪烁之后马上清除，防止因为之前的置信度而反复闪烁
            }else{
                if(strcmp(prediction,"idle")==0){ //当识别出来是静止时
                    set_led_color(ON, OFF, OFF); //红色
                }
                else{ //此处是unknown模式
                    set_led_color(OFF, OFF, OFF); //关闭
                }
            }
        } else {
            set_led_color(OFF, OFF, OFF); //关闭
        }

        //线程在完成判断后，进行短暂休眠 ，此处决定了LED的刷新率
        rtos::ThisThread::sleep_for(std::chrono::milliseconds(100));
    }
}