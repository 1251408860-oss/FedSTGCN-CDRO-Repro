# 第 1 章 引言

网络攻击检测正在越来越多地依赖数据驱动模型，但高质量、细粒度且可持续更新的标签在真实环境中通常昂贵、滞后并且不完整。弱监督为这一问题提供了更现实的训练路径：标签可以来自规则、签名、已有检测器、威胁情报或少量人工校验，而不必完全依赖逐样本人工标注[1,2]。这一设定降低了标注成本，也更贴近实际安全运营流程。然而，弱监督带来的并不只是“标签更少”，而是监督质量在不同样本、不同区域和不同阶段上都可能显著不均匀。

这类监督异质性不能被简单视为平均意义上的随机噪声。已有研究指出，弱监督往往同时包含不完整监督、粗粒度监督和不准确监督三类问题[2]；而标签噪声会改变分类边界、提高学习难度，并削弱模型在分布变化下的稳定性[3]。对攻击检测而言，这一点尤其关键，因为弱标签通常来自启发式规则和历史检测逻辑，其可靠性并不会在所有流量区域中保持一致。某些区域可能具有较强的攻击侧证据，而另一些区域则主要由模糊的 benign 启发式、规则缺失或多视角不一致构成。若训练过程只是在平均意义上拟合这些弱标签，模型就可能在部署时对不确定区域产生系统性过响应。

对入侵检测系统而言，真正昂贵的失败模式也不只是总体精度下降，而是 benign false positives 的持续膨胀。经典研究已经指出，在攻击基率很低的场景下，即使检测器具有看似较高的分类准确率，误报仍可能主导告警流并使系统难以使用[4]。后续关于误报抑制和 IDS 技术综述的工作也反复表明，false alarm reduction 是部署层面的核心问题，而不是结果表中的附带指标[5-7]。因此，如果一篇攻击检测论文只报告 pooled F1，而不交代 benign-side false-positive behavior，就很难回答模型是否真正适合部署。

与此同时，图神经网络和图表示学习正在成为攻击检测的重要建模工具，因为网络流、主机、会话和告警之间天然具有关系结构。近期综述和具体方法表明，图模型能够利用流拓扑、动态图关系以及有限标注来提升检测性能[8-10]。时空图异常检测研究也进一步说明，异常判据往往随时间和上下文变化，单一静态读法难以充分刻画复杂行为[11]。但现有图攻击检测工作大多默认监督信号相对可靠，或把目标放在整体分类性能上。对于“弱监督 + 条件偏移 + 误报成本高”这一组合场景，现有方法仍缺少足够聚焦的训练机制。

本文研究的正是这一更窄但更实际的问题：当弱标签的可靠性在时空图的不同区域中呈现明显异质性时，能否通过条件鲁棒训练抑制部署代价更高的 benign false positives。我们将这一问题表述为 weakly supervised spatiotemporal graph attack detection under conditional shift，并提出 `CDRO-UG`。该方法将 uncertainty-guided conditional DRO 与 class-asymmetric trust 结合起来，使模型在训练时对不确定且更易出错的区域施加更高鲁棒压力，并对 weak attack 与 weak benign 信号赋予不同信任程度。本文的目标不是构造一个对所有 noisy-label baseline 都普遍占优的通用学习器，而是设计一个在特定部署风险下更可靠的训练机制。

现有实验结果支持这一更克制的定位。`CDRO-UG` 在主批次四种弱监督协议上整体保持竞争性，但最强且最可信的正向证据出现在外部条件偏移批次 `external-J`：相对 `Noisy-CE`，pooled false-positive rate 从 `0.2695` 降至 `0.2259`，配对检验 `p = 0.0051`；在 source-locked threshold 下，平均 benign false alerts 从 `63.4` 次/run 降至 `36.1` 次/run，每 `10k` benign 节点告警数从 `1676` 降至 `958`。与此同时，这一收益并非免费，模型在 `F1`、attack-IP detect rate 和 first-alert delay 上存在可测 tradeoff。基于这一完整读法，本文将 `CDRO-UG` 定位为面向 trustworthy deployment 的 benign false-positive control mechanism，而不是 universal superiority paper。

本文的主要贡献如下。

1. 我们将弱监督攻击检测在 conditional shift 下的问题重新表述为一个部署导向的问题，其中核心风险不是平均精度下降，而是 benign false-positive escalation 与 analyst alert burden 上升。
2. 我们提出 `CDRO-UG`，将 uncertainty-guided conditional DRO 与 class-asymmetric trust 结合起来，在不引入复杂伪样本扩展的前提下，对结构化弱监督中的高风险区域施加更强训练压力。
3. 我们在外部偏移批次 `external-J` 上给出最强实证证据，并进一步用 frozen-threshold 读法把统计指标翻译成 operator-facing alert-burden reduction。
4. 我们通过 non-uniform prioritization、asymmetric trust 和 benign false-positive source decomposition 的机制分析解释收益来源，并明确给出方法边界，而不做 universal overclaim。

全文其余部分安排如下。第 `2` 章讨论相关工作并说明本文定位；第 `3` 章给出问题定义与 `CDRO-UG` 方法；第 `4` 章报告实验设置、核心结果、部署迁移结果与机制分析；第 `5` 章讨论方法边界、附录导向证据与全文结论。

## 本章引用文献

[1] Ratner, A.J., Bach, S.H., Ehrenberg, H.R., Fries, J.A., Wu, S., Ré, C.: Snorkel: rapid training data creation with weak supervision. VLDB Journal 29, 709-730 (2020). https://doi.org/10.1007/s00778-019-00552-1

[2] Zhou, Z.-H.: A brief introduction to weakly supervised learning. National Science Review 5(1), 44-53 (2018). https://doi.org/10.1093/nsr/nwx106

[3] Frénay, B., Verleysen, M.: Classification in the presence of label noise: a survey. IEEE Transactions on Neural Networks and Learning Systems 25(5), 845-869 (2014). https://doi.org/10.1109/TNNLS.2013.2292894

[4] Axelsson, S.: The base-rate fallacy and the difficulty of intrusion detection. ACM Transactions on Information and System Security 3(3), 186-205 (2000). https://doi.org/10.1145/357830.357849

[5] Hubballi, N., Suryanarayanan, V.: False alarm minimization techniques in signature-based intrusion detection systems: a survey. Computer Communications 49, 1-17 (2014). https://doi.org/10.1016/j.comcom.2014.04.012

[6] Buczak, A.L., Guven, E.: A survey of data mining and machine learning methods for cyber security intrusion detection. IEEE Communications Surveys & Tutorials 18(2), 1153-1176 (2016). https://doi.org/10.1109/COMST.2015.2494502

[7] Khraisat, A., Gondal, I., Vamplew, P., Kamruzzaman, J., Alazab, A.: Survey of intrusion detection systems: techniques, datasets and challenges. Cybersecurity 2, 20 (2019). https://doi.org/10.1186/s42400-019-0038-7

[8] Zhong, M., Lin, M., Zhang, C., Xu, Z.: A survey on graph neural networks for intrusion detection systems: methods, trends and challenges. Computers & Security 141, 103821 (2024). https://doi.org/10.1016/j.cose.2024.103821

[9] Deng, X., Zhu, J., Pei, X., Zhang, L., Ling, Z., Xue, K.: Flow topology-based graph convolutional network for intrusion detection in label-limited IoT networks. IEEE Transactions on Network and Service Management 20(1), 684-696 (2023). https://doi.org/10.1109/TNSM.2022.3213807

[10] Duan, G., Lv, H., Wang, H., Feng, G.: Application of a dynamic line graph neural network for intrusion detection with semisupervised learning. IEEE Transactions on Information Forensics and Security 18, 699-714 (2023). https://doi.org/10.1109/TIFS.2022.3228493

[11] Deng, L., Lian, D., Huang, Z., Chen, E.: Graph convolutional adversarial networks for spatiotemporal anomaly detection. IEEE Transactions on Neural Networks and Learning Systems 33(6), 2416-2428 (2022). https://doi.org/10.1109/TNNLS.2021.3136171
