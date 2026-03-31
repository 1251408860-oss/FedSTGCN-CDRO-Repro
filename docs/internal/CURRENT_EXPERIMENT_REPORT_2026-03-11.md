# 当前实验情况报告（2026-03-11）

## 1. 报告目的

本报告用于说明 `FedSTGCN` 当前已经完成的实验、当前最可靠的实验结论、统计口径、方法公式，以及当前仍然存在的边界条件。

结论先行：

- 当前最稳的主结果是：`poisoned federated setting` 下，鲁棒聚合显著优于 `FedAvg`。
- `traditional anti-leakage` 中心化 family 目前仍然不显著，不能再作为主创新结论。
- `congestion-family` 的 physics gain 为正，但只能写成 `raw-significant / not globally correction-robust` 的次主结论。
- 当前这轮重跑是可复核的，但不是“在当前 WSL 宿主上完成 fresh Mininet 实重采”的结果。

## 2. 当前已完成的实验套件

### 2.1 主套件 recharge

- 目录：`/home/user/FedSTGCN/top_conf_suite_recharge`
- 完成时间：`2026-03-10 12:44:07` 到 `2026-03-10 13:31:56`
- 已完成：
  - `stage3_runs = 50`
  - `federated_runs = 60`
  - `paper_ready_plus` 已刷新

### 2.2 外部验证 batch2

- 目录：`/home/user/FedSTGCN/top_conf_suite_batch2`
- 完成时间：`2026-03-10 14:59:44` 到 `2026-03-10 15:22:14`
- 已完成：
  - `stage3_runs = 30`
  - `federated_runs = 36`

### 2.3 经典鲁棒联邦 baseline 补充套件

- 目录：`/home/user/FedSTGCN/top_conf_suite_recharge/fed_classic_robust_baselines`
- 已完成：
  - `median`
  - `trimmed_mean`
  - `rfa`
  - `krum`
  - `multi_krum`
  - `bulyan`
  - `shapley_proxy`

## 3. 数据到模型的实验流程

当前实验流水线可以写成：

\[
\text{Traffic Generation}
\rightarrow
\text{PCAP Capture}
\rightarrow
\text{Spatiotemporal Graph}
\rightarrow
\text{Central / Federated Training}
\rightarrow
\text{Significance Test}
\rightarrow
\text{Paper-ready Summary}
\]

其中关键阶段如下。

### 3.1 图构建

每个源 IP 在时间窗口 \(t\) 上形成一个流节点 \(v_{i,t}\)，并额外设置一个目标节点 \(v_{\mathrm{target}}\)。

节点特征向量为：

\[
\mathbf{x}_{i,t}
=
[
\ln(N_{i,t}+1),
\ln(T_{i,t}+1),
H_{i,t},
D^{\mathrm{obs}}_{i,t},
r_{i,t},
\bar{s}_{i,t},
q_{i,t}
]
\]

其中：

- \(N_{i,t}\)：该窗口中的总字节量
- \(T_{i,t}\)：该窗口内持续时间
- \(H_{i,t}\)：payload Shannon entropy
- \(D^{\mathrm{obs}}_{i,t}\)：平均包到达间隔
- \(r_{i,t}\)：包速率
- \(\bar{s}_{i,t}\)：平均包长
- \(q_{i,t}\)：端口多样性

边定义为：

\[
E_s = \{(v_{i,t}, v_{\mathrm{target}})\}
\]

\[
E_t = \{(v_{i,t-1}, v_{i,t})\}
\]

即：

- `spatial edge`：流节点指向目标节点
- `temporal edge`：同一源 IP 的相邻时间窗口相连

### 3.2 中心化 PI-GNN

模型是双分支图注意力网络：

- 空间分支：对 \(E_s\) 做 GAT
- 时间分支：对 \(E_t\) 做 GAT
- 门控融合：将两支特征融合

融合形式为：

\[
\mathbf{g} = \sigma\left(W_g[\mathbf{h}_s \| \mathbf{h}_t]\right)
\]

\[
\mathbf{h}_{\mathrm{fused}} = \mathbf{g} \odot \mathbf{h}_s + (1-\mathbf{g}) \odot \mathbf{h}_t
\]

### 3.3 物理约束损失

总损失函数为：

\[
L_{\mathrm{total}} = L_{\mathrm{data}} + \alpha L_{\mathrm{flow}} + \beta L_{\mathrm{latency}}
\]

其中：

\[
L_{\mathrm{data}} = \mathrm{CE}(\hat{y}, y)
\]

对每个时间窗口 \(w\)，先用模型预测出的攻击概率 \(p_{i,w}\) 形成加权聚合量：

\[
\mathrm{agg\_rate}_w = \sum_i p_{i,w} r_{i,w}
\]

\[
\rho_w = \frac{\mathrm{agg\_rate}_w}{C+\varepsilon}
\]

这里 \(C\) 是链路容量。

流量约束项写成：

\[
L_{\mathrm{flow}}
=
\frac{1}{|W|}\sum_{w}
\left[\max(\rho_w - 1, 0)\right]^2
\]

排队时延约束项写成：

\[
D^{\mathrm{theory}}_w = \frac{1}{1-\rho_w+\varepsilon}
\]

\[
L_{\mathrm{latency}}
=
\frac{1}{|W|}\sum_w
\max\left(D^{\mathrm{theory}}_w - \frac{\bar D^{\mathrm{obs}}_w}{D_{\mathrm{ref}}}, 0\right)
\]

因此，physics loss 的意义不是“强行替代分类损失”，而是在拥塞更明显的窗口中惩罚不符合流量守恒和 M/M/1 排队趋势的预测。

## 4. 联邦实验与统计公式

### 4.1 主要聚合器

设第 \(k\) 个客户端上传参数为 \(\mathbf{w}_k\)，样本量为 \(n_k\)。

`FedAvg`：

\[
\mathbf{w}^{(t+1)} = \sum_{k=1}^{K} \frac{n_k}{\sum_j n_j}\mathbf{w}_k^{(t)}
\]

`Coordinate-wise Median`：

\[
\mathbf{w}^{(t+1)}[m] = \mathrm{median}\left(\mathbf{w}_1[m], \dots, \mathbf{w}_K[m]\right)
\]

`Trimmed Mean`：

\[
\mathbf{w}^{(t+1)}[m]
=
\frac{1}{K-2k}
\sum_{j=k+1}^{K-k}
\mathbf{w}_{(j)}[m]
\]

其中 \(\mathbf{w}_{(j)}[m]\) 表示该坐标排序后的第 \(j\) 个值。

`Shapley Proxy` 在代码中的打分近似为：

\[
\mathrm{score}_i
=
\max(\cos(\Delta_i, \Delta_{\mathrm{ref}}), 0)
\cdot
\exp(-\mathrm{dist}(\Delta_i, \Delta_{\mathrm{ref}}))
\cdot
\max(0.05, \mathrm{train\_f1}_i)
\]

然后用归一化后的 score 作为权重做加权聚合。

### 4.2 评价指标

\[
\mathrm{Precision}=\frac{TP}{TP+FP}, \quad
\mathrm{Recall}=\frac{TP}{TP+FN}
\]

\[
F1 = \frac{2 \cdot \mathrm{Precision} \cdot \mathrm{Recall}}
{\mathrm{Precision} + \mathrm{Recall}}
\]

### 4.3 显著性检验

当前主套件使用 `paired sign-flip / permutation test`。

设成对差值为：

\[
d_i = x_i - y_i
\]

观测统计量为：

\[
T_{\mathrm{obs}} = \left|\frac{1}{n}\sum_{i=1}^{n} d_i\right|
\]

对应的双侧 p 值为：

\[
p =
\Pr\left(
\left|
\frac{1}{n}\sum_{i=1}^{n} s_i d_i
\right|
\ge T_{\mathrm{obs}}
\right),
\quad s_i \in \{-1, +1\}
\]

此外，当前 `paper_ready_plus` 还补了：

- Holm correction
- Benjamini-Hochberg correction

## 5. 当前最重要的实验结果

### 5.1 传统 central anti-leakage family：仍不显著

recharge 主套件：

- `temporal_ood`: `data_f1=0.993867`, `physics_f1=0.993493`, `p=0.515152`
- `topology_ood`: `data_f1=0.998194`, `physics_f1=0.998344`, `p=1.000000`
- `attack_strategy_ood`: `data_f1=0.998390`, `physics_f1=0.998593`, `p=0.636364`

batch2：

- `temporal_ood`: `data_f1=0.996872`, `physics_f1=0.996016`, `p=0.555556`
- `topology_ood`: `data_f1=0.986309`, `physics_f1=0.986875`, `p=0.777778`
- `attack_strategy_ood`: `data_f1=0.995455`, `physics_f1=0.995455`, `p=1.000000`

解释：

- 这条线已经可以明确归类为 `repeated null result`
- 因此不能再把“physics 在传统 OOD family 中稳定提升”写成主结论

### 5.2 联邦鲁棒聚合：当前最稳的 headline result

recharge pooled cross-protocol：

- `FedAvg F1 = 0.890659`
- `Shapley F1 = 0.980892`
- `Delta = +0.090232`
- `p = 0.000213617`

batch2 pooled cross-protocol：

- `FedAvg F1 = 0.905170`
- `Shapley F1 = 0.978659`
- `Delta = +0.073490`
- `p = 0.005847953`

high-poison 9-seed extension：

- `p(shapley vs fedavg) = 0.013645224`

解释：

- 这是当前最强、最稳定、最适合放在标题和摘要里的结果
- 它同时在主批次和 batch2 上成立

### 5.3 congestion-family：有正向信号，但不能写过头

recharge：

- `congestion_soft`: `delta_f1=0.001991`, `p=0.243593`
- `congestion_mid`: `delta_f1=0.001885`, `p=0.245057`
- `congestion_hard`: `delta_f1=0.001832`, `p=0.177691`
- `pooled`: `delta_f1=0.001903`, `p_raw=0.0275812`

全局多重校正后：

- `Holm_global = 0.193068`
- `BH_global = 0.0606785`

解释：

- 这条结果可以写成“方向正确、机制相关、pooled raw-significant”
- 但不能写成“经过严格全局校正后仍稳健显著”

### 5.4 classic robust FL baselines：已经补齐，而且结果不弱

pooled mean F1 相对 `FedAvg`：

- `median`: `0.985402`, `+0.015980`, `p=0.013645224`
- `trimmed_mean`: `0.986036`, `+0.016614`, `p=0.013645224`
- `rfa`: `0.985935`, `+0.016514`, `p=0.013645224`
- `multi_krum`: `0.978815`, `+0.009393`, `p=0.033138402`
- `bulyan`: `0.978236`, `+0.008814`, `p=0.033138402`
- `shapley_proxy`: `0.982720`, `+0.013298`, `p=0.017543860`
- `krum`: `0.975888`, `+0.006467`, `p=0.134502924`

解释：

- 现在可以清楚地说：强结果不是“只有 Shapley 才有效”
- 更准确的说法是：`robust aggregation family` 整体优于 `FedAvg`

### 5.5 运行成本：没有明显额外代价

主联邦套件运行时间：

- `clean / fedavg`: `17.67 +/- 0.11 s`
- `clean / median`: `17.74 +/- 0.14 s`
- `clean / shapley_proxy`: `17.64 +/- 0.14 s`
- `clean / trimmed_mean`: `17.60 +/- 0.09 s`

Stage-3：

- `clean / data_only`: `41.40 +/- 11.24 s`
- `clean / physics_stable`: `39.92 +/- 10.82 s`

解释：

- 目前没有看到“显著更鲁棒但明显更慢”的代价
- 这对会议稿是加分项

## 6. 当前结果的真实性边界

### 6.1 当前这轮不是 fresh Mininet 实重采

当前 WSL 宿主缺少 `openvswitch` 和 `tun` 内核能力，因此：

- 本轮不能声称“在当前机器上完成了可信 fresh recapture”
- 更准确的说法是：
  - 已完成代码修复
  - 已完成 corrupted manifest 拦截
  - 已完成基于 existing PCAP 的 graph rebuild 与 suite rerun

### 6.2 本轮对 legacy 高 bot 场景做的是 manifest-only repair

当前已修的 legacy 场景包括：

- `scenario_c_two_tier_high`
- `scenario_e_three_tier_high2`
- `scenario_f_two_tier_high2`
- `scenario_g_mimic_congest`
- `scenario_j_three_tier_high_b2`
- `scenario_k_two_tier_high_b2`

这些修复的意义是：

- 让 suite 不再把 target 错标为 bot
- 让现有 PCAP 能继续被一致地重建和评估

但它不等于：

- 完成新的真实抓包

### 6.3 batch2 是 capture-independent，不是 payload-fully-independent

当前 batch2 的正确表述应为：

- 独立抓包批次
- 独立场景名与 seed
- 但复用了同一批 payload pool

所以不能写成：

- fully independent regenerated data batch

## 7. 现在最合理的论文口径

如果按当前证据写论文，最稳的说法是：

1. 论文第一主结果：

\[
\text{Robust Federated Aggregation} \; > \; \text{FedAvg}
\quad \text{under poisoning}
\]

2. 论文第二主结果：

\[
\text{Physics-informed gain}
\]

只在 congestion-centric setting 中呈现为正向信号，且其 strongest pooled evidence 仅达到：

\[
p_{\mathrm{raw}} = 0.0276,
\quad
p_{\mathrm{Holm,global}} = 0.1931
\]

3. 明确保留负结果：

\[
\text{Traditional anti-leakage central family}
\not\Rightarrow
\text{significant PI gain}
\]

## 8. 当前实验状态一句话总结

截至 `2026-03-11`，`FedSTGCN` 已经完成一轮可写稿的主实验、batch2 外部验证、经典鲁棒联邦 baseline 和运行成本汇总；当前最可信的结论是“鲁棒联邦聚合在投毒设定下稳定优于 FedAvg”，而 central physics gain 只能作为拥塞场景下的次主结论，且必须保留其统计边界与当前 rerun provenance 的限制说明。
