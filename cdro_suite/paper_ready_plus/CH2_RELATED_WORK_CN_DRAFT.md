# 第 2 章 相关工作与论文定位

## 2.1 弱监督、noisy-label 学习与 shift-aware robust learning

弱监督学习的基本出发点，是在高质量人工标签难以大规模获得时，利用规则、启发式函数、已有模型、知识库或多个不完美标注源来构造训练信号[1,2]。这一方向的代表性工作表明，弱监督并不等同于简单的少量标注，而是要在多个弱标注源之间处理冲突、缺失和 abstention，并将这些不完美信号整合为可用于训练的监督信息[1]。从这一意义上看，弱监督为现实系统提供了比全监督更可扩展的标注路径，但它同时也把“监督质量不均匀”这一问题直接带入训练过程[1,2]。

与弱监督密切相关的是 noisy-label 学习。该方向的大量研究围绕标签污染下的稳健损失、样本选择、噪声建模和校正机制展开，其核心目标通常是尽可能恢复平均意义上的预测性能[3]。这类工作为理解错误标签如何影响决策边界、优化过程和泛化行为提供了重要基础[3]。然而，对本文关注的攻击检测场景而言，仅仅把弱标签视为平均意义上的 label noise 仍然不够，因为我们面对的不是均匀、静态且类别对称的噪声，而是随区域、上下文和样本覆盖情况变化的结构化监督异质性。换言之，本文的关键问题不是“如何在整体上容忍错误标签”，而是“当弱标签在不同条件区域中可靠性不同、且 benign-side 误报成本更高时，训练应如何重新分配压力”。

进一步看，shift-aware robust learning 与 domain generalization 文献为本文提供了另一个重要背景。相关综述指出，分布偏移会破坏训练和测试同分布假设，因此需要通过数据变换、表示学习或学习策略提升模型对未见域的稳定性[4,5]。这些研究强调了在 unseen domain 上维持性能的重要性，也推动了大量针对 OOD generalization 的方法设计[4,5]。但本文与这类工作仍有两个明显区别。第一，我们并不试图解决一般意义上的 unseen-domain generalization，而是聚焦弱监督攻击检测中的 conditional shift。第二，我们不把目标设为广义的 worst-case accuracy 或 universal generalization，而是把 benign false-positive control 作为更贴近部署成本的主目标。因此，本文与弱监督、noisy-label 学习以及 shift-aware robust learning 都相关，但它们都不足以直接覆盖“弱监督异质性 + 图结构关系 + benign 误报成本高”这一更具体的问题组合。

## 2.2 图攻击检测与本文定位

图表示学习为攻击检测提供了重要建模优势，因为网络流、主机、进程、会话乃至告警之间天然存在多种交互关系。近期综述系统总结了图神经网络在入侵检测中的应用，指出图构建方式、时变关系建模以及模型部署方式是这一方向的三个核心问题[6]。在具体方法层面，已有工作利用流拓扑构图和图卷积来提升 label-limited 场景下的入侵检测能力，也有研究通过动态图线图神经网络和半监督训练利用时序关系与结构关系改进检测性能[7,8]。这些结果说明，图模型相较于仅使用表格特征的检测器，更适合表达通信实体之间的关联结构。

除了网络流层面的关系图，system-level provenance graph 方向也表明，图结构能够更自然地承载攻击历史相关性、依赖链条和上下文语义，从而支持 threat detection 与 investigation[9]。从更广泛的时空异常检测研究来看，图结构和时间结构的联合建模对于识别随位置和上下文变化的异常模式同样重要[10]。这些研究共同说明，图建模已经不再只是表示层面的技术选择，而是安全检测中刻画复杂行为依赖关系的重要工具。

尽管如此，现有图攻击检测工作大多仍默认监督信号相对可靠，或者把主要目标放在总体分类性能提升上[6-10]。即使在 label-limited 或 semisupervised 设定下，相关方法通常也更关注“如何更好地利用图结构补偿标签不足”，而较少明确处理 weak attack 与 weak benign 信号在可信度上的非对称性，更少把 benign false positives 作为训练目标的核心约束[7,8]。本文因此采取不同定位。我们不是提出一种新的图神经网络架构，也不是试图给出一个对所有 noisy-label baseline 都普遍占优的通用方案。相反，本文将图模型视为已有时空关系建模骨架，把主要创新放在训练机制上：通过 uncertainty-guided conditional robustness 与 class-asymmetric trust，在 weakly supervised spatiotemporal graph attack detection under conditional shift 的场景下，更直接地抑制部署代价较高的 benign false positives。基于这一定位，本文更接近一篇面向 trustworthy deployment 的机制论文，而不是架构论文或普适噪声学习论文。

## 本章引用文献

[1] Ratner, A.J., Bach, S.H., Ehrenberg, H.R., Fries, J.A., Wu, S., Ré, C.: Snorkel: rapid training data creation with weak supervision. VLDB Journal 29, 709-730 (2020). https://doi.org/10.1007/s00778-019-00552-1

[2] Zhou, Z.-H.: A brief introduction to weakly supervised learning. National Science Review 5(1), 44-53 (2018). https://doi.org/10.1093/nsr/nwx106

[3] Frénay, B., Verleysen, M.: Classification in the presence of label noise: a survey. IEEE Transactions on Neural Networks and Learning Systems 25(5), 845-869 (2014). https://doi.org/10.1109/TNNLS.2013.2292894

[4] Zhou, K., Liu, Z., Qiao, Y., Xiang, T., Loy, C.C.: Domain generalization: a survey. IEEE Transactions on Pattern Analysis and Machine Intelligence 45(4), 4396-4415 (2023). https://doi.org/10.1109/TPAMI.2022.3195549

[5] Wang, J., Lan, C., Liu, C., Ouyang, Y., Qin, T.: Generalizing to unseen domains: a survey on domain generalization. In: Proceedings of the 30th International Joint Conference on Artificial Intelligence (IJCAI), pp. 4627-4635 (2021). https://doi.org/10.24963/ijcai.2021/628

[6] Zhong, M., Lin, M., Zhang, C., Xu, Z.: A survey on graph neural networks for intrusion detection systems: methods, trends and challenges. Computers & Security 141, 103821 (2024). https://doi.org/10.1016/j.cose.2024.103821

[7] Deng, X., Zhu, J., Pei, X., Zhang, L., Ling, Z., Xue, K.: Flow topology-based graph convolutional network for intrusion detection in label-limited IoT networks. IEEE Transactions on Network and Service Management 20(1), 684-696 (2023). https://doi.org/10.1109/TNSM.2022.3213807

[8] Duan, G., Lv, H., Wang, H., Feng, G.: Application of a dynamic line graph neural network for intrusion detection with semisupervised learning. IEEE Transactions on Information Forensics and Security 18, 699-714 (2023). https://doi.org/10.1109/TIFS.2022.3228493

[9] Li, Z., Chen, Q.A., Yang, R., Chen, Y.: Threat detection and investigation with system-level provenance graphs: a survey. Computers & Security 106, 102282 (2021). https://doi.org/10.1016/j.cose.2021.102282

[10] Deng, L., Lian, D., Huang, Z., Chen, E.: Graph convolutional adversarial networks for spatiotemporal anomaly detection. IEEE Transactions on Neural Networks and Learning Systems 33(6), 2416-2428 (2022). https://doi.org/10.1109/TNNLS.2021.3136171
