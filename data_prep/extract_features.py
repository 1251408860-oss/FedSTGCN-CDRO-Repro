from scapy.all import rdpcap, Raw
import math
from collections import Counter

def calculate_shannon_entropy(data_bytes):
    """
    计算载荷的香农微观熵 (Micro-Entropy, sigma)。
    熵值越高，说明数据越复杂、越接近人类自然语言或高密度信息。
    机械化 DoS 攻击的熵值通常极低（因为是重复字符填充）。
    """
    if not data_bytes: return 0.0
    entropy = 0.0
    length = len(data_bytes)
    counts = Counter(data_bytes)
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy

print("[*] 正在加载并解析 llm_attack.pcap 物理流量包...")
packets = rdpcap('llm_attack.pcap')

# 初始化流的统计容器
payloads = b""
timestamps = []
total_bytes = 0

for pkt in packets:
    timestamps.append(pkt.time)
    total_bytes += len(pkt)
    # 只提取包含应用层数据的真实 Payload（我们 LLM 生成的 HTTP GET 请求）
    if pkt.haslayer(Raw):
        payloads += bytes(pkt[Raw].load)

# --- 计算跨流物理时空图 (ST-GNN) 节点特征 ---

# 1. 持续时间 T (单位：秒)
duration = float(timestamps[-1] - timestamps[0]) if len(timestamps) > 1 else 0

# 2. 计算香农微观熵 sigma
sigma = calculate_shannon_entropy(payloads)

# 3. 计算对数映射后的高维特征向量
ln_N = math.log(total_bytes + 1)
ln_T = math.log(duration + 1)

print("\n" + "="*50)
print("🎯 成功提取 PI-GNN 节点的高维特征张量 X_i")
print("="*50)
print(f"原始流变持续时间 T  : {duration:.4f} 秒")
print(f"原始宏观传输总体积 N: {total_bytes} Bytes")
print("-" * 50)
print(f"特征 1: 宏观对数体积 ln(N+1)  -> {ln_N:.4f}")
print(f"特征 2: 流变对数时间 ln(T+1)  -> {ln_T:.4f}")
print(f"特征 3: 载荷微观物理熵 sigma   -> {sigma:.4f} Bits/Byte")
print("="*50)
print("\n[分析]: 正常的机械 DoS 熵值往往在 0.5 - 2.0 之间。")
print("如果你的 sigma 超过了 4.5，说明 LLM 完美实现了 '特征注水'，成功骗过了纯统计学分类器！")
