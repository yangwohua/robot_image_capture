#!/usr/bin/python2
#coding=utf-8
from binascii import unhexlify,hexlify
from crcmod import *
import serial

# CRC16-MODBUS
def crc16Add(read):
    crc16 = crcmod.mkCrcFun(0x18005,rev=True,initCrc=0xFFFF,xorOut=0x0000)
    print(read)
    readcrcout = hex(crc16(read))
    readcrcout = read + unhexlify(readcrcout[4:]) +unhexlify(readcrcout[2:4])

    return readcrcout
 
if __name__ == '__main__':
    start_sign = "\x03\x03\x00\x00"
    start_sign = crc16Add(start_sign)

    port = serial.Serial("/dev/ttyAMA0", baudrate=115200)

    port.write(start_sign)




