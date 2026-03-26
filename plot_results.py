import matplotlib.pyplot as plt
import numpy as np
import os

# 设置图表风格为学术风
plt.style.use('seaborn-v0_8-whitegrid')

# ==========================================
# 图 1：微观熵 (Micro-Entropy) 降维打击对比
# ==========================================
def plot_entropy_comparison():
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # 实验真实数据
    categories = ['Mechanical DoS\n(Traditional)', 'Human User\n(Benign)', 'LLM Agent\n(DLDoS Attack)']
    entropies = [1.25, 4.7882, 5.4478] # 传统 DDoS 熵极低，人类正常，LLM 注水最高
    colors = ['#8C92AC', '#2E8B57', '#C83200']
    
    bars = ax.bar(categories, entropies, color=colors, width=0.5)
    
    ax.set_ylabel('Shannon Entropy (Bits/Byte)', fontsize=14, fontweight='bold')
    ax.set_title('Fig 1: Micro-Entropy Camouflage by LLM Agents', fontsize=16, fontweight='bold')
    ax.set_ylim(0, 6.5)
    
    # 在柱状图上添加具体数值
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.4f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, fontweight='bold')

    # 绘制传统防御阈值的警示线
    ax.axhline(y=3.5, color='gray', linestyle='--', linewidth=1.5)
    ax.text(1.5, 3.6, 'Traditional NIDS Detection Threshold', color='gray', fontsize=10, fontstyle='italic', ha='center')

    plt.tight_layout()
    plt.savefig('fig1_entropy_comparison.png', dpi=300)
    print("[*] 成功生成 图1: fig1_entropy_comparison.png")

# ==========================================
# 图 2：PI-GNN 物理信息损失 (Loss Landscape) 揭秘
# ==========================================
def plot_loss_landscape():
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # 我们的 PI-GNN 训练真实数据 (最后 5 个 Epoch)
    epochs = np.array([4, 8, 12, 16, 20])
    l_data = np.array([0.7046, 0.7085, 0.6537, 0.6158, 0.6183])
    l_physics = np.array([5945.7, 5945.7, 5945.7, 5945.7, 5945.7])
    
    # 使用对数坐标轴 (Log Scale) 来同时展示 0.6 和 5945 这样悬殊的数字
    ax.plot(epochs, l_data, marker='o', markersize=8, linewidth=2.5, color='#4A90E2', label='Data Loss ($L_{data}$)')
    ax.plot(epochs, l_physics, marker='s', markersize=8, linewidth=2.5, color='#E94B3C', label='Physics Loss ($L_{physics}$)')
    
    ax.set_yscale('log') # 开启对数坐标！
    
    ax.set_xlabel('Training Epochs', fontsize=14, fontweight='bold')
    ax.set_ylabel('Loss Magnitude (Log Scale)', fontsize=14, fontweight='bold')
    ax.set_title('Fig 2: Physics-Informed GNN Exposing Hidden Threats', fontsize=16, fontweight='bold')
    ax.set_xticks(epochs)
    ax.legend(fontsize=12, loc='center right')
    
    # 添加文字高亮说明
    ax.annotate('LLM evades Data Loss\n(Falsely classified as Benign)', 
                xy=(16, 0.6158), xytext=(8, 2),
                arrowprops=dict(facecolor='#4A90E2', shrink=0.05),
                fontsize=11)
                
    ax.annotate('Physics Law Violation\n(Kirchhoff & Queueing Constraints)', 
                xy=(16, 5945), xytext=(6, 1000),
                arrowprops=dict(facecolor='#E94B3C', shrink=0.05),
                fontsize=11)

    plt.tight_layout()
    plt.savefig('fig2_physics_loss.png', dpi=300)
    print("[*] 成功生成 图2: fig2_physics_loss.png")

if __name__ == "__main__":
    plot_entropy_comparison()
    plot_loss_landscape()
    print("\n[🎉 完成] 两张顶会级别的学术配图已保存到当前目录！")
