#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
基础协议类
内存拼接和消息处理由协议类来处理
进程主要用来控制心跳
"""

import time
import datetime
import threading
import logging


logger = logging.getLogger('plugin')

class BaseProtocol(object):
    def __init__(self, protocol_params):
        self.protocol_params = protocol_params
        self.protocol_type = "basic"
        self.device_addr = "addr1"
        self.device_port = "port1"
        self.device_type = "basic"
        # 缓存命令来方便解析数据
        self.device_cmd_msg = None
        # channel对象
        self.channel = None
        self.thread = None
        # 缓存未处理的消息
        self.pending_device_cmd_msg_list = list()
        # 初始化超时时间，默认5s
        if "timeout" in protocol_params:
            self.timeout_interval = protocol_params["timeout"]
        else:
            # 默认5s超时
            self.timeout_interval = 5
        # 初始化定时器
        self.reset_timer()

    @staticmethod
    def check_config(protocol_params):
        return True

    def set_device_info(self, device_addr, device_port):
        # 设置默认的设备地址和端口
        # 设备地址和端口都是字符串类型
        self.device_addr = str(device_addr).replace(".", "_").replace(" ", "")
        self.device_port = str(device_port).replace(".", "_").replace(" ", "")

    def process_data(self, network_name, data):
        """
        返回device_data数组
        :param network_name:网络名称，data:收到的数据
        :return:设备数据字典
        设备数据格式:device_id, device_addr, device_port, device_type, data
        对于下行指令的处理结果则data包含command_id,result；
        主动上行数据data只包含result.
        """
        return []

    def process_cmd(self, device_cmd_msg):
        """
        处理设备指令，如果上一条指令未完成，则append未完成队列Pending_device_cmd_msg_list
        :param device_cmd_msg:设备指令，格式为device_id, device_addr, device_port, device_type, command. command_id
        :return:
        """
        self.device_cmd_msg = device_cmd_msg
        return ""

    def set_channel(self, channel):
        self.channel = channel

    def run(self):
        while True:
            # 处理未处理的消息
            for device_cmd_msg in self.pending_device_cmd_msg_list:
                self.channel.process_cmd(device_cmd_msg)
                self.pending_device_cmd_msg_list.remove(device_cmd_msg)
            time.sleep(1)

    def start(self):
        if self.thread is not None:
            # 如果进程非空，则等待退出
            self.thread.join(1)

        # 启动一个新的线程来运行
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def isAlive(self):
        if self.thread is not None:
            return self.thread.isAlive()
        else:
            return False

    def add_pending(self, device_cmd_msg):
        self.pending_device_cmd_msg_list.append(device_cmd_msg)

    def reset_timer(self):
        """
        重置计时器
        :return:
        """
        self.timeout_datatime = datetime.datetime.now() + datetime.timedelta(seconds=self.timeout_interval)

    def check_process(self):
        """
        超时检查
        :return:
        """
        return self.device_cmd_msg is None or datetime.datetime.now() > self.timeout_datatime

    def check_command_msg(self, device_command_msg):
        if device_command_msg is not None \
                and "device_id" in device_command_msg\
                and "device_type" in device_command_msg\
                and "device_addr" in device_command_msg\
                and "device_port" in device_command_msg\
                and "command" in device_command_msg\
                and "command_id" in device_command_msg\
                and device_command_msg["device_type"] == self.device_type:
            return True
        else:
            logger.error("错误消息:%r." % device_command_msg)
            return False