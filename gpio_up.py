#!/usr/bin/python2
#coding=utf-8

import os
from ctypes import cdll

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
drive = cdll.LoadLibrary("%s/wiring_pwm.so" %BASE_DIR)
drive.hard_pwm_init()
drive.up(180)

try:
    while True:
        pass
except:
    drive.stop()
    drive.clear()