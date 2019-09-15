#!/usr/bin/python2
# coding=utf-8
from Serial import Commu_stm32, Thread_serial
import threading
import time
from multiprocessing import Process
serial_monitor = Thread_serial()
serial_monitor.debug = True
lock = threading.Lock()
# serial_monitor.start()

serial_monitor.mode = 1
Thread_stm = threading.Thread(
    target=serial_monitor.thread_serial, args=(lock,))
Thread_stm.setDaemon(True)
Thread_stm.start()
# t = Process(target=serial_monitor.thread_serial, args=())
# # 守护进程必须在开启子进程前开启
# t.daemon = True
# t.start()
while True:
    try:
        pass
        print("运行pass")
        time.sleep(0.02)
        # serial_monitor.fastMeasure_1()
    except KeyboardInterrupt:
        # serial_monitor.finish()
        break

if __name__ == "__main__":
    pass
