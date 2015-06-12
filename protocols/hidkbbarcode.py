#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
hid协议键盘数据格式的条码扫描仪设备
"""

import logging

from libs.base_protocol import BaseProtocol
from libs.utils import KeyBoard_ENTER, keyboardcode_to_ascii


logger = logging.getLogger('plugin')


class HidKbBarCodeProtocol(BaseProtocol):
    def __init__(self, protocol_params):
        BaseProtocol.__init__(self, protocol_params)
        # 修改协议名称
        self.protocol_type = "hidkbbarcode"
        self.device_type = "hidkbbarcode"

    def process_data(self, network_name, data):
        """
        返回device_data
        :param data_msg:
        :return:
        """
        device_data_msg_list = []
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

        if not isinstance(data, list):
            logger.error("data(%r) is not list" % data)
            return []

        data_len = len(data)
        if data_len == 0:
            return []

        if data_len % 8 != 0:
            logger.error("data length(%d) error" % data_len)
            return []

        # 从后向前清理修饰键,保留字段
        for i in range(data_len/8, 0, -1):
            del data[8 * (i-1) + 1] # 修饰键
            del data[8 * (i-1)]     # 保留字段

        # 清除无效按键和回车键
        for i in range(len(data), 0, -1):
            if data[i-1] == KeyBoard_ENTER or data[i-1] == 0:
                logger.debug("del data %d" % (i-1))
                del data[i-1]

        # 数据转换
        result = ""
        for keycode in data:
            result += keyboardcode_to_ascii(keycode)

        logger.debug("data:%r, data_result:%s" % (data, result))

        device_data_msg = {
            "device_id": device_id,
            "device_addr": device_addr,
            "device_port": device_port,
            "device_type": device_type,
            "protocol": self.protocol_type,
            "data": result
        }
        device_data_msg_list.append(device_data_msg)

        return device_data_msg_list

    def process_cmd(self, device_cmd_msg):
        """
        返回cmd_msg
        :param device_cmd:
        :return:
        """
        self.device_cmd_msg = device_cmd_msg
        return device_cmd_msg["command"].get("resource_route", "")

