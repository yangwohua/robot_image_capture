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
import threading
import multiprocessing 
import socket              
import time 
from Queue import PriorityQueue
import json
import sys
import binascii
import six
from io import *
from ctypes import cdll
import serial
from Raspi_BMP085 import BMP085
from Serial import Laser, Thread_serial
import v4l2_python
reload(sys)
sys.setdefaultencoding('utf-8')
print("Program started on:"+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
#gcc wiring_pwm.c -fpic -shared -o wiring_pwm.so -lwiringPi

	
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
drive = cdll.LoadLibrary("%s/wiring_pwm.so" %BASE_DIR)
drive.hard_pwm_init()

que = PriorityQueue(50)
que2 = PriorityQueue(50)
threadLock = threading.Lock()

class PRESURE(BMP085):
    Origin_Altitude = 0.01
    relative_altitude = 0.01

    def Get_Origin_Altitude(self):              #获取原始高度
        self.Origin_Altitude = BMP085(0x77, 1).readAltitude()

    def Get_relative_altitude(self):            #计算相对高度
        while 1:
            
            re_altitude = BMP085(0x77, 1).readAltitude() - self.Origin_Altitude   #相对高度 = 实时高度 - 原始高度
            # if(re_altitude < 1.0):           #相对高度小于1时不计算
            #     self.relative_altitude = 0.0
            # else:
            self.relative_altitude = re_altitude
            time.sleep(0.05)

  
try:                #初始化两个激光测距模块
    i = 0
    j = 0
    laser = Laser(debug = False)
    while (i<10):               #循环测试10次
        value_laser_up = laser.fastMeasure_1()
        i = i+1
        if value_laser_up == "error":
            break
    while (j<10):               #循环测试10次
        value_laser_down = laser.fastMeasure_2()
        j = j+1
        if value_laser_down == "error":
            break
    if value_laser_up or value_laser_down is not "error":
        print "DBG: The init laser1 data is  %.2f m" % value_laser_up
        print "DBG: The init laser2 data is  %.2f m" % value_laser_down
except Exception as e:
    print("Laser init error", e) 
    #sys.exit(0)
try:            #初始化大气压传感器
    bmp = PRESURE(0x77, 1, debug = False)  # ULTRAHIRES Mode

    bmp.Get_Origin_Altitude()
    print "DBG: The init Altitude data is  %.2f m" % bmp.Origin_Altitude

    value_bmp180 = bmp.readAltitude()
    print "DBG: The init Altitude data is  %.2f m" % value_bmp180
except Exception as e:
    print("Bmp180 init error", e) 
    sys.exit(0)
#init_position = "%.2f" %value_laser_2
#TODO 下面的init_position 变量为测试使用，实际使用时使用上面的激光测量出来的到地距离
init_position = 0.50
print "bmp180 and Laser init successful"    #大气压和激光测距模块正常，程序正常运行

global cam0,cam1,cam2,cam3
cam0 = v4l2_python.Camera(0)
cam1 = v4l2_python.Camera(1)
cam2 = v4l2_python.Camera(2)
cam3 = v4l2_python.Camera(3)
#-------------------------拍照存图并放入队列函数--------------------------------------
#作用：
#1、调用nrf24.c中的拍照函数，take_pictures函数将获取摄像头内容，保存一张jpg格式的图片
#2、打开take_pictures函数保存的图片，读取图片内容为frame_data,将frame_data组包放入队列
#-------------------------------------------------------------------------------------
def fun_picture0():
    
    cam0.init_stream_on()
    cam0.filter_invalid_data()
    
    while (1):
        try:
            frame_data = cam0.get_frame_data()
            #print("DBG: Camera 0 work normal")
            #pic_len = hex(len(frame_data))
            hnum = int(len(frame_data)/256)         #获取图片数据高位
            lnum = int (len(frame_data)%256)        #获取图片数据低位
            packet = b"\xAA\x96\xAB\x02"+six.int2byte(lnum)+six.int2byte(hnum)+b"\x00"+frame_data+b"\x69"
            put_picture_data(packet)    
            #time.sleep(0.2)
        except Exception as e:
            print("camera0 exit", e) 
            return 0
def fun_picture1():                                         #打开/dev/video1设备进行拍照并保存图片为 '/home/pi/Pictures/camera1/image_%d.jpg'
    
    cam1.init_stream_on()
    cam1.filter_invalid_data()
    
    while (1):
        try:
            frame_data = cam1.get_frame_data()
            #if (send_video_flag == False):
            #print("DBG: Camera 1 work normal")
            #pic_len = hex(len(frame_data))
            hnum = int(len(frame_data)/256)         #获取图片数据高位
            lnum = int (len(frame_data)%256)        #获取图片数据低位
            packet = b"\xAA\x96\xAB\x02"+six.int2byte(lnum)+six.int2byte(hnum)+b"\x01"+frame_data+b"\x69"
            put_picture_data(packet)   
            #time.sleep(0.2)
        except Exception as e:
            print("camera1 exit", e) 
            return 0
def fun_picture2():
    
    cam2.init_stream_on()
    cam2.filter_invalid_data()
    while (1):
        try:
            frame_data = cam2.get_frame_data()
            #print("DBG: Camera 2 work normal")
            #pic_len = hex(len(frame_data))
            hnum = int(len(frame_data)/256)         #获取图片数据高位
            lnum = int (len(frame_data)%256)        #获取图片数据低位
            packet = b"\xAA\x96\xAB\x02"+six.int2byte(lnum)+six.int2byte(hnum)+b"\x02"+frame_data+b"\x69"
            put_picture_data(packet)  
            #time.sleep(0.2)
        except Exception as e:
            print("camera2 exit", e) 
            return 0
def fun_video():   
    cam3.init_stream_on()
    cam3.filter_invalid_data()
    frame_data = cam3.get_frame_data()
   
    while (1):
        try:
            frame_data = cam3.get_frame_data()
            if (so_deal.send_video_flag == False):
                #print("开始传输图片到手机")
                #pic_len = hex(len(frame_data))
                hnum = int( len( frame_data)/256)
                lnum = int( len( frame_data)%256)
                packet = b"\xAA\x96\xAC\x03"+six.int2byte(lnum)+six.int2byte(hnum)+frame_data+b"\x69"       #AC代表送机器人发送到APP
                que2.put(packet)

                so_deal.send_video_flag = True    
            time.sleep(0.05)
        except Exception as e:
            print("camera video exit", e) 
            return 0

#将心跳包放入队列
def EightTimeS():
    global que
    alive = "\xaa\x96\xab\x00\x00\x00\x69"
    hard_ID()       #将机器人ID放入队列
    while 1:
        que.put((1, alive))
        #print("put 心跳包成功"), 
        #print("on:"+time.strftime("%H:%M:%S", time.localtime()))
        time.sleep(4)

#将机器人ID放入队列
def hard_ID():
    global que
    pgz_ID = "pgz002"
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
        try:
            self.socket_server.connect((self.host_server, self.port_server)) 
        except:
            print("connection timeout")

        time.sleep(0.5)

        self.host_app = host
        self.port_app = int(port)
        self.addr = (self.host_app, self.port_app)
        self.socket_app = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket_app.connect(self.addr) 
        except:
            print("connection timeout")
        else:
            print ('...connected to :', self.addr)
        self.link_check = "true"

    def __del__(self):
        if(self.link_check == 'true'):
            print("close socket by _del_")
            self.socket_server.close()
            self.socket_app.close()
            self.link_check = "false"
class socket_deal(socket_init):
    #########################################变量状态声明##########################################
    # motion_mode = 0 ：手动模式              move_info = 0 : 上升 
    # motion_mode = 1 ：自动模式              move_info = 1 : 下降     
    #                                        move_info = 2 : 停止           
    ###############################################################################################
    is_connected = True
    is_pause = False
    send_video_flag = True
    cmd_change = False
    motion_mode = -1
    move_info = -1    
    ISLOCK = False
    ALIVE = True
    #明线定时检测心跳包
    def det_heartbeat(self, socket_server):
        while 1:
            time.sleep(12)
            if(self.ALIVE == 0):
                print("心跳包异常")
                #socket_server.close()
                break
            self.ALIVE = 0

    '''
    暗线发送数据函数:
        检查队列2是否为空，不为空的话发送数据
        专门将需要发送给手机APP的数据经过暗线socket发送到服务器
        如果socket断开连接，捕获异常并退出该函数，连接断开标志位 is_connect置为 True
    '''
    def send_to_app(self, socket_app, que_app):
        while 1:
            try: 
                if (que_app.empty() == False ):
                        socket_app.send(que_app.get())
            except Exception:
                self.is_connected = False
                #drive.stop()
                #print("Socket2 Send Error", e)
                print("Socket sent to app exit on:"+time.strftime("%H:%M:%S", time.localtime()))
                break
    #明线socket发送线程
    def send_to_server(self, socket_server, que_server):
        while 1:
            try:
                if(self.ISLOCK == 0):
                    
                    if (que_server.empty() == False):
                        data = que_server.get()[1]
                        socket_server.send(data)
                        self.ISLOCK = 1

            except Exception:
                self.is_connected = False
                #print("Send to server error", e) 
                print("Send to server exit on:"+time.strftime("%H:%M:%S", time.localtime()))
                #drive.stop()
                break
    def rev_from_server(self, socket_server):
        while 1:
            try:
                if(self.ISLOCK == 1):
                    rev_str = socket_server.recv(1024)
                    #判断包的长度
                    packet_length = len(rev_str)
                    
                    #如果是心跳包，作如下处理
                    if(packet_length==7 or packet_length==8):
                        if( (rev_str[0]==b"\xAA") and ( ord(rev_str[1]) + ord(rev_str[packet_length-1]) == 0xff ) ):
                            if ( rev_str[3]==b"\x00" ):
                                #print("server_scoket is alive")
                                self.ALIVE = 1
                   
                            elif( rev_str[3]==b"\x01"):           #如果是ID识别包
                                #print("应答终端ID识别包正确")
                                pass    
                            elif( rev_str[3]==b"\x02"):
                                pass
                    self.ISLOCK = 0
            except Exception:
                self.is_connected = False
                #drive.stop()
                #print("Rev_from server error", e)
                print("Rev_from server exit on:"+time.strftime("%H:%M:%S", time.localtime()))
                break
    '''
    暗线接收数据:
        接收服务器转发的APP端数据，并进行处理
        如果socket断开连接，捕获异常并退出该函数，连接断开标志位 is_connect置为 True

    '''
    def rev_from_app(self, socket_app, que_app):
        while 1:
            try:
                rev_str = socket_app.recv(1024)
    
                #判断包的长度
                packet_length = len(rev_str)

                if(packet_length == 8 or packet_length == 9 ):
                    if( (rev_str[0]==b"\xAA") and ( ord(rev_str[1]) + ord(rev_str[packet_length-1]) == 0xff ) ):
                        #如果收到运动模式包  AA 96 CA 00 01 00 00 69
                        if( rev_str[3]==b"\x03"):               #任务标识码 = 0x03 发送图片到手机                               
                            self.send_video_flag = False  

                        elif(rev_str[3]==b"\x04"):
                            brige_hight = ord(rev_str[7]) * 256 + ord(rev_str[6])
                            print "桥的高度是： "+ str(brige_hight)
                            que_app.put("\xAA\x96\xAC\x04\x01\x00\x01\x69")   

                        elif( rev_str[3]==b"\x00"):             #任务标识码 = 0x00 运动模式包
                            print("接收到运动模式包正确")
                            if(rev_str[6] == b"\x00"):
                                self.motion_mode = 0                  #进入自动模式                            
                                que_app.put("\xAA\x96\xAC\x00\x01\x00\x01\x69")
    
                            else:
                                que_app.put("\xAA\x96\xAC\x00\x01\x00\x00\x69")
        
                        elif( rev_str[3]==b"\x01"):             #任务标识码 = 0x01  运动指令包
                            if(rev_str[6] == b"\x00"):
                                self.move_info = 0               #up  
                                self.cmd_change = True 
                                print("接收到UP")
                                que_app.put("\xAA\x96\xAC\x01\x01\x00\x01\x69")

                            elif(rev_str[6] == b"\x01"):
                                self.move_info = 1               #down
                                self.cmd_change = True 
                                print("接收到DOWN")
                                que_app.put("\xAA\x96\xAC\x01\x01\x00\x01\x69")

                            elif(rev_str[6] == b"\x02"):
                                self.move_info = 2               #stop
                                self.cmd_change = True 
                                self.is_pause = True
                                print self.is_pause
                                print("接收到STOP")
                                que_app.put("\xAA\x96\xAC\x01\x01\x00\x01\x69")
                            elif(rev_str[6] == b"\x03"):
                                self.move_info = 3               #break
                                self.cmd_change = True 
                                self.is_pause = False
                                print self.is_pause
                                print("接收到BREAK")
                                que_app.put("\xAA\x96\xAC\x01\x01\x00\x01\x69")
                            else:
                                que_app.put("\xAA\x96\xAC\x01\x01\x00\x00\x69")   
                        
                        elif( rev_str[3]==b"\x02"):         #任务标识码 = 0x02  位置信息包
                            if(rev_str[6] == b"\x01"):   
                                #bmp.Get_relative_altitude()
                                re_altitude = "%.2f" %bmp.relative_altitude
                                #relative_altitude = "%.2f" %(bmp.readAltitude())
                                que_app.put(b"\xAA\x96\xAC\x02\x01\x00"+re_altitude+b"\x69")     
                    
                        else:
                            que_app.put("\xAA\x96\xAC\x04\x01\x00\x01\x69")   
            except Exception as e:
                self.is_connected = False
                #drive.stop()
                print("Rev_from app error" ,e)
                print("Rev_from app exit on:"+time.strftime("%H:%M:%S", time.localtime()))
                break

def auto_move_wifi():
    time.sleep(2)
    while(1): 
        drive.up(212)                                               #上升，上升之后进行判断
        while(bmp.relative_altitude >= 0):                             #上升距离已经超过需要高度,用来计算激光可测安全距离： 需要高度 = 桥高 - 50m 
            top_dist = laser.fastMeasure_1()
            if(top_dist <= 1.5 and top_dist != None):               #到顶部距离小于等于1.5米并且不是0， 如果满足条件，减速
                print (top_dist)
                drive.stop()
                time.sleep(1)
                top_dist = laser.fastMeasure_1()
                while(top_dist >= 0.4 and top_dist != None):        #再进行判断，如果顶部距离大于0.4米，继续上升
                    top_dist = laser.fastMeasure_1()
                    drive.up(112)
                else:
                    drive.stop()
                    time.sleep(2)
                    drive.down(180)            #下降
                    low_speed_position = init_position + 0.50
                    #print "It is time to lower the speed" + str(low_speed_position)
                    print type(bmp.relative_altitude), bmp.relative_altitude
                    while(bmp.relative_altitude <= 10.0):                 #距离地面已经不超过10米
                        ground_dist = laser.fastMeasure_2()
                        if( (ground_dist <= (low_speed_position) ) and (ground_dist != None)):#到底部距离小于等于1.0米并且不是0
                            print (ground_dist)
                            drive.stop()
                            time.sleep(1)
                            ground_dist = laser.fastMeasure_2()
                            while(ground_dist >= init_position and ground_dist != None):        #再进行判断，如果顶部距离大于0.4米，继续上升
                                ground_dist = laser.fastMeasure_2()
                                print "It is time to stop" + str(init_position)
                                drive.down(112)
                            else:
                                drive.stop()
                                time.sleep(2)
                            print("Program exit normally")
                            return 0
'''
上升过程：

'''
def up_function(serial_monitor, lock = None):

    serial_monitor.mode = 3
    time.sleep(0.5)
    drive.up(212)
    try:
        while True:
            if serial_monitor.heart_beat == False:                      #判断单片机心跳，如果停止，进入紧急下降处理
                raise Exception
            if so_deal.is_pause and so_deal.is_connected == True:       #如果有暂停指令就让机器人停止，否则机器人上升
                while True:
                    #print("is pause!!!")
                    if (so_deal.cmd_change == True):
                        so_deal.cmd_change = False

                        if lock!=None:
                            lock.acquire()
                        top_dist = serial_monitor.dis_top
                        if lock!=None:
                            lock.release()
                        #lock.release()
                        
                        if so_deal.move_info == 0:                          #上升指令 move_info 等于 0
                            if(top_dist >= 1.0 or top_dist == None):       #到顶部距离大于等于1米并且不是0, 小于1米不执行上升
                                print(top_dist)
                                drive.up(112)
                                time.sleep(1)
                                drive.stop()
                            else:
                                drive.stop()
                    
                        elif so_deal.move_info == 1:                        #下降指令 move_info 等于 1
                            drive.down(112)
                            time.sleep(1)
                            drive.stop()
                            so_deal.move_info = -1

                        elif so_deal.move_info == 2:                        #停止指令 move_info 等于 2
                            drive.stop()
                        
                        elif so_deal.move_info == 3:
                            drive.up(212)
                            break
            if lock!=None:
                lock.acquire()
            top_dist = serial_monitor.dis_top
            if lock!=None:
                lock.release()
                print(top_dist)
            #TODO

            if top_dist != None:
                top_dist = 2.2
            if top_dist <= 2.0:
                drive.up(112)
            
            if top_dist <= 0.4 :#TODO 加入到顶的检测开关
                drive.stop()
                time.sleep(1)
                break

    except (Exception, KeyboardInterrupt) as e:
        if lock!=None:
            lock.acquire()
        while serial_monitor.ras_stop_sign != True:
            serial_monitor.ras_stop_sign = True
        if lock!=None:
            lock.release()
            time.sleep(0.2)
        serial_monitor.finish()                 #不让单片机接管
        while 1:
            drive.down(121)
            down_dist = serial_monitor.fastMeasure_down()
            if (down_dist - value_laser_down) <= 0.5 or bmp.relative_altitude <= 0:
                drive.stop()   
                 
        sys.exit(1)

'''
下降过程：

'''
def down_function(serial_monitor, lock = None):
    while serial_monitor.mode != 5:
        serial_monitor.mode = 5
    time.sleep(0.05)
    drive.down(150)
    
    try:
        while True:
            if serial_monitor.heart_beat == False:                      #判断单片机心跳，如果停止，进入紧急下降处理
                raise Exception
            if so_deal.is_pause and so_deal.is_connected == True:       #如果有暂停指令就让机器人停止，否则机器人下降
                while True:
                    print("is pause!!!")
                    if (so_deal.cmd_change == True):
                        so_deal.cmd_change = False

                        if lock!=None:
                            lock.acquire()
                        top_dist = serial_monitor.dis_top
                        if lock!=None:
                            lock.release()
                        #lock.release()
                        
                        if so_deal.move_info == 0:                          #上升指令 move_info 等于 0
                            if(top_dist >= 1.0 or top_dist == None):       #到顶部距离大于等于1米并且不是0, 小于1米不执行上升
                                print(top_dist)
                                drive.up(112)
                                time.sleep(1)
                                drive.stop()
                            else:
                                drive.stop()
                    
                        elif so_deal.move_info == 1:                        #下降指令 move_info 等于 1
                            drive.down(112)
                            time.sleep(1)
                            drive.stop()
                            so_deal.move_info = -1

                        elif so_deal.move_info == 2:                        #停止指令 move_info 等于 2
                            drive.stop()
                        
                        elif so_deal.move_info == 3:
                            drive.up(212)
                            break
            if lock!=None:
                lock.acquire()
            down_dis = serial_monitor.dis_down
            if lock!=None:
                lock.release()

            if down_dis != None:
                if (down_dis- value_laser_down) <= 1 or bmp.relative_altitude <=1:
                    drive.down(100)
                    time.sleep(1)
                
                if (down_dis- value_laser_down) <= 0.5 or bmp.relative_altitude <= 0:
                    drive.stop()
                    break

    except (Exception, KeyboardInterrupt) as e:
        print("Whool!!!",e)
        if lock!=None:
            lock.acquire()
        while serial_monitor.ras_stop_sign != True:
            serial_monitor.ras_stop_sign = True
        if lock!=None:
            lock.release()
            time.sleep(0.2)
        serial_monitor.finish()                 #不让单片机接管
        while 1:
            drive.down(121)
            down_dist = serial_monitor.fastMeasure_down()
            if (down_dist - value_laser_down) <= 0.5 or bmp.relative_altitude <= 0:
                drive.stop()       
                sys.exit(1)            

   

def auto_move():
    global cam0,cam1,cam2,cam3 
    time.sleep(2)
    serial_monitor = Thread_serial() 
    serial_monitor.mode = 3
    lock = threading.Lock()
    
    serial_monitor.start()
    
    Thread_stm = threading.Thread( target = serial_monitor.thread_serial, args = (lock, ) )
    Thread_stm.setDaemon(True)
    Thread_stm.start()
    try:
        time.sleep(0.5)
        up_function(serial_monitor, lock)

        down_function(serial_monitor, lock)

        if lock!=None:
            lock.acquire()
        while serial_monitor.ras_stop_sign != True:
            serial_monitor.ras_stop_sign = True
        if lock!=None:
            lock.release()
        time.sleep(0.2)
        serial_monitor.finish()
        print("Program exit normally")                          
        return
    except (Exception, KeyboardInterrupt) as e:
        print("Whool!!!",e)
        drive.stop()       
        sys.exit(1)
def start_all_thread():
    try:
        Thread1 = threading.Thread( target = EightTimeS, args = () )         #每隔8秒发送
        Thread1.setDaemon(True)
        Thread1.start()
    except:
        print ('thread1 start exception')
    
    try:
        Thread2 = threading.Thread( target = so_deal.det_heartbeat, args = (client.socket_server,) )            #心跳包检测
        Thread2.setDaemon(True)
        Thread2.start()
    except:
        print ('thread2 start exception')
    
    try:
        Thread3 = threading.Thread( target = so_deal.rev_from_server, args = (client.socket_server,) )          
        Thread3.setDaemon(True)
        Thread3.start()
    except:
       print ('thread3 start exception')
    
    try:
        Thread4 = threading.Thread( target = so_deal.send_to_server, args = (client.socket_server, que, ) )
        Thread4.setDaemon(True)
        Thread4.start()
    except:
        print ('thread4 start exception')
    
    try:
        
        Thread5 = threading.Thread( target = so_deal.send_to_app, args = (client.socket_app, que2, ) )
        Thread5.setDaemon(True)
        Thread5.start()
    except:
        print ('thread5 start exception')
    
    try:
        Thread6 = threading.Thread( target = so_deal.rev_from_app, args = (client.socket_app, que2, ) )
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

    #thread_start = 0
    # stm_watch = raspi_stm.watch()
    # stm_watch.start()
    Thread_bmp_read = threading.Thread( target = bmp.Get_relative_altitude, args = () )
    Thread_bmp_read.setDaemon(True)
    Thread_bmp_read.start()

    client = socket_init()
    Thread_socket = threading.Thread( target = client.creat_client, args = (sys.argv[1], sys.argv[2], ) )
    Thread_socket.setDaemon(True)
    Thread_socket.start()
    Thread_socket.join(5)
    if (client.link_check) == 'true':
        so_deal = socket_deal()
        start_all_thread()
        so_deal.is_connected = True
        while(True):                                         
            if (so_deal.motion_mode == 0):       
                print("进入自动运动模式")         

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
        try:
            try:
                print("开始创建服务器socket")
                hot_point_socket = socket.socket()    
                hot_point_host = ''
                hot_point_port = 8104
                addr = (hot_point_host, hot_point_port)
                hot_point_socket.bind(addr)        # 绑定端口
                hot_point_socket.listen(5)
            except Exception:
                del cam0,cam1,cam2,cam3
                print "socket_server_creat_failure"
                sys.exit(1)

            to_client, addr = hot_point_socket.accept()
            print ('...connected from :', addr)

            rev_str = to_client.recv(1024)
            to_client.send("\xAA\x96\xAC\x00\x01\x00\x01\x69")
            rev_str = to_client.recv(1024)
            packet_length = len(rev_str)

            if(packet_length==8):
                if( (rev_str[0]==b"\xAA") and ( ord(rev_str[1]) + ord(rev_str[7]) == 0xff ) ):
                #motion_mode = 0
                    # cam0 = v4l2_python.Camera(0)
                    # cam1 = v4l2_python.Camera(1)
                    # cam2 = v4l2_python.Camera(2)
                    # cam3 = v4l2_python.Camera(3)
                    if(rev_str[6] == b"\x00"):
                        try:
                            Threadcam0 = threading.Thread( target = cam0.start_capturing, args = () )
                            Threadcam0.setDaemon(True)
                            Threadcam0.start()
                        except:
                            print ('Threadcam0 start exception')
                        try:
                            Threadcam1 = threading.Thread( target = cam1.start_capturing, args = () )
                            Threadcam1.setDaemon(True)
                            Threadcam1.start()
                        except:
                            print ('Threadcam1 start exception')
                        try:
                            Threadcam2 = threading.Thread( target = cam2.start_capturing, args = () )
                            Threadcam2.setDaemon(True)
                            Threadcam2.start()
                        except:
                            print ('Threadcam2 start exception')
                        try:
                            Threadcam3 = threading.Thread( target = cam3.start_capturing, args = () )
                            Threadcam3.setDaemon(True)
                            Threadcam3.start()
                        except:
                            print ('Threadcam3 start exception')
                        
                        print("Auto move begin!!!")
                        auto_move_wifi()
                        #time.sleep(300)
                        print("Auto move finish!!!")
                
                        os.system("sudo killall -9 create_ap")
                        os.system("sudo killall -9 hostapd")
                        to_client.close()
                        hot_point_socket.close()         
                        print("program exit normally:-> close socket")
        except:
            print ("Execption!!!")
            to_client.close()
            hot_point_socket.close()                