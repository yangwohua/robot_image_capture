#!/usr/bin/python2
# coding=utf-8
import serial
import time
from binascii import unhexlify, hexlify
import threading
from crcmod import *


class Laser:
    distance = None
    Distence_falg = None
    port = None

    measure_cmd_up = "\x02\x03\x00\x24\x00\x02\x84\x33"
    measure_cmd_down = "\x01\x03\x00\x24\x00\x02\x84\x00"
    heartbeat_sign = "\x03\x02\x00\x00\xa1\xa0\x0d\x0a"

    def __init__(self, debug=False):
        # self.port = serial.Serial("/dev/ttyS0")
        self.port = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=0.3)
        self.debug = debug

    def crc16Add(self, read):
        crc16 = crcmod.mkCrcFun(
            0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
        # print(read)
        readcrcout = hex(crc16(read))
        readcrcout = read + \
            unhexlify(readcrcout[4:]) + unhexlify(readcrcout[2:4])

        return readcrcout

    def set_speed(self):
        sp_20hz = "\x02\x10\x00\x1b\x00\x01\x02\x00\x14\xb1\44"
        self.port.flushInput()
        self.port.write(sp_20hz)
        time.sleep(0.03)
        rcv1 = self.port.read(8)
        print "speed respond " + str(hexlify(rcv1))
        time.sleep(0.03)

    def fastMeasure_1(self, lock=None):
        # time.sleep(0.02)
        if lock != None:
            lock.acquire()
            if (self.debug):
                print("激光测距1获得锁")
        self.port.flushInput()
        self.port.write(self.measure_cmd_up)
        time.sleep(0.02)
        rcv1 = self.port.read(9)
        if lock != None:
            lock.release()
            if (self.debug):
                print("激光测距1释放锁")
        try:
            error_detected = int(hexlify(rcv1[5:7]), 16)
            print "DBG: self.port.read " + str(hexlify(rcv1))
            if error_detected != 0:
                distance = int(hexlify(rcv1[5:7]), 16)
                distance = distance * 0.001
                if (self.debug):
                    print("测量激光1 on:" +
                          time.strftime("%H:%M:%S", time.localtime()))
                    print "DBG: Distance 1: %.2f m" % distance
                return distance
            else:
                return
        except Exception as e:
            print ("Error in function fastMeasure_1: "+str(e))
            return "error"

    def fastMeasure_2(self, lock=None):
        # time.sleep(0.05)
        if lock != None:
            lock.acquire()
            print("激光测距2获得锁")
        self.port.flushInput()
        self.port.write(self.measure_cmd_down)
        time.sleep(0.03)
        rcv2 = self.port.read(9)
        if lock != None:
            lock.release()
            print("激光测距2释放锁")
        try:
            error_detected = int(hexlify(rcv2[5:7]), 16)
            if error_detected != 0:
                distance = int(hexlify(rcv2[5:7]), 16)
                distance = distance * 0.001
                if (self.debug):
                    print("测量激光2 on:" +
                          time.strftime("%H:%M:%S", time.localtime()))
                    print "DBG: Distance 2: %.2f m" % distance
                    print "DBG: self.port.read " + str(hexlify(rcv2))
                return distance
            else:
                return
        except Exception as e:
            print ("Error in function fastMeasure_2: "+str(e))
            return "error"


class Thread_serial(Laser):
    dis_top = None
    dis_down = None
    laser_up_error = 0
    laser_up_v0 = 0
    laser_down_error = 0
    laser_down_v0 = 0
    bmp_control = False
    heart_beat = True
    ADC_1 = None
    ADC_2 = None
    mode = 0
    reserve = None
    ras_stop_sign = False

    '''
    向上激光测距：
        1. 使用快速模式，测量指令继承自 Laser类 。
        2. 测量数据正常则返回测量数据，数据单位为 m ,默认保留两位小数，测量数据失败返回 None 。
    '''

    def fastMeasure_up(self, lock=None):
        # time.sleep(0.02)
        try:
            for i in range(2):
                self.port.flushInput()
                self.port.write(self.measure_cmd_up)
                time.sleep(0.02)
                rcv_laser_up = self.port.read(9)

            if ((rcv_laser_up[0:3]) != b"\x02\x03\x04"):
                print("laser up error")
                self.laser_up_error = self.laser_up_error + 1  # 如果串口异常，每0.5秒读到一个空值，对空值进行计数
                if self.laser_up_error == 3:  # 累计3次，也就是1.5秒内没有任何激光数据返回
                    self.dis_top = 0.3  # 让主程序跳转到下降过程
                    return
            else:
                error_detected = int(hexlify(rcv_laser_up[5:7]), 16)

                if error_detected != 0:
                    self.laser_up_error = 0
                    self.laser_up_v0 = 0
                    distance = int(hexlify(rcv_laser_up[5:7]), 16)
                    distance = distance * 0.001
                    if lock != None:
                        lock.acquire()
                    self.dis_top = distance
                    if lock != None:
                        lock.release()
                        if (self.debug):
                            print("激光测距1释放锁")
                    if (self.debug):
                        print("测量激光1 on:" +
                              time.strftime("%H:%M:%S", time.localtime()))
                        print "DBG: Distance up: %.2f m" % distance
                    return distance
                else:
                    self.laser_up_v0 = self.laser_up_v0 + 1
                    if self.laser_up_v0 == 20:
                        self.dis_top = 0.3  # 让主程序跳转到下降过程

                    if lock != None:
                        lock.acquire()
                    self.dis_top = None
                    if lock != None:
                        lock.release()
                        print("激光测距1释放锁")

                if (self.debug):
                    print "DBG: self.port.read in fastMeasure_up() " + str(hexlify(rcv_laser_up))
        except Exception as e:
            print ("Error in function fastMeasure_1: "+str(e))
            return "error"

    '''
    向下激光测距：(传入参数 : lock ,作为线程调用时使用)
        1. 使用快速模式，测量指令继承自 Laser类 。
        2. 测量数据正常则返回测量数据，数据单位为 m ,默认保留两位小数，测量数据失败返回 None 。
    '''

    def fastMeasure_down(self, lock=None):
        # time.sleep(0.02)
        for i in range(2):
            self.port.flushInput()
            self.port.write(self.measure_cmd_down)
            time.sleep(0.02)
            rcv_laser_down = self.port.read(9)

        try:
            if ((rcv_laser_down[0:3]) != b"\x01\x03\x04"):
                print("laser down error")
                self.laser_down_error = self.laser_down_error + 1
                if self.laser_down_error == 3:
                    # TODO 使用大气压返回地面
                    # self.dis_down = 0.3  # 让自动运行函数跳转到stop的条件
                    self.bmp_control = True  # 把大气压高度值来进行控制机器人
                    return
            else:
                error_detected = int(hexlify(rcv_laser_down[5:7]), 16)
                if error_detected != 0:
                    self.laser_down_error = 0
                    self.laser_down_v0 = 0
                    distance = error_detected * 0.001
                    if lock != None:
                        lock.acquire()
                        if (self.debug):
                            print("激光测距2 获得锁")
                    self.dis_down = distance
                    if lock != None:
                        lock.release()
                        if (self.debug):
                            print("激光测距2 释放锁")
                    if (self.debug):
                        print("测量激光2 on:" +
                              time.strftime("%H:%M:%S", time.localtime()))
                        print "DBG: Distance 2: %.2f m" % distance
                    return distance
                else:
                    self.laser_down_v0 += 1
                    if self.laser_down_v0 == 20:
                        # self.dis_down = 0.3  # 让自动运行函数跳转到stop的条件
                        self.bmp_control = True  # 把大气压高度值来进行控制机器人
                        return
                    if lock != None:
                        lock.acquire()
                    self.dis_down = None
                    if lock != None:
                        lock.release()
                        if (self.debug):
                            print("激光测距2释放锁")

                if (self.debug):
                    print "DBG: self.port.read in fastMeasure_down()" + str(hexlify(rcv_laser_down))
        except Exception as e:
            print ("Error in function fastMeasure_down: "+str(e))
            return "error"

    '''
    心跳包：(传入参数 : lock ,作为线程调用时使用)
        1. 检测stm32与树莓派是否能够正常通信
        2. 给stm32发数据，单片机会回复当前检测的电流
    '''

    def mcu_heartbeat(self, lock=None):

        self.port.flushInput()
        self.port.write(self.heartbeat_sign)
        time.sleep(0.02)
        # count = self.port.inWaiting()

        rcv = self.port.read(9)
        if (self.debug):
            print("心跳 on:" +
                  time.strftime("%H:%M:%S", time.localtime()))
            print "心跳回应数据 " + str(hexlify(rcv))
        if ((rcv[0:3]) != b"\x03\x02\x04"):
            self.stm_err_val = self.stm_err_val + 1
        else:
            self.stm_err_val = 0
            #
            if lock != None:
                lock.acquire()
            self.ADC_1 = int(hexlify(rcv[3:5]), 16)
            self.ADC_2 = int(hexlify(rcv[5:7]), 16)
            if (self.debug):
                print(self.ADC_1, self.ADC_2)
            if lock != None:
                lock.release()
            # print(ADC_1, ADC_2)

        if self.stm_err_val == 3:
            print("stm32_heartbeat == False")
            if lock != None:
                lock.acquire()
            self.heart_beat = False
            if lock != None:
                lock.release()

    '''
    线程监听方法：(传入参数 : lock ,作为线程调用时使用)
        1. 用轮询机制对树莓派串口资源进行管理
        2. 在主程序初始化完成之后，树莓派与单片机的启动通信正常之后开启线程调用此函数
        3. 如果停止信号为真，推出循环，结束与单片机的通信
        4. 通过对 mode 参数的值来执行某一个或几个模式。
    '''

    def start(self, bmp_init_val=1.36):
        bmp_value = hex(int(bmp_init_val * 1000))
        str_list = list(bmp_value)
        if len(str_list) == 5:
            str_list.insert(2, '0')      # 位数不足补0
        bmp_value = "".join(str_list)
        # print(bmp_value)
        start_sign = "\x03\x01" + \
            unhexlify(bmp_value[4:]) + unhexlify(bmp_value[2:4])
        start_sign = self.crc16Add(start_sign)
        start_sign = start_sign + "\x0d\x0a"

        # self.port.flushInput()
        self.port.write(start_sign)
        time.sleep(0.03)
        while True:
            count = self.port.inWaiting()
            # print count
            if count != 0:
                rcv = self.port.read(9)
                if rcv[0:3] == b"\x03\x01\x04":
                    print "Communication is normal"
                    break
                else:
                    print "Communication is failed"
                    break

    def finish(self):
        error_cnt = 0
        finish_sign = "\x03\x03\x00\x00\xf0\x60\x0d\x0a"
        while True:
            self.port.flushInput()
            self.port.write(finish_sign)
            time.sleep(0.05)
            recv = self.port.read(9)
            print (hexlify(recv))
            if recv == b"\x03\x03\x04\x00\x00\x00\x00\xd9\xf3":
                print("结束回应正确")
                error_cnt = 0
                return 0
            else:
                print("结束回应错误")
                error_cnt += 1
                if error_cnt == 10:
                    return -1

    def thread_serial(self, lock=None):
        while True:
            # print(self.mode)
            if (self.mode & 0x01):  # 模式1：心跳包
                self.mcu_heartbeat(lock)

            if (self.mode & 0x02):  # 模式2：顶部激光测距
                self.fastMeasure_up(lock)

            if (self.mode & 0x04):  # 模式3：底部激光测距
                self.fastMeasure_down(lock)
            if lock != None:
                lock.acquire()
            if self.ras_stop_sign == True:
                return
            if lock != None:
                lock.release()
            time.sleep(0.01)


if __name__ == "__main__":
    laser = Laser(debug=True)
    while 1:
        laser.fastMeasure_1()
    # serial_monitor = Thread_serial()
    # #serial_monitor.debug = True
    # lock = threading.Lock()
    # serial_monitor.start()
    # serial_monitor.mode = 5
    # Thread_stm = threading.Thread(
    #     target=serial_monitor.thread_serial, args=(lock, ))
    # Thread_stm.setDaemon(True)
    # Thread_stm.start()
    # while True:
    #     try:
    #         time.sleep(5)
    #         serial_monitor.ras_stop_sign = True
    #         time.sleep(0.3)
    #         serial_monitor.finish()
    #         break
    #     except Exception as e:
    #         print("1 finish!!!", e)
    #         serial_monitor.ras_stop_sign = True
    #         time.sleep(0.02)
    #         serial_monitor.finish()
    #         break
    # else:
    #     serial_monitor.ras_stop_sign = True
    #     time.sleep(0.02)
    #     print("3 finish!!!")
    #     serial_monitor.finish()
    # laser.fastMeasure_2(lock)
    # commu_stm = Commu_stm32()
    # commu_stm.start()
    # Thread_stm = threading.Thread( target = commu_stm.heartbeat, args = () )
    # Thread_stm.setDaemon(True)
    # Thread_stm.start()
    # while True:
    #     if (raw_input("输入s并按回车结束程序") == "s"):
    #         commu_stm.break_point = True
    #         break
    # commu_stm.finish()
