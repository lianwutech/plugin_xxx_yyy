#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
realcom协议，上海卓岚科技
"""
import time
import datetime
import struct
import binascii
import logging

from libs.base_protocol import BaseProtocol


logger = logging.getLogger('plugin')

# 指令超时时间，单位秒
timeout_interval = 10


class ZLRealComProtocol(BaseProtocol):
    def __init__(self, protocol_params):
        BaseProtocol.__init__(self, protocol_params)
        # 修改协议名称
        self.protocol_type = "zlrealcom"
        self.device_type = "zlrealcom"
        self.device_cmd_msg = None
        # 如果指令5s没有返回则认为超时
        self.timeout_datatime = datetime.datetime.now() + datetime.timedelta(seconds=timeout_interval)

    @staticmethod
    def check_config(protocol_params):
        return BaseProtocol.check_config(protocol_params)

    def process_data(self, network_name, data):
        """
        输入原始数据，返回设备数据消息
        返回device_data
        :param data:
        :return:
        """
        result_data = None
        # 首先进行16进制字符串编码
        data_str = binascii.b2a_hex(data)
        if "fa071302fa" in data_str:
            # 忽略连接消息
            pass
        elif "fa0101" in data_str:
            result_data = data_str[6:]
        else:
            logger.error("错误数据格式")
            return None

        device_data_msg_list = []

        if result_data is not None:
            if self.device_cmd_msg is not None:
                device_id = self.device_cmd_msg["device_id"]
                device_addr = self.device_cmd_msg["device_addr"]
                device_port = self.device_cmd_msg["device_port"]
                device_type = self.device_cmd_msg["device_type"]
            else:
                device_id = "%s/%s/%s" % (network_name, self.device_addr, self.device_port)
                device_addr = self.device_addr
                device_port = self.device_port
                device_type = self.device_type

            if self.device_cmd_msg is not None:
                # 需要根据原有指令组包
                device_data_msg = {
                    "device_id": device_id,
                    "device_addr": device_addr,
                    "device_port": device_port,
                    "device_type": device_type,
                    "protocol": self.protocol_type,
                    "data": {"command": self.device_cmd_msg["command"], "result": result_data}
                }
                device_data_msg_list.append(device_data_msg)

            # 处理完成后，消息置空
            self.device_cmd_msg = None

        return device_data_msg_list

    def process_cmd(self, device_cmd_msg):
        """
        输入设备指令消息返回设备指令字符串
        :param device_cmd_msg:
        :return:
        """
        cmd_data = ""
        # 判断指令有效性
        if device_cmd_msg["device_type"] == self.device_type:
            device_cmd = device_cmd_msg["command"]
            # 将command进行十六进制解码并打包
            try:
                cmd_data = binascii.a2b_hex(device_cmd)
            except Exception, e:
                logger.error("str(%s) binascii.a2b_hex error(%r)." % (device_cmd, e))
        else:
            # 错误洗哦阿西
            logger.error("错误消息:%r." % device_cmd_msg)

        return cmd_data

    def run(self):
        """
        run函数
        每隔10s钟发一次心跳
        :return:
        """
        while True:
            # 发送心跳消息
            if self.channel is not None:
                data = struct.pack("!B", 0x00)
                self.channel.send(data)
            else:
                logger.info("channel为空，不处理.")
            time.sleep(10)
