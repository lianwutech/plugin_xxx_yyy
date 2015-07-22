#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
linkworld RTU协议类
"""

import datetime

import logging

from libs.utils import unpack_from_bin
from libs.base_protocol import BaseProtocol


logger = logging.getLogger('plugin')


class Rtu_Data_Package(object):
    def __init__(self, data_set, package_len):
        self.data_set = data_set
        self.package_len = package_len
        self.data_len = 0
        self.device_id = 0
        self.func_code = 0
        self.data = ""
        self.crc_low = 0
        self.crc_high = 0

    def process_data(self):
        self.data_len = self.data_set[2]
        # 校验长度
        if self.package_len != self.data_len + 5:
            logger.debug("data_len error, data_len:%d,  package_length:%d" %
                         (self.data_len, self.package_len))
            return False
        self.crc_low = self.data_set[-2]
        self.crc_high = self.data_set[-1]
        # 不校验crc
        pass
        self.device_id = self.data_set[0]
        self.func_code = self.data_set[1]
        for i in range(0, self.data_len):
            self.data += "%02x " % self.data_set[i + 3]

        return True


def unpack_rtu_data(data):
    """
    解析RTU数据，返回json字符串或None
    :param data:
    :return:
    """
    # 协议包头 2个字节 0xAB  0xCD
    # 卡号 11个字节 0x01 0x03 0x09 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08
    # 第1路数据包长度 1个字节 最大0x69
    # 第1路数据:
    #   Device ID: 1个字节 0x01
    #   功能码: 1个字节 0x03
    #   数据长度: 1个字节 0x64 最大值100
    #   数据：
    #   CRC校验码: 2个字节 低位在前，高位在后
    # 第2路数据包长度 1个字节 最大0x69
    # 第2路数据：参照第1路数据包
    # 第3路数据包长度 1个字节 最大0x69
    # 第3路数据：参照第1路数据包
    # 第4路数据包长度 1个字节 最大0x0D（13个字节）
    # 第4路数据：参照第1路数据包，其中数据长度不大于8个字节
    # 第5路数据包长度 1个字节 最大0x15（21个字节）
    # 第5路数据：参照第1路数据包，其中数据长度不大于16个字节
    # 第6路数据包长度 1个字节 最大0x1D（29个字节）
    # 第6路数据: 参照第1路数据包，其中数据长度不大于24个字节
    # 协议尾：2个字节 0xDC 0xBA

    _offset = 0
    # 协议包头 2个字节 0xAB  0xCD
    (packet_header_1, packet_header_2) = unpack_from_bin("!BB", data, _offset)
    _offset += 2
    if packet_header_1 != 0xAB and packet_header_2 != 0xCD:
        logger.debug("packet error: %02X %02X" % (packet_header_1, packet_header_2))
        return None

    # 卡号 11个字节
    msisdn_set = unpack_from_bin("!11B", data, _offset)
    _offset += 11
    msisdn = ""
    for i in msisdn_set:
        if i < 0 or i > 9:
            logger.debug("msisdn error, msisdn_set: %r" % msisdn_set)
            return None
        msisdn += "%d" % i

    packet_dict = {}
    # 处理消息包内容
    for index in range(0, 6):
        (packet_len,) = unpack_from_bin("!B", data, _offset)
        _offset += 1

        if packet_len > 0:
            if packet_len > 0x69:
                logger.debug("packet_len %d error" % packet_len)
                return None

            packet_set = unpack_from_bin("!%dB" % packet_len, data, _offset)
            _offset += packet_len

            data_packet = Rtu_Data_Package(packet_set, packet_len)
            result = data_packet.process_data()
            if not result:
                return None
            packet_dict[index] = data_packet

    if len(packet_dict) == 0:
        logger.debug("package has not data.")
        return None

    # 协议尾：2个字节 0xDC 0xBA
    (packet_tail_1, packet_tail_2) = unpack_from_bin("!BB", data, _offset)
    if packet_tail_1 != 0xDC and packet_tail_2 != 0xBA:
        logger.debug("packet error: %02X %02X" % (packet_tail_1, packet_tail_2))
        return None

    return packet_dict


class LWRtuProtocol(BaseProtocol):
    def __init__(self, protocol_params):
        BaseProtocol.__init__(self, protocol_params)
        # 修改协议名称
        self.protocol_type = "lwrtu"
        self.device_type = "lwrtu"
        self.device_cmd_msg = None

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

        # 消息解析
        result_dict = unpack_rtu_data(data)

        # 生成数据
        result_data = {}
        if result_dict:
            for index in result_dict:
                result_data[index] = {"device_id": result_dict[index].device_id,
                                      "func_code": result_dict[index].func_code,
                                      "data": result_dict[index].data}

        if len(result_data) > 0:
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
                    "data": {"command_id": self.device_cmd_msg["command_id"], "result": result_data}
                }
            else:
                device_data_msg = {
                    "device_id": device_id,
                    "device_addr": device_addr,
                    "device_port": device_port,
                    "device_type": device_type,
                    "protocol": self.protocol_type,
                    "data": result_data
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
        pass
