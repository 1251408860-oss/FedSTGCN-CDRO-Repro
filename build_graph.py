from scapy.all import rdpcap, IP, TCP, Raw
import math
from collections import Counter, defaultdict
import torch
from torch_geometric.data import Data

def calculate_shannon_entropy(data_bytes):
    """计算微观信息熵"""
    if not data_bytes: return 0.0
    entropy = 0.0
    length = len(data_bytes)
    counts = Counter(data_bytes)
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy

print("[*] 正在加载全量广域网真实交火数据集 full_arena.pcap ...")
# 载入你刚打出来的靶场数据
packets = rdpcap('full_arena.pcap')

# 用于存储每个 IP 的流变信息
flows = defaultdict(lambda: {'payloads': b"", 'timestamps': [], 'bytes': 0})

print("[*] 正在解析底层数据包，映射多维物理空间...")
for pkt in packets:
    if IP in pkt and TCP in pkt:
        src_ip = pkt[IP].src
        # 我们只分析发往目标服务器的请求流，排除服务器自己的回包
        if src_ip == '10.0.0.100': continue 
        
        flows[src_ip]['timestamps'].append(pkt.time)
        flows[src_ip]['bytes'] += len(pkt)
        if Raw in pkt:
            flows[src_ip]['payloads'] += bytes(pkt[Raw].load)

# ----------------------------------------------------
# 构建图神经网络所需的张量矩阵
# ----------------------------------------------------
node_features = []
labels = []
ip_to_idx = {}
edge_src = []
edge_dst = []

# 1. 压入目标服务器节点 (Node 0 作为星型拓扑的中心)
target_ip = '10.0.0.100'
ip_to_idx[target_ip] = 0
node_features.append([15.0, 10.0, 1.0]) # 目标节点的占位基线特征
labels.append(0)

print("\n" + "="*70)
print(f"{'源 IP (网络实体)':<18} | {'ln(N+1)':<10} | {'ln(T+1)':<10} | {'微观熵 sigma':<15} | {'Ground Truth'}")
print("="*70)

# 2. 遍历所有捕获到的边缘设备，提取物理特征并构图
for ip, data in flows.items():
    if not data['timestamps']: continue
    
    idx = len(ip_to_idx)
    ip_to_idx[ip] = idx
    
    # 提取物理特征
    duration = float(data['timestamps'][-1] - data['timestamps'][0]) if len(data['timestamps']) > 1 else 0.0
    total_bytes = data['bytes']
    sigma = calculate_shannon_entropy(data['payloads'])
    
    ln_N = math.log(total_bytes + 1)
    ln_T = math.log(duration + 1)
    
    node_features.append([ln_N, ln_T, sigma])
    
    # 根据我们在 Mininet 中设定的 IP 网段打标签
    # 10.0.0.2x 是受控僵尸节点 (Label 1)
    # 10.0.0.1x 是合法人类用户 (Label 0)
    label = 1 if ip.startswith('10.0.0.2') else 0
    labels.append(label)
    
    # 构建拓扑：所有边缘流节点汇聚指向目标服务器节点 (0)，形成扇入效应
    edge_src.append(idx)
    edge_dst.append(0)

    label_str = "🔥 恶意攻击 (LLM)" if label == 1 else "✅ 良性用户 (人类)"
    print(f"{ip:<20} | {ln_N:<10.4f} | {ln_T:<10.4f} | {sigma:<15.4f} | {label_str}")

# 3. 转化为 PyTorch Geometric 标准图对象
x = torch.tensor(node_features, dtype=torch.float)
y = torch.tensor(labels, dtype=torch.long)
edge_index = torch.tensor([edge_src, edge_dst], dtype=torch.long)

graph_data = Data(x=x, edge_index=edge_index, y=y)

print("="*70)
print("\n🎯 跨流物理时空图 (Spatiotemporal Graph) 构建完成！")
print(f"[*] 图节点数量 (Nodes) : {graph_data.num_nodes} (1个目标节点 + {graph_data.num_nodes-1}个流节点)")
print(f"[*] 图边数量 (Edges)   : {graph_data.num_edges} (有向图连边)")
print(f"[*] 特征矩阵维度 (X)   : {graph_data.x.shape} (节点数 x [体积, 时间, 熵])")
print("\n[下一步] 可以将此 graph_data 直接喂给你之前写好的 PI-GNN 物理损失函数进行制裁了！")
torch.save(graph_data, 'arena_graph.pt')
print("[*] 真实靶场图张量已保存为 arena_graph.pt，准备进入物理制裁程序！")
