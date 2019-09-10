# robot_image_capture
#爬管子机器人树莓派客户端主程序
# 环境搭建步骤
1 打开板载硬件串口，方法参考 <https://blog.csdn.net/m0_37509650/article/details/85403217>
    (1) 输入命令 sudo raspi-config 进入树莓派配置
        找到Interfacing选项，找到serial。
        第一个问题是：would you like a login shell to be accessible  over serial? 选否。
        第二个问题是would you like the serial port hardware to be enabled?选是。
    (2) 输入命令 sudo vim /boot/config.txt 编辑配置文件
        在最末尾另加一行，写 dtoverlay=pi3-miniuart-bt, 保存退出

2 输入命令 sudo raspi-config 在树莓派配置中打开i2c接口

3 下载 v4l2 python API接口
  （1）打开<https://pypi.org/project/v4l2/0.2/> 选择 Download files 下载压缩包
  （2）拷贝到树莓派中，目录可以随便选择，可以放在工作区间中，cd v4l2_0.2 进入安装目录
   (3) sudo python setup.py build
   (4) sudo python setup.py install

4 从GitHub上获取树莓派创建热点的脚本程序，并安装相关依赖库
    git clone <https://github.com/oblique/create_ap>
    cd create_ap
    make install

    sudo apt install util-linux procps hostapd iproute2 iw haveged dnsmasq

    

