#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
YYkj协议类
"""

import datetime
import logging

from libs.base_protocol import BaseProtocol


logger = logging.getLogger('plugin')

# 指令超时时间，单位秒
timeout_interval = 5

class YykjifProtocol(BaseProtocol):
    def __init__(self, protocol_params):
        BaseProtocol.__init__(self, protocol_params)
        # 修改协议名称
        self.protocol_type = "yykjir"
        self.device_type = "yykjir"
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
        device_data_msg_list = []

        if "01:Begin" in data:
            # 开始消息忽略
            result_data = None
        elif "01:StudyOK" in data:
            result_data = "01:StudyOK"
        elif "01:StudyER" in data:
            result_data = "01:StudyER"
        elif "01:Send_OK" in data:
            result_data = "01:Send_OK"
        elif "01:Send_ER" in data:
            result_data = "01:Send_ER"
        else:
            logger.error("Unknown infrared message(%s). " % data)
            # 错误消息忽略
            result_data = None

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
        # 判断指令有效性
        if device_cmd_msg["device_type"] == self.device_type:
            device_cmd = device_cmd_msg["command"]
            device_cmd = device_cmd.strip()
            if len(device_cmd) != 6 \
                    or ('S' not in device_cmd and 'F' not in device_cmd)\
                    or (not device_cmd[1:6].isdigit()):
                device_cmd = ""
            else:
                if self.device_cmd_msg is None or datetime.datetime.now() > self.timeout_datatime:
                    # 命令消息为空，或命令超时，则执行当前命令
                    self.device_cmd_msg = device_cmd_msg
                    self.timeout_datatime = datetime.datetime.now() + datetime.timedelta(seconds=timeout_interval)
                    logger.debug("执行指令消息:%r" % device_cmd_msg)
                else:
                    # 上一条命令未超时，则丢弃当前命令
                    logger.info("上一条指令消息(%r)执行中，当前指令消息(%r)丢弃." % (self.device_cmd_msg, device_cmd_msg))
                    device_cmd = ""
        else:
            # 错误洗哦阿西
            logger.error("错误消息:%r." % device_cmd_msg)
            device_cmd = ""

        return device_cmd

