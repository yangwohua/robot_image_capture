#!/usr/bin/python2
#coding=utf-8
import RPi.GPIO as GPIO
import time
class watch:
    IN1 = 13                  
    
    def __init__(self, debug=False):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)   
        GPIO.setup(self.IN1, GPIO.OUT)      #设定电机对应的GPIO号为输出引脚
        print("GPIO-27引脚启动脉冲")
    def start(self):
        GPIO.output(self.IN1,GPIO.LOW)
        time.sleep(0.02)
        GPIO.output(self.IN1,GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.IN1,GPIO.LOW)
    def detect(self):
        while True:
            GPIO.output(self.IN1,GPIO.LOW)
            time.sleep(0.02)
            GPIO.output(self.IN1,GPIO.HIGH)
            time.sleep(0.02)
            GPIO.output(self.IN1,GPIO.LOW)
    def _del_(self):  
        GPIO.cleanup()


