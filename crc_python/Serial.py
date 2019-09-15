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

    def __init__(self, debug=False):
        # self.port = serial.Serial("/dev/ttyS0")
        self.port = serial.Serial("/dev/ttyAMA0", baudrate=115200)
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
            print("激光测距1获得锁")
        self.port.flushInput()
        self.port.write(self.measure_cmd_up)
        time.sleep(0.02)
        rcv1 = self.port.read(9)
        if lock != None:
            lock.release()
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


class Commu_stm32(Laser):
    break_point = False
    exit_value = 0

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

    def heartbeat(self, lock=None):
        heartbeat_sign = "\x03\x02\x00\x00\xa1\xa0\x0d\x0a"
        # while True:
        if lock != None:
            lock.acquire()
            print("心跳包获得锁")
        # self.port.flushInput()
        self.port.write(heartbeat_sign)
        # print("send " + str(hexlify(heartbeat_sign)))
        time.sleep(0.02)
        rcv = self.port.read(9)
        # print("recv :" + str(hexlify(rcv)))
        if lock != None:
            lock.release()
            print("心跳包释放锁")
        if (hexlify(rcv[0:2]) != "\x03\x02\x04"):
            self.exit_value = self.exit_value + 1
        else:
            self.exit_value = 0
            # print "DBG: self.port.read " + str(hexlify(rcv))
            ADC_1 = int(hexlify(rcv[3:5]), 16)
            ADC_2 = int(hexlify(rcv[5:7]), 16)
            # print(ADC_1, ADC_2)
            if self.break_point == True:
                print("stop")
                return
        if self.exit_value == 70:
            print("exit value == True")
            exit(1)

    def finish(self):
        error_cnt = 0
        finish_sign = "\x03\x03\x00\x00\xf0\x60\x0d\x0a"
        while True:
            self.port.write(finish_sign)
            time.sleep(0.05)
            recv = self.port.read(9)
            print (hexlify(recv))
            if recv == b"\x03\x03\x04\x00\x00\x00\x00\xd9\xf3":
                print("结束回应正确")
                error_cnt = 0
                break
            else:
                print("结束回应错误")
                error_cnt += 1
                if error_cnt == 10:
                    break


class Thread_serial(Commu_stm32):
    dis_top = None
    dis_down = None
    heart_beat = None
    ADC_1 = None
    ADC_2 = None
    mode = None
    reserve = None

    def fastMeasure_up(self, lock=None):
        # time.sleep(0.02)
        self.port.flushInput()
        self.port.write(self.measure_cmd_up)
        time.sleep(0.02)
        rcv_laser_up = self.port.read(9)

        try:
            error_detected = int(hexlify(rcv_laser_up[5:7]), 16)
            print "DBG: self.port.read " + str(hexlify(rcv_laser_up))
            if error_detected != 0:
                distance = int(hexlify(rcv_laser_up[5:7]), 16)
                distance = distance * 0.001
                if lock != None:
                    lock.acquire()
                self.dis_top = distance
                if lock != None:
                    lock.release()
                    print("激光测距1释放锁")
                if (self.debug):
                    print("测量激光1 on:" +
                          time.strftime("%H:%M:%S", time.localtime()))
                    print "DBG: Distance 1: %.2f m" % distance

            else:
                if lock != None:
                    lock.acquire()
                self.dis_top = None
                if lock != None:
                    lock.release()
                    print("激光测距1释放锁")
        except Exception as e:
            print ("Error in function fastMeasure_1: "+str(e))
            return "error"

    def fastMeasure_down(self, lock=None):
        # time.sleep(0.02)
        self.port.flushInput()
        self.port.write(self.measure_cmd_down)
        time.sleep(0.02)
        rcv_laser_down = self.port.read(9)

        try:
            error_detected = int(hexlify(rcv_laser_down[5:7]), 16)
            print "DBG: self.port.read " + str(hexlify(rcv_laser_down))
            if error_detected != 0:
                distance = error_detected * 0.001
                if lock != None:
                    lock.acquire()
                    print("激光测距2 获得锁")
                self.dis_down = distance
                if lock != None:
                    lock.release()
                    print("激光测距2 释放锁")
                if (self.debug):
                    print("测量激光2 on:" +
                          time.strftime("%H:%M:%S", time.localtime()))
                    print "DBG: Distance 2: %.2f m" % distance

            else:
                if lock != None:
                    lock.acquire()
                self.dis_down = None
                if lock != None:
                    lock.release()
                    print("激光测距2释放锁")
        except Exception as e:
            print ("Error in function fastMeasure_down: "+str(e))
            return "error"

    def heartbeat(self, lock=None):
        heartbeat_sign = "\x03\x02\x00\x00\xa1\xa0\x0d\x0a"

        self.port.write(heartbeat_sign)
        time.sleep(0.02)
        rcv = self.port.read(9)

        if (rcv[0:2] != b"\x03\x02\x04"):
            self.exit_value = self.exit_value + 1
        else:
            self.exit_value = 0
            # print "DBG: self.port.read " + str(hexlify(rcv))
            if lock != None:
                lock.acquire()
            self.ADC_1 = int(hexlify(rcv[3:5]), 16)
            self.ADC_2 = int(hexlify(rcv[5:7]), 16)
            print(self.ADC_1, self.ADC_2)
            if lock != None:
                lock.release()
            # print(ADC_1, ADC_2)

        if self.exit_value == 70:
            print("exit value == True")
            if lock != None:
                lock.acquire()
            self.is_alive_stm = False
            if lock != None:
                lock.release()

    def thread_serial(self, lock=None):
        while True:
            print(self.mode)
            if (self.mode & 0x01):  # 模式1：心跳包
                self.heartbeat(lock)

            if (self.mode & 0x02):  # 模式2：顶部激光测距
                self.fastMeasure_up(lock)

            if (self.mode & 0x04):  # 模式3：底部激光测距
                self.fastMeasure_down(lock)
            time.sleep(0.02)


if __name__ == "__main__":
    thread_s = Thread_serial(debug=True)
    thread_s.mode = 5
    thread_s.thread_serial()
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
