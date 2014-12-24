#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
realcom协议，上海卓岚科技
北川仪表电表控制器
"""
import time
import datetime
import struct
import binascii
import logging

from libs.base_protocol import BaseProtocol


logger = logging.getLogger('plugin')


def reverse_data(data_str):
    """
    16进制字符串逆序
    :param data_str:
    :return:
    """
    data_str_reverse = ""
    data_list = []
    for i in range(0, len(data_str)/2):
        data_list.append(data_str[i*2:i*2+2])
    data_list.reverse()
    for i in range(0, len(data_list)):
        data_str_reverse += data_list[i]

    return data_str_reverse


def data_str_add_33(data_str):
    """
    数据字符串加33操作
    :param data_str:
    :return:
    """
    dest_data_str = ""
    for i in range(0, len(data_str)/2):
        tmp_data_str = data_str[i*2:i*2+2]
        tmp_data = (int(tmp_data_str, 16) + 0x33) & 0xff
        dest_data_str += "%02x" % tmp_data
    return dest_data_str


def data_str_minus_33(data_str):
    """
    数据字符串减33操作
    :return:
    """
    dest_data_str = ""
    for i in range(0, len(data_str)/2):
        tmp_data_str = data_str[i*2:i*2+2]
        tmp_data = (int(tmp_data_str, 16) + 0x0100 - 0x33) & 0xff
        dest_data_str += "%02x" % tmp_data
    return dest_data_str


def cal_check_code(data_str):
    check_code = 0
    for i in range(0, len(data_str)/2):
        tmp_data_str = data_str[i*2:i*2+2]
        check_code += int(tmp_data_str, 16)

    check_code &= 0xff
    return "%02x" % check_code


class ZLRealComBcybDbkzqProtocol(BaseProtocol):
    def __init__(self, protocol_params):
        BaseProtocol.__init__(self, protocol_params)
        # 修改协议名称
        self.protocol_type = "bdyb"
        self.device_type = ["dbkzq"]
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
        # 解析realcom协议
        realcom_data_str = ""
        # 首先进行16进制字符串编码
        data_str = binascii.b2a_hex(data)
        if "fa071302fa" in data_str:
            # 忽略连接消息
            return []
        elif "fa0101" in data_str:
            realcom_data_str = data_str[6:]
        else:
            logger.error("错误数据格式:%s" % data_str)
            return []

        # 解析北川电表控制器协议
        if len(realcom_data_str) < 24:
            logger.error("消息格式错误:%s" % realcom_data_str)
            return []

        device_data_msg_list = []
        if len(realcom_data_str) > 24:
            if "68" == realcom_data_str[0:2] \
                    and "68" == realcom_data_str[14:16] \
                    and "91" == realcom_data_str[16:18] \
                    and "16" == realcom_data_str[-2:]:
                # 获取表号
                ammeter_id = reverse_data(realcom_data_str[2:12])
                ammeter_data_length = int(realcom_data_str[18:20], 16)
                ammeter_data_origin = realcom_data_str[20: 20+ammeter_data_length*2]
                # 跳过前面8位的指令
                ammeter_cmd_origin = ammeter_data_origin[0:8]
                ammeter_cmd_reverse = reverse_data(ammeter_cmd_origin)
                ammeter_cmd = data_str_minus_33(ammeter_cmd_reverse)
                if ammeter_cmd != "02ff5555":
                    return []
                # 对电表数据进行逆序
                ammeter_data_reverse = reverse_data(ammeter_data_origin[8:])
                # 对电表数据－33
                ammeter_data = data_str_minus_33(ammeter_data_reverse)
                logger.debug("ammeter_id:%s, ammeter_data:%s" % (ammeter_id, ammeter_data))

                if self.device_cmd_msg is not None:
                    device_id = self.device_cmd_msg["device_id"]
                    device_addr = self.device_cmd_msg["device_addr"]
                    device_port = self.device_cmd_msg["device_port"]
                    device_type = self.device_cmd_msg["device_type"]
                else:
                    device_id = "%s/%s/%s" % (network_name, ammeter_id, "0")
                    device_addr = ammeter_id
                    device_port = 0
                    device_type = self.device_type

                if self.device_cmd_msg is not None:
                    # 需要根据原有指令组包
                    device_data_msg = {
                        "device_id": device_id,
                        "device_addr": device_addr,
                        "device_port": device_port,
                        "device_type": device_type,
                        "protocol": self.protocol_type,
                        "data": {"command_id": self.device_cmd_msg["command_id"], "result": ammeter_data}
                    }
                    device_data_msg_list.append(device_data_msg)

                    # 处理完成后，消息置空
                    self.device_cmd_msg = None
        elif len(realcom_data_str) == 24:
            # 控制指令结果
            if self.device_cmd_msg is not None:
                # 解析指令结果
                result_data = "00"
                # 需要根据原有指令组包
                device_data_msg = {
                    "device_id": self.device_cmd_msg["device_id"],
                    "device_addr": self.device_cmd_msg["device_addr"],
                    "device_port": self.device_cmd_msg["device_port"],
                    "device_type": self.device_cmd_msg["device_type"],
                    "protocol": self.protocol_type,
                    "data": {"command_id": self.device_cmd_msg["command_id"], "result": result_data}
                }
                device_data_msg_list.append(device_data_msg)
                # 处理完成后，消息置空
                self.device_cmd_msg = None
        elif len(realcom_data_str) == 13:
            # 解析指令结果
                result_data = realcom_data_str[20:22]
                # 需要根据原有指令组包
                device_data_msg = {
                    "device_id": self.device_cmd_msg["device_id"],
                    "device_addr": self.device_cmd_msg["device_addr"],
                    "device_port": self.device_cmd_msg["device_port"],
                    "device_type": self.device_cmd_msg["device_type"],
                    "protocol": self.protocol_type,
                    "data": {"command_id": self.device_cmd_msg["command_id"], "result": result_data}
                }
                device_data_msg_list.append(device_data_msg)
                # 处理完成后，消息置空
                self.device_cmd_msg = None
        else:
            logger.error("消息格式错误:%s" % realcom_data_str)

        return device_data_msg_list

    def process_cmd(self, device_cmd_msg):
        """
        输入设备指令消息返回设备指令字符串
        :param device_cmd_msg
        :return: ""－命令错误，其他－命令正常
        """
        # 判断指令有效性
        if not self.check_command_msg(device_cmd_msg):
            return ""

        cmd_data = ""
        if self.check_process():
            # 命令消息为空，或命令超时，则执行当前命令
            self.device_cmd_msg = device_cmd_msg
            self.reset_timer()
            logger.debug("执行指令消息:%r" % device_cmd_msg)
        else:
            # 上一条命令未超时，当前命令不执行，放入未处理队列
            self.add_pending(device_cmd_msg)
            logger.info("上一条指令消息(%r)执行中，当前指令消息(%r)丢弃." % (self.device_cmd_msg, device_cmd_msg))
            return cmd_data

        device_cmd = device_cmd_msg["command"]
        self.device_cmd_msg = device_cmd_msg
        # 对设备控制命令进行编码
        device_cmd_str = ""
        # 支持设备命令有：get_data, open, close
        if "get_data" == device_cmd:
            # 查询数据指令
            # 对表号进行翻转
            # 对标示符进行转换
            origin_flag_data = "02ff5555"
            if len(origin_flag_data) != 8:
                return ""
            # ＋33操作
            flag_data_a33 = data_str_add_33(origin_flag_data)
            # 进行翻转操作
            flag_data = reverse_data(flag_data_a33)

            # 对表号进行翻转
            ammeter_id = device_cmd_msg.get("device_addr", "000000000000")
            ammeter_id_reverse = reverse_data(ammeter_id)
            device_cmd_str = "68" + ammeter_id_reverse + "68" + "1104" + flag_data
            # 计算校验码
            check_code_str = cal_check_code(device_cmd_str)
            # 组结尾
            device_cmd_str = device_cmd_str + check_code_str + "16"
        elif "open" == device_cmd:
            # 合闸，通电
            ammeter_id = device_cmd_msg.get("device_addr", "000000000000")
            ammeter_id_reverse = reverse_data(ammeter_id)
            # 硬编码：14 0d 35 34 53 ca 33 33 33 33 ab 89 67 45 42
            device_cmd_str = "68" + ammeter_id_reverse + "68" + "140d353453ca33333333ab89674542"
            # 计算校验码
            check_code_str = cal_check_code(device_cmd_str)
            # 组结尾
            device_cmd_str = device_cmd_str + check_code_str + "16"

        elif "close" == device_cmd:
            # 跳闸，断电
            ammeter_id = device_cmd_msg.get("device_addr", "000000000000")
            ammeter_id_reverse = reverse_data(ammeter_id)
            # 硬编码：14 0d 34 34 53 ca 33 33 33 33 ab 89 67 45 42
            device_cmd_str = "68" + ammeter_id_reverse + "68" + "140d343453ca33333333ab89674542"
            # 计算校验码
            check_code_str = cal_check_code(device_cmd_str)
            # 组结尾
            device_cmd_str = device_cmd_str + check_code_str + "16"

        else:
            logger.error("cmd_type error: %s" % device_cmd)
            return ""

        # 对标示符进行＋33操作
        # 将command进行十六进制解码并打包
        try:
            cmd_data = binascii.a2b_hex(device_cmd_str)
        except Exception, e:
            logger.error("str(%s) binascii.a2b_hex error(%r)." % (device_cmd_str, e))

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
                self.channel.send_data(data)
            else:
                logger.info("channel为空，不处理.")

            # 处理未处理的消息
            for device_cmd_msg in self.pending_device_cmd_msg_list:
                self.pending_device_cmd_msg_list.remove(device_cmd_msg)
                self.channel.process_cmd(device_cmd_msg)

            time.sleep(1)
