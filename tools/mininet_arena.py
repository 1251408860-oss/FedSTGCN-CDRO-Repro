#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOME_DIR = os.path.expanduser("~")
CONDA_ACTIVATE = os.path.join(HOME_DIR, "miniconda3", "bin", "activate")
LOCUST_FILE = os.path.join(BASE_DIR, "benign_user.py")
LLM_ATTACK_SCRIPT = os.path.join(BASE_DIR, "llm_attack_robust.py")

def create_physical_arena():
    # 开启 TCLink 支持，这是模拟真实物理链路 (带宽限制、延迟、丢包) 的关键！
    net = Mininet(controller=Controller, switch=OVSKernelSwitch, link=TCLink)

    info('*** [1] 添加控制器\n')
    net.addController('c0')

    info('*** [2] 构建网络拓扑节点\n')
    # 核心交换机 (骨干网) 与 边缘交换机
    core_sw = net.addSwitch('s1')
    edge_sw1 = net.addSwitch('s2')
    edge_sw2 = net.addSwitch('s3')

    # 目标服务器 (Target)
    target = net.addHost('h_target', ip='10.0.0.100')

    # 合法的人类用户 (Benign Users)
    user1 = net.addHost('h_user1', ip='10.0.0.10')
    user2 = net.addHost('h_user2', ip='10.0.0.11')

    # 受控的 IoT 僵尸节点 (Botnet for LLM Attack)
    bot1 = net.addHost('h_bot1', ip='10.0.0.20')
    bot2 = net.addHost('h_bot2', ip='10.0.0.21')
    bot3 = net.addHost('h_bot3', ip='10.0.0.22')

    info('*** [3] 添加具有严苛物理约束的链路 (TCLink)\n')
    # 【核心瓶颈】：核心交换机到目标服务器的链路。
    # 我们故意将其带宽限制在 10Mbps，添加 5ms 的真实传播延迟，并设置最大队列长度 max_queue_size。
    # 只有这样，分布式低速攻击汇聚时，才能在这里引发物理排队排队拥塞！
    net.addLink(target, core_sw, bw=10, delay='5ms', max_queue_size=1000)

    # 边缘交换机连接到核心 (骨干链路通常带宽充裕，100Mbps)
    net.addLink(edge_sw1, core_sw, bw=100, delay='2ms')
    net.addLink(edge_sw2, core_sw, bw=100, delay='2ms')

    # 用户和僵尸节点连接到边缘网关
    net.addLink(user1, edge_sw1, bw=50)
    net.addLink(user2, edge_sw1, bw=50)
    net.addLink(bot1, edge_sw2, bw=10) # 模拟 IoT 设备网络较差
    net.addLink(bot2, edge_sw2, bw=10)
    net.addLink(bot3, edge_sw2, bw=10)

    info('*** [4] 启动物理网络靶场\n')
    net.start()

    info('*** [5] 部署服务与监听\n')
    # 在目标服务器上启动一个轻量级 Python HTTP 服务，用来真实响应 GET 请求
    target.cmd('python3 -m http.server 80 &')
    time.sleep(1)
    
    # 在目标服务器上启动 tcpdump，专门抓取这个网卡的流量
    info('    -> 目标服务器正在开启 tcpdump 抓包 (生成 full_arena.pcap)...\n')
    target.cmd('tcpdump -i h_target-eth0 tcp port 80 -w full_arena.pcap &')

    info('*** [6] 注入 Locust 工业级真实背景良性流量\n')
    # 使用 bash -c 先激活 DL 虚拟环境，再运行 locust
    locust_cmd = f'bash -c "source {CONDA_ACTIVATE} DL && locust -f {LOCUST_FILE} --headless -u 5 -r 1 -H http://10.0.0.100" > /tmp/locust.log 2>&1 &'
    user1.cmd(locust_cmd)
    user2.cmd(locust_cmd)

    info('*** [7] 释放大模型赋能的分布式协同攻击 (DLDoS)\n')
    # 同样地，先 source 激活环境，再运行 LLM 攻击脚本
    llm_cmd = f'bash -c "source {CONDA_ACTIVATE} DL && python {LLM_ATTACK_SCRIPT} 10.0.0.100"'
    
    bot1.cmd(f'{llm_cmd} > /tmp/bot1_attack.log 2>&1 &')
    bot2.cmd(f'{llm_cmd} > /tmp/bot2_attack.log 2>&1 &')
    bot3.cmd(f'{llm_cmd} > /tmp/bot3_attack.log 2>&1 &')
    info('*** [8] 攻击演练进行中，进入 Mininet CLI (输入 exit 退出并保存 PCAP)\n')
    info('    💡 提示: 靶场正在运行！良性流量与高熵攻击流量正在核心交换机发生物理碰撞！\n')
    CLI(net)

    info('*** [9] 停止靶场，清理战场\n')
    net.stop()
    os.system('pkill -f "http.server"')
    os.system('pkill -f "wget"')

if __name__ == '__main__':
    setLogLevel('info')
    create_physical_arena()
