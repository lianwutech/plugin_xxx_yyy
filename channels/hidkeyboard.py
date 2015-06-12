#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
HID通道类
通过调用管理类对象的process_data函数实现信息的发送。
device_id规则定义:vendorid_productid
network_name将用于区分同一设备在不同网络节点中的位置
"""
import time
import logging

import usb1
import hid

from libs.utils import KeyBoard_ENTER

from libs.base_channel import BaseChannel


logger = logging.getLogger('plugin')


class HidKeyBoardChannel(BaseChannel):
    def __init__(self, channel_params, devices_file_name, protocol, mqtt_client, network_name):
        BaseChannel.__init__(self, channel_params, devices_file_name, protocol, mqtt_client, network_name)
        # 配置项
        self.vendor_id = int(channel_params.get("vendor_id", "0"), 16)
        self.product_id = int(channel_params.get("product_id", "0"), 16)
        self.timeout = channel_params.get("timeout", 2)
        self.protocol.set_device_info(self.vendor_id, self.product_id)
        usb_context = usb1.USBContext()
        usb_device = usb_context.getByVendorIDAndProductID(self.vendor_id, self.product_id)
        self.device_max_packet_size = usb_device.getMaxPacketSize0()
        self.device_bus = usb_device.getBusNumber()
        self.device_port = usb_device.getDeviceAddress()
        logger.debug("device bus:%03i device:%03i" % (self.device_bus, self.device_port))

    @staticmethod
    def check_config(channel_params):
        if "vendor_id" not in channel_params or "product_id" not in channel_params:
            return False
        return BaseChannel.check_config(channel_params)

    def run(self):
        # 首先上报设备数据
        for device_id in self.devices_info_dict:
            device_info = self.devices_info_dict[device_id]
            device_msg = {
                "device_id": device_info["device_id"],
                "device_type": device_info["device_type"],
                "device_addr": device_info["device_addr"],
                "device_port": device_info["device_port"],
                "protocol": self.protocol.protocol_type,
                "data": ""
            }
            self.mqtt_client.publish_data(device_msg)

        # 打印hid设备信息
        for d in hid.enumerate(0, 0):
            keys = d.keys()
            keys.sort()
            for key in keys:
                logger.debug("%s : %s" % (key, d[key]))
            logger.debug("")

        # 打开设备
        try:
            hid_device = hid.device(self.vendor_id, self.product_id)
        except Exception, e:
            logger.error("hid.device exception: %r." % e)
            return

        logger.debug("Manufacturer: %s" % hid_device.get_manufacturer_string())
        logger.debug("Product: %s" % hid_device.get_product_string())
        logger.debug("Serial No: %s" % hid_device.get_serial_number_string())

        result_list = list()
        be_clear = False
        while True:
            # 该线程保持空转
            try:
                data = hid_device.read(self.device_max_packet_size)
            except Exception, e:
                logger.error("hid_device.read exception: %r." % e)
                break

            if data:
                result_list.extend(data)
                logger.debug("data: %r , result data:%r" % (data, result_list))
                # 键盘的输入报表和输出报表的数据格式。其中输入报表共8个字节，输出报表只有1个字节。
                # 修饰键, 保留, 键值1, 键值2, 键值3, 键值4, 键值5, 键值6
                # 修饰键存放指示灯信息
                if KeyBoard_ENTER in data[2:8]:
                    # 数据搜集完毕,调用协议处理
                    device_data_list = self.protocol.process_data(self.network_name, result_list)
                    result_list = list()
                    logger.debug("Process data result: %r" % device_data_list)
                    for device_data in device_data_list:
                        self.check_device(device_data["device_id"],
                                          device_data["device_type"],
                                          device_data["device_addr"],
                                          device_data["device_port"])
                        self.mqtt_client.publish_data(device_data)

            time.sleep(0.05)
