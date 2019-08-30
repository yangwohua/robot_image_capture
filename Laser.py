#!/usr/bin/python2
#coding=utf-8
import serial
import time
import binascii

class Laser:
    distance = None
    Distence_falg = None
    port = None

    measure_cmd1 ="\x01\x03\x00\x24\x00\x02\x84\x00"            #�����ֶ���������
    measure_cmd2 ="\x02\x03\x00\x24\x00\x02\x84\x33"            #�����ֶ���������
    def __init__(self, debug=False):
        #self.port = serial.Serial("/dev/ttyS0")
        self.port = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=3.0)
        self.debug = debug
    def fastMeasure_1(self):
        time.sleep(0.05)
        self.port.write(self.measure_cmd1)
        rcv1 = self.port.read(9)
        try:
            error_detected = int(binascii.hexlify(rcv1[5:7]), 16)
            if error_detected != 0:
                distance = int(binascii.hexlify(rcv1[5:7]), 16)
                distance = distance * 0.001  
            if (self.debug):
                print "DBG: Distance 1: %.2f m" % distance
                print "DBG: self.port.read " + str(binascii.hexlify(rcv1))
            return distance
        except Exception as e:
            print ("Error in function fastMeasure_1: "+str(e))
        
        
    def fastMeasure_2(self):
        time.sleep(0.05)
        self.port.write(self.measure_cmd2)
        try:
            rcv2 = self.port.read(9)
            error_detected = int(binascii.hexlify(rcv2[5:7]), 16)
            if error_detected != 0: 
                distance = int(binascii.hexlify(rcv2[5:7]), 16)
                distance = distance * 0.001
            if (self.debug):
                print "DBG: Distance 2: %.2f m" % distance
                print "DBG: self.port.read " + str(binascii.hexlify(rcv2))
            return distance
        except Exception as e:
            print ("Error in function fastMeasure_2: "+str(e))
            

if __name__=="__main__":
    laser = Laser(debug = True)
    while True:
        #laser.fastMeasure_1()
        laser.fastMeasure_2()
