#!/usr/bin/python2
#coding=utf-8
import serial
import time
from binascii import unhexlify,hexlify
import threading
from crcmod import *
class Laser:
    distance = None
    Distence_falg = None
    port = None

    measure_cmd1 ="\x01\x03\x00\x24\x00\x02\x84\x00"            #�����ֶ���������
    measure_cmd2 ="\x02\x03\x00\x24\x00\x02\x84\x33"            #�����ֶ���������
    def __init__(self, debug=False):
        #self.port = serial.Serial("/dev/ttyS0")
        self.port = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=5.0)
        self.debug = debug
    def crc16Add(self, read):
        crc16 = crcmod.mkCrcFun(0x18005,rev=True,initCrc=0xFFFF,xorOut=0x0000)
        print(read)
        readcrcout = hex(crc16(read))
        readcrcout = read + unhexlify(readcrcout[4:]) +unhexlify(readcrcout[2:4])
        
        return readcrcout

    def fastMeasure_1(self ,lock):
        time.sleep(0.02)
        lock.acquire()
        print("心跳包获得锁")
        self.port.flushInput()
        self.port.write(self.measure_cmd1)
        rcv1 = self.port.read(9)
        lock.release()
        print("心跳包释放锁")
        try:
            error_detected = int(hexlify(rcv1[5:7]), 16)
            if error_detected != 0:
                distance = int(hexlify(rcv1[5:7]), 16)
                distance = distance * 0.001  
                if (self.debug):
                    print "DBG: Distance 1: %.2f m" % distance
                    print "DBG: self.port.read " + str(hexlify(rcv1))
                return distance
        except Exception as e:
            print ("Error in function fastMeasure_1: "+str(e))
            return "error"
        
        
    def fastMeasure_2(self, lock):
        lock.acquire()
        print("心跳包获得锁")
        self.port.flushInput()
        self.port.write(self.measure_cmd2)
        rcv2 = self.port.read(9)
        lock.release()
        print("心跳包释放锁")
        try:
            error_detected = int(hexlify(rcv2[5:7]), 16)
            if error_detected != 0:
                distance = int(hexlify(rcv2[5:7]), 16)
                distance = distance * 0.001  
                if (self.debug):
                    print "DBG: Distance 2: %.2f m" % distance
                    print "DBG: self.port.read " + str(hexlify(rcv2))
                return distance
        except Exception as e:
            print ("Error in function fastMeasure_2: "+str(e))
            return "error"
        

class Commu_stm32(Laser):
    break_point = False
    def start(self, bmp_init_val = 1.36): 
        bmp_value = hex(int(bmp_init_val * 1000))
        str_list = list(bmp_value)
        if len(str_list) == 5:
            str_list.insert(2,'0')      # 位数不足补0
        bmp_value = "".join(str_list)
        print(bmp_value)
        start_sign = "\x03\x01"+ unhexlify(bmp_value[4:]) +unhexlify(bmp_value[2:4])
        start_sign = self.crc16Add(start_sign)
        start_sign = start_sign + "\x0d\x0a"

        self.port.flushInput()
        self.port.write(start_sign)
        # while True:
        #     count = self.port.inWaiting()
        #     #print count
        #     if count != 0:
        #         rcv = self.port.read(9)
        #         if rcv[0:3] == "\x03\x01\x04":
        #             print "Communication is normal"
        #             break
        #         else:
        #             print "Communication is failed"
        #             break
    def heartbeat(self, lock = False):
            #time.sleep(1)
            heartbeat_sign = "\x03\x02\x00\x00\xa1\xa0\x0d\x0a"
            while True:
                lock.acquire()
                print("心跳包获得锁")
                self.port.flushInput()
                self.port.write(heartbeat_sign)
                time.sleep(0.05)
                lock.release()
                print("心跳包释放锁")
                #rcv = self.port.read(9)  
                # print "DBG: self.port.read " + str(binascii.hexlify(rcv))
                # ADC_1 = int(binascii.hexlify(rcv[3:5]), 16)
                # ADC_2 = int(binascii.hexlify(rcv[5:7]), 16)
                # print(ADC_1, ADC_2)
                if self.break_point == True:
                    print("stop")
                    break    
    def finish(self):
        finish_sign = "\x03\x03\x00\x00\xf0\x60\x0d\x0a"
        self.port.write(finish_sign)

if __name__=="__main__":
    laser = Laser(debug = True)
    while True:
        #laser.fastMeasure_1()
        laser.fastMeasure_2()
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
