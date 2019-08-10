import cv2
from fcntl import ioctl
import mmap
import numpy as np
import os
import struct
import v4l2
import threading
import time

class Camera(object):
    NUM_BUFFERS = 4
    def __init__(self, device_num):
        self.device_num = device_num
        self.device_name = "/dev/video%d"%device_num
        self.open_device()
        self.init_device()

    def open_device(self):
        self.fd = os.open(self.device_name, os.O_RDWR, 0)

    def init_device(self):
        cap = v4l2.v4l2_capability()
        fmt = v4l2.v4l2_format()

        ioctl(self.fd, v4l2.VIDIOC_QUERYCAP, cap)
        
        if not (cap.capabilities & v4l2.V4L2_CAP_VIDEO_CAPTURE):
            raise Exception("{} is not a video capture device".format(self.device_name))
        
        fmt.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
        fmt.fmt.pix.width = 640
        fmt.fmt.pix.height = 480
        fmt.fmt.pix.pixelformat = v4l2.V4L2_PIX_FMT_MJPEG
        fmt.fmt.pix.field = v4l2.V4L2_FIELD_NONE
        ioctl(self.fd, v4l2.VIDIOC_S_FMT, fmt)
        
        self.init_mmap()
    
    def init_mmap(self):
        req = v4l2.v4l2_requestbuffers()
        
        req.count = self.NUM_BUFFERS
        req.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
        req.memory = v4l2.V4L2_MEMORY_MMAP
        
        try:
            ioctl(self.fd, v4l2.VIDIOC_REQBUFS, req)
        except Exception:
            raise Exception("video buffer request failed")
        
        if req.count < 2:
            raise Exception("Insufficient buffer memory on {}".format(self.device_name))

        self.buffers = []
        for x in range(req.count):
            buf = v4l2.v4l2_buffer()
            buf.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
            buf.memory = v4l2.V4L2_MEMORY_MMAP
            buf.index = x
            
            ioctl(self.fd, v4l2.VIDIOC_QUERYBUF, buf)

            buf.buffer =  mmap.mmap(self.fd, buf.length, mmap.PROT_READ, mmap.MAP_SHARED, offset=buf.m.offset)
            self.buffers.append(buf)

    def start_capturing(self):
        for buf in self.buffers:
            ioctl(self.fd, v4l2.VIDIOC_QBUF, buf)
        video_type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
        ioctl(self.fd, v4l2.VIDIOC_STREAMON, struct.pack('i', video_type))
        self.filter_invalid_data()
        self.main_loop()

    
    def process_image(self, buf, path_name, pic_count):
        video_buffer = self.buffers[buf.index].buffer
        data = video_buffer.read(buf.bytesused)
        try:
            fout = open(path_name+"picture%d.jpg"%pic_count, "w+")
            fout.write(data)
            fout.close()
            video_buffer.seek(0)
        except Exception as e:
            # Not entirely sure what Exceptions I'm looking for here, potentially a bad read?
            print (e)

    def main_loop(self):
        path_name = "./cam%d_pictures/"%self.device_num
        if(os.access(path_name, os.F_OK) == False):
            os.mkdir(path_name)
        pic_count = 0
        print("camera%dstart capturing ..."%self.device_num)
        while True:
            #time.sleep(0.05)
            for x in range(self.NUM_BUFFERS):
                #print "grabbing frame {}".format(x)
                buf = self.buffers[x]
                ioctl(self.fd, v4l2.VIDIOC_DQBUF, buf)
                self.process_image(buf, path_name, pic_count)
                ioctl(self.fd, v4l2.VIDIOC_QBUF, buf)
                pic_count = pic_count+1

    def filter_invalid_data(self):
        for i in range(3):
            for x in range(self.NUM_BUFFERS):
                buf = self.buffers[x]
                ioctl(self.fd, v4l2.VIDIOC_DQBUF, buf)
                video_buffer = self.buffers[buf.index].buffer
                data = video_buffer.read(buf.bytesused)
                video_buffer.seek(0)
                ioctl(self.fd, v4l2.VIDIOC_QBUF, buf)

    def get_frame_data(self):
            #self.filter_invalid_data()
            for x in range(self.NUM_BUFFERS):
                buf = self.buffers[x]
                ioctl(self.fd, v4l2.VIDIOC_DQBUF, buf)
                video_buffer = self.buffers[buf.index].buffer
                data = video_buffer.read(buf.bytesused)
                video_buffer.seek(0)
                ioctl(self.fd, v4l2.VIDIOC_QBUF, buf)
                #time.sleep(0.2)
            return data
    def init_stream_on(self):
        for buf in self.buffers:
            ioctl(self.fd, v4l2.VIDIOC_QBUF, buf)
            video_type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
            ioctl(self.fd, v4l2.VIDIOC_STREAMON, struct.pack('i', video_type))
if __name__ == "__main__":
    cam0 = Camera(0)
    #cam0.start_capturing()
    cam1 = Camera(1)
    #cam1.start_capturing()
    cam2 = Camera(2)
    #cam2.start_capturing()
    cam3 = Camera(3)
    #cam3.start_capturing()
    try:
        localtime = time.asctime( time.localtime(time.time()) )
        print ("local time :", localtime)
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
    except:
        localtime = time.asctime( time.localtime(time.time()) )
        print ("local time :", localtime)

    try:
        while True:
            pass
    except:
        localtime = time.asctime( time.localtime(time.time()) )
        print ("local time :", localtime)
