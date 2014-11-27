plugin_xxx_yyy
==============

插件模版库
1、插件库中插件命名格式：plugin_xxx_yyy，现场命名格式：plugin_xxx_yyy_zzz
xxx：通道名称，如serial、tcpserver、tcpclient、udpserver、udpclient
yyy：协议名称，如modbus、gzxx（感智信息）、yykj（易运科技）、xpkj(携普科技)
zzz：序号或识别号，用于多路同类型协议
2、插件架构
统一程序入口为plugin.py，协议通过扫描protocols目录来实现，只支持唯一协议
3、配置说明
json格式
4、设备运行信息：
devices.txt



通过配置的方式组装出一个插件
channel(schema) + protocol ＋ mqtt

mqtt进程为主进程
channel进程为线程方式，每次处理调用protocol