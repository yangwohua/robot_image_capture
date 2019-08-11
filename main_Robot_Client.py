#!/usr/bin/python2
#coding=utf-8
'''
1.0版本
这个版本将某些控制性的变量改用字典定义
在激光测距和高度模块屏蔽的情况下执行
用来测试传图片，测试与服务器的通信

1.1版本
socket创建优化，面对对象，轻松解决连接超时问题
设置一个变量timeout， 按照需要设置成5s, 10s, 20s 等确定的值
使用线程创建socket，线程开启后用join(timeout)方法，阻塞timeout 秒 的时间
如果连接成功，阻塞立即解除，设置标志位为true
如果连接失败，阻塞timeout 秒之后，设置标志位为false

1.1.1版本
    试试将以前版本的用作心跳包测试
    在没有将控制变量为字典变量的时候是正常的，
    程序不会出现broken pipe和connect reset by peer这些错误
    #TODO 继续测试改进变量为字典，提高程序的后续可读性。

'''

import os
#from __future__ import print_function
import RPi.GPIO as GPIO
import threading
import socket              
import time 
from Queue import PriorityQueue
import json
import sys
import binascii
import cv2
import six
from PIL import Image
from io import *
from ctypes import cdll
import serial
from Raspi_BMP085 import BMP085
from Laser import Laser
import v4l2_python
reload(sys)
sys.setdefaultencoding('utf-8')
print("Program started on:"+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
#gcc wiring_pwm.c -fpic -shared -o wiring_pwm.so -lwiringPi
drive = cdll.LoadLibrary("./wiring_pwm.so")
drive.hard_pwm_init()

#GlobalVariable

ISLOCK_app = 1
ISLOCK = 0
ALIVE = 0
distance = 0
Distence_flag = 0

pgz_ID = "pgz002"
send_video_flag = True

que = PriorityQueue(50)
que2 = PriorityQueue(50)
threadLock = threading.Lock()

class PRESURE(BMP085):
    relative_altitude = 0

    def Get_Origin_Altitude(self):              #获取原始高度
        Origin_Altitude = BMP085(0x77, 3).readAltitude()
        return Origin_Altitude
    def Get_relative_altitude(self):            #计算相对高度
        self.relative_altitude = BMP085(0x77, 3).readAltitude() - self.Get_Origin_Altitude()   #相对高度 = 实时高度 - 原始高度
        if(self.relative_altitude<1):           #相对高度小于1时不计算
            self.relative_altitude = 0
  
try:                #初始化两个激光测距模块
    i = 0
    j = 0
    laser = Laser(debug = False)
    while (i<20):               #循环测试20次
        laser.fastMeasure_1()
        i = i+1
    value_laser_1 = laser.fastMeasure_1()
    while (j<20):               #循环测试20次
        laser.fastMeasure_2()
        j = j+1
    value_laser_2 = laser.fastMeasure_2()
    print "DBG: The init laser1 data is  %.2f m" % value_laser_1
    print "DBG: The init laser2 data is  %.2f m" % value_laser_2
except:
    print("Laser init error") 
    #sys.exit(0)
try:            #初始化大气压传感器
    bmp = PRESURE(0x77, 3, debug = False)  # ULTRAHIRES Mode
    value_bmp180_1 = bmp.readAltitude()
    print "DBG: The init Altitude data is  %.2f m" % value_bmp180_1 
except Exception as e:
    print("Bmp180 init error", e) 
    #sys.exit(0)

#print "bmp180 and Laser init successful"    #大气压和激光测距模块正常，程序正常运行

#########################################变量状态声明##########################################
# motion_mode = 0 ：手动模式              move_info = 0 : 上升 
# motion_mode = 1 ：自动模式              move_info = 1 : 下降     
#                                         move_info = 2 : 停止           
###############################################################################################
motion_mode = -1          
move_info = -1 
             
cmd_change = False      #命令是否改变标志位

#-------------------------拍照存图并放入队列函数--------------------------------------
#作用：
#1、调用nrf24.c中的拍照函数，take_pictures函数将获取摄像头内容，保存一张jpg格式的图片
#2、打开take_pictures函数保存的图片，读取图片内容为frame_data,将frame_data组包放入队列
#-------------------------------------------------------------------------------------
def fun_picture0():
    cam0 = v4l2_python.Camera(0)
    cam0.init_stream_on()
    cam0.filter_invalid_data()
    #try:
    while (1):
        frame_data = cam0.get_frame_data()
        #print("DBG: Camera 0 work normal")
        pic_len = hex(len(frame_data))
        hnum = int(len(frame_data)/256)         #获取图片数据高位
        lnum = int (len(frame_data)%256)        #获取图片数据低位
        packet = b"\xAA\x96\xAB\x02"+six.int2byte(lnum)+six.int2byte(hnum)+b"\x00"+frame_data+b"\x69"
        put_picture_data(packet)    
        #time.sleep(0.2)
    #except Exception as e:
            # Not entirely sure what Exceptions I'm looking for here, potentially a bad read?
        #print (e)
        #print("camera0 error") 
def fun_picture1():                                         #打开/dev/video1设备进行拍照并保存图片为 '/home/pi/Pictures/camera1/image_%d.jpg'
    cam1 = v4l2_python.Camera(1)
    cam1.init_stream_on()
    cam1.filter_invalid_data()
    try:
        while (1):
            frame_data = cam1.get_frame_data()
            #if (send_video_flag == False):
            #print("DBG: Camera 1 work normal")
            pic_len = hex(len(frame_data))
            hnum = int(len(frame_data)/256)         #获取图片数据高位
            lnum = int (len(frame_data)%256)        #获取图片数据低位
            packet = b"\xAA\x96\xAB\x02"+six.int2byte(lnum)+six.int2byte(hnum)+b"\x01"+frame_data+b"\x69"
            put_picture_data(packet)   
            #time.sleep(0.2)
    except Exception as e:
        print("camera1 error", e) 
    
def fun_picture2():
    cam2 = v4l2_python.Camera(2)
    cam2.init_stream_on()
    cam2.filter_invalid_data()
    try:
        while (1):
            frame_data = cam2.get_frame_data()
            #print("DBG: Camera 2 work normal")
            pic_len = hex(len(frame_data))
            hnum = int(len(frame_data)/256)         #获取图片数据高位
            lnum = int (len(frame_data)%256)        #获取图片数据低位
            packet = b"\xAA\x96\xAB\x02"+six.int2byte(lnum)+six.int2byte(hnum)+b"\x02"+frame_data+b"\x69"
            put_picture_data(packet)  
            #time.sleep(0.2)
    except Exception as e:
        print("camera2 error", e) 

def fun_video():
    cam3 = v4l2_python.Camera(3)
    cam3.init_stream_on()
    cam3.filter_invalid_data()
    frame_data = cam3.get_frame_data()
    try:
        while True:
            frame_data = cam3.get_frame_data()
            pic_len = hex(len(frame_data))
            hnum = int( len( frame_data)/256)
            lnum = int( len( frame_data)%256)
            packet = b"\xAA\x96\xAC\x03"+six.int2byte(lnum)+six.int2byte(hnum)+frame_data+b"\x69"       #AC代表送机器人发送到APP
            que2.put(packet)
            #time.sleep(0.3)
    except Exception as e:
        print("camera video error", e) 
#明线定时检测心跳包
def det_heartbeat(socket_server):
    global ALIVE
    while 1:
        time.sleep(12)
        if(ALIVE==0):
            print("心跳包异常")
            #socket_server.close()
            break
        ALIVE=0

#将心跳包放入队列
def EightTimeS():
    global que
    alive = "\xaa\x96\xab\x00\x00\x00\x69"
    hard_ID()       #将机器人ID放入队列
    while 1:
        que.put((1, alive))
        time.sleep(4)

#明线socket发送线程
def send_to_server(socket_server):
    global ISLOCK
    global que
    # zhengc 
    while 1:
        try:
            if(ISLOCK == 0):
                
                if (que.empty() == False):
                    data = que.get()[1]
                    socket_server.send(data)
                    if(data == "\xaa\x96\xab\x00\x00\x00\x69"):
                        print("成功发送心跳包"),
                        print("on:"+time.strftime("%H:%M:%S", time.localtime()))
                    #print(data[0:2])
                    ISLOCK = 1
                elif que.empty():
                    print(que.empty())
                elif que.full():
                    print(que.full())
        except Exception as e:
            print("Send to server error", e) 
            print("Exception on:"+time.strftime("%H:%M:%S", time.localtime()))
            # failure
            break

#明线REV funciton
def rev_from_server(socket_server):
    global ISLOCK
    global ALIVE
    while 1:
        try:
            pass
            if(ISLOCK == 1):
                rev_str = socket_server.recv(1024)
                #判断包的长度
                packet_length = len(rev_str)
                
                #如果是心跳包，作如下处理
                if(packet_length==7):
                    if( (rev_str[0]==b"\xAA") and ( ord(rev_str[1]) + ord(rev_str[6]) == 0xff ) ):
                        #print("head is right")
                        if ( rev_str[3]==b"\x00" ):
                            #print("server_scoket is alive")
                            ALIVE = 1

                #如果是ID识别包
                if(packet_length==8):
                    if((rev_str[0]==b"\xAA") and ( ord(rev_str[1]) + ord(rev_str[7]) == 0xff ) ):
                        if( rev_str[3]==b"\x01"):
                            print("应答终端ID识别包正确")
                            pass    
                        if( rev_str[3]==b"\x02"):
                            pass
                ISLOCK = 0
        except Exception as e:
            print("Rev_from server error", e)
            print("Exception on:"+time.strftime("%H:%M:%S", time.localtime()))
            socket_server.close()
            break

#暗线接收数据
def rev_from_app(socket_app):
    global  send_video_flag
    global  motion_mode
    global  move_info
    global  cmd_change
    #global  position
    while 1:
        try:
            rev_str = socket_app.recv(1024)
 
            #判断包的长度
            packet_length = len(rev_str)

            if(packet_length==8):
                if( (rev_str[0]==b"\xAA") and ( ord(rev_str[1]) + ord(rev_str[7]) == 0xff ) ):
                    #如果收到运动模式包  AA 96 CA 00 01 00 00 69
                    if( rev_str[3]==b"\x03"):                                 
                        send_video_flag = False   
                    elif( rev_str[3]==b"\x00"):
                        print("接收到运动模式包正确")
                        if(rev_str[6] == b"\x00"):
                            motion_mode = 0                    #进入自动模式                            
                            que2.put("\xAA\x96\xAC\x00\x01\x00\x01\x69")
                                
                        elif(rev_str[6] == b"\x01"):
                            motion_mode = 1                    #进入手动模式                           
                            que2.put("\xAA\x96\xAC\x00\x01\x00\x01\x69")  
                            
                        else:
                            que2.put("\xAA\x96\xAC\x00\x01\x00\x00\x69")
                                
                    #如果接收到的是运动指令包
                    elif( rev_str[3]==b"\x01"):
                        if(rev_str[6] == b"\x00"):
                            move_info = 0               #up  
                            cmd_change = True 
                            print("接收到UP")
                            que2.put("\xAA\x96\xAC\x01\x01\x00\x01\x69")

                        elif(rev_str[6] == b"\x01"):
                            move_info = 1               #down
                            cmd_change = True 
                            print("接收到DOWN")
                            que2.put("\xAA\x96\xAC\x01\x01\x00\x01\x69")

                        else:#(rev_str[6] == b"\x02"):
                            move_info = 2               #stop
                            cmd_change = True 
                            print("接收到STOP")
                            que2.put("\xAA\x96\xAC\x01\x01\x00\x01\x69")
                           
                    #如果接收到的是位置信息包
                    elif( rev_str[3]==b"\x02"):
                        if(rev_str[6] == b"\x01"):   
                            #bmp.Get_relative_altitude()
                            relative_altitude = 6
                            #relative_altitude = str(relative_altitude)
                            relative_altitude = "%.2f" %(bmp.readAltitude())
                            que2.put(b"\xAA\x96\xAC\x02\x01\x00"+relative_altitude+b"\x69")     
                            #que2.put(b"\xAA\x96\xAC\x02\x01\x00"+str(bmp.relative_altitude)+b"\x69")                                          
                            #print "DBG: The current Altitude is  %.2f m" % bmp.relative_altitude
        except Exception as e:
            print("Rev_from app error" ,e)
            print("Exception on:"+time.strftime("%H:%M:%S", time.localtime()))
            #socket_app.close()
            break
#暗线发送数据函数
def send_to_app(socket_app):
    global send_video_flag
    global que2

    while 1:
        try: 
            if (que2.empty() == False ):
                    socket_app.send(que2.get())
        except Exception as e:
            print("Socket2 Send Error", e)
            print("Exception on:"+time.strftime("%H:%M:%S", time.localtime()))
            break

#将机器人ID放入队列
def hard_ID():
    global que
    global pgz_ID
    hnum = int(len(pgz_ID)/256)         
    lnum = int (len(pgz_ID)%256)
    packet_hard_id = b"\xAA\x96\xAB\x01"+six.int2byte(lnum)+six.int2byte(hnum)+pgz_ID+b"\x69"
    que.put( (2, packet_hard_id) )

#图片数据放入队列
def put_picture_data(picture_data):
    global que    
    que.put( (3, picture_data) )           #picture_data = b"\xAA\x96\xAB\x02"+six.int2byte(lnum)+six.int2byte(hnum)+b"\x00"+frame_data+b"\x69"

class socket_init(object):
    link_check = "false"
    socket_server = None
    socket_app = None
    def creat_client(self, host, port):

        self.host_server = host
        self.port_server = int(port)
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_server.connect((self.host_server, self.port_server)) 

        time.sleep(0.5)

        self.host_app = host
        self.port_app = int(port)
        self.socket_app = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_app.connect((self.host_app, self.port_server)) 

        self.link_check = "true"
    def __del__(self):
        if(self.link_check == 'true'):
            print("close socket by _del_")
            self.socket_server.close()
            self.socket_app.close()
def auto_move():
    time.sleep(5)
    while(1):
        drive.up(512)                  #上升

        if(bmp.relative_altitude >= 0):                              #上升距离已经超过1.5米
            top_dist = laser.fastMeasure_1()
            if(top_dist <= 0.8 and top_dist != None):                #到顶部距离小于等于0.8米并且不是0
                print (top_dist)
                drive.stop()
                time.sleep(3)
                while(1):
                    drive.down(512)            #下降

                    if(bmp.relative_altitude <= 0):                 #距离地面已经不超过2米
                        ground_dist = laser.fastMeasure_2()
                        if(ground_dist <= 0.8 and top_dist != None):#到底部距离小于等于0.8米并且不是0
                            drive.stop()
                            time.sleep(1)
                            break
                break    

def start_all_thread():
    try:
       Thread1 = threading.Thread( target = EightTimeS, args = () )         #每隔8秒发送
       Thread1.setDaemon(True)
       Thread1.start()
    except:
       print ('thread1 start exception')
    
    try:
       Thread2 = threading.Thread( target = det_heartbeat, args = (client.socket_server,) )            #心跳包检测
       Thread2.setDaemon(True)
       Thread2.start()
    except:
       print ('thread2 start exception')
    
    try:
       Thread3 = threading.Thread( target = rev_from_server, args = (client.socket_server,) )          
       Thread3.setDaemon(True)
       Thread3.start()
    except:
       print ('thread3 start exception')
    
    try:
       Thread4 = threading.Thread( target = send_to_server, args = (client.socket_server,) )
       Thread4.setDaemon(True)
       Thread4.start()
    except:
       print ('thread4 start exception')
    
    try:
       Thread5 = threading.Thread( target = send_to_app, args = (client.socket_app,) )
       Thread5.setDaemon(True)
       Thread5.start()
    except:
       print ('thread5 start exception')
    
    try:
       Thread6 = threading.Thread( target = rev_from_app, args = (client.socket_app,) )
       Thread6.setDaemon(True)
       Thread6.start()
    except:
       print ('thread6 start exception')
    
    
    try:
       Thread7 = threading.Thread( target = fun_picture0, args = ( ) )
       Thread7.setDaemon(True)
       Thread7.start()
    except:
       print ('thread7 start exception')
    
    try:
       Thread8 = threading.Thread( target = fun_picture1, args = ( ) )
       Thread8.setDaemon(True)
       Thread8.start()
    except:
       print ('thread8 start exception')
    
    try:
       Thread8 = threading.Thread( target = fun_picture2, args = ( ) )
       Thread8.setDaemon(True)
       Thread8.start()
    except:
       print ('thread8 start exception')
    
    try:
       Thread9 = threading.Thread( target = fun_video, args = () )
       Thread9.setDaemon(True)
       Thread9.start()
    except:
       print ('thread9 start exception')

if __name__=="__main__":

    thread_start = 0
    network_value = 0
    manual_value = 0
    auto_value = 0
    client = socket_init()
    Thread_socket = threading.Thread( target = client.creat_client, args = (sys.argv[1], sys.argv[2], ) )
    Thread_socket.setDaemon(True)
    Thread_socket.start()

    Thread_socket.join(5)
    time.sleep(1)
    if (client.link_check) == 'true':
        start_all_thread()
    
        while(True):                                         
            if (motion_mode == 1):              #进入手动运动模式，等待接收运动指令
                if(manual_value == 0):          #manual_value初始值为0，进入这里之后加1，之后一直为1
                    print("进入手动运动模式")
                    manual_value += 1
                    auto_value = 0
                            
                if (motion_mode == 1):          
                    if(cmd_change == True):
                        cmd_change = False
                        #接收到上升指令
                        if (move_info == 0):
                            drive.up(512)
                            print("上升")                                
                        #接收到下降指令
                        elif (move_info == 1):
                            drive.down(512)
                            print("下降")
                        #接收到停止指令
                        else:                        
                            drive.stop()
                            print("停止")                     
                        que2.put("\xAA\x96\xAC\x01\x01\x00\x01\x69")  
                
            #进入自动模式，自动运动
        
            elif (motion_mode == 0):       
                #auto_move();
                if(auto_value == 0):
                    print("进入自动运动模式")           #auto_value初始值为0，进入这里之后加1，之后一直为1
                    auto_value+=1
                    manual_value = 0

                auto_move()
                sys.exit(1)

            else:
                pass
    else:
        '''
        当树莓派连接不上服务器的时候运行这个分支
        开热点，创建socket
        接收到自动运行模式的指令之后开始自动运行
        自动运行之前先打开拍照，每个摄像头单独开一个线程
        '''
        #查询关于创建热点的进程，如果存在，杀死关于创建热点的进程，避免热点创建失败      
        strtmp = os.popen("ps -a | grep create_ap") 
        cmdback = strtmp.read()
        p = str(cmdback).find('create_ap')
        if not p == -1:
            os.system("sudo killall -9 create_ap")

        strtmp = os.popen("ps -a | grep hostapd") 
        cmdback = strtmp.read()
        p = str(cmdback).find('hostapd')
        if not p == -1:
            os.system("sudo killall -9 hostapd")

        os.system("sudo create_ap wlan0 eth0 robot 24659959 &")
        print("热点创建成功")

        print("开始创建服务器socket")
        hot_point_socket = socket.socket()    
        hot_point_host = ''
        hot_point_port = 8104
        addr = (hot_point_host, hot_point_port)
        hot_point_socket.bind(addr)        # 绑定端口
        hot_point_socket.listen(5)

        to_client, addr = hot_point_socket.accept()
        print ('...connected from :', addr)

        rev_str = to_client.recv(1024)
        to_client.send("\xAA\x96\xAC\x00\x01\x00\x01\x69")
        rev_str = to_client.recv(1024)
        packet_length = len(rev_str)

        if(packet_length==8):
            if( (rev_str[0]==b"\xAA") and ( ord(rev_str[1]) + ord(rev_str[7]) == 0xff ) ):
            #motion_mode = 0
                cam0 = v4l2_python.Camera(0)
                cam1 = v4l2_python.Camera(1)
                cam2 = v4l2_python.Camera(2)
                cam3 = v4l2_python.Camera(3)
                if(rev_str[6] == b"\x00"):
                    try:
                        Thread1 = threading.Thread( target = cam0.start_capturing, args = () )
                        Thread1.setDaemon(True)
                        Thread1.start()
                    except:
                        print ('thread1 start exception')
                    try:
                        Thread2 = threading.Thread( target = cam1.start_capturing, args = () )
                        Thread2.setDaemon(True)
                        Thread2.start()
                    except:
                        print ('thread2 start exception')
                    try:
                        Thread3 = threading.Thread( target = cam2.start_capturing, args = () )
                        Thread3.setDaemon(True)
                        Thread3.start()
                    except:
                        print ('thread3 start exception')
                    try:
                        Thread4 = threading.Thread( target = cam3.start_capturing, args = () )
                        Thread4.setDaemon(True)
                        Thread4.start()
                    except:
                        print ('thread4 start exception')
                    #auto_move()
                    print("Auto move begin!!!")
                    time.sleep(300)
                    print("Auto move finish!!!")
            
                    os.system("sudo killall -9 create_ap")
                    os.system("sudo killall -9 hostapd")
                    print("program exit normally:-> close socket")
                    hot_point_socket.close()
                    to_client.close()