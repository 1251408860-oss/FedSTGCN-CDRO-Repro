# 中文摘要与贡献点

## 中文摘要

弱监督攻击检测在实际部署中常常依赖不完美的启发式标签，而这些弱标签的可靠性在不同数据区域上并不均匀，尤其在条件分布偏移下更为明显。本文研究时空图攻击检测中的这一问题，提出一种基于不确定性的条件分布鲁棒训练目标 CDRO-UG。该方法将非均匀组优先级分配与弱标签的类别非对称信任机制结合起来，使模型在训练时更关注高不确定、易出错的条件区域。实验表明，该方法并不在所有设置下都带来普遍的 pooled 性能提升，但在外部分布偏移批次上能够更稳定地抑制 benign false positives，这是本文最可靠的正向结果。机制实验进一步表明，这一收益依赖于非均匀组加权和 attack/benign 弱标签的非对称信任设计；错误来源分析也显示，收益主要集中在 benign abstain 和 weak-benign 区域，而不是来自全局性的统一改进。进一步的 deployment-oriented 检查表明，在 main 批次锁定阈值后，CDRO-UG 仍能在 external-J 上保持最低 FPR，但需要接受一定的 F1 与首报时延 tradeoff；family breakdown 和 analyst-facing case studies 则把这种收益具体落实到 slowburn / mimic 家族和可解释的单案例上。补充的公开 HTTP benchmark、supervision-budget、non-graph baseline、clean-label upper bound 与 reproducibility package 进一步明确了方法的适用边界、部署读法与可复现材料。总体而言，本文更适合被理解为一种面向结构化弱监督与条件偏移场景的机制型方法，而不是对任意噪声标签都普适有效的通用鲁棒学习器。

## 中文贡献点

1. 我们将条件分布偏移下的弱监督攻击检测形式化为一个条件鲁棒性问题，并明确将 benign false-positive escalation 视为核心部署风险，而不仅仅关注 pooled accuracy。
2. 我们提出了 CDRO-UG 训练目标，将非均匀组优先级分配与弱标签的类别非对称信任机制结合起来；最终锁定版本不依赖伪样本扩样，从而保留了更清晰的机制解释。
3. 我们证明该方法最可靠的经验收益出现在外部分布偏移批次上，表现为 benign false-positive suppression；同时通过机制消融、弱标签审计和错误来源分解解释了该收益何时出现、为何出现。
4. 我们补充了公开可复现的 HTTP benchmark、监督预算曲线，以及 non-graph baseline / clean-label upper bound，使论文可以直接回答 public comparability、label efficiency 和 supervision ceiling 三类审稿问题。
5. 我们进一步补充了 frozen-threshold external test、per-attack-family breakdown、analyst-facing case studies 与轻量级 reproducibility package，使论文可以直接回答 deployment tradeoff、family-specific behavior 和 artifact transparency 三类问题。
6. 我们表明该方法最适合的使用场景是：covered-only weak supervision、moderate structured noise，以及 benign-side false-positive control 比普适 pooled superiority 更重要的条件偏移环境。

## 中文实验结论摘要

从整体实验结果来看，CDRO-UG 并不是一个在所有 noisy-label 条件下都全面占优的方法。它最硬的正向证据来自 external-J 批次，在该外部分布偏移场景下，相比 Noisy-CE 能显著降低 pooled FPR。更重要的是，机制实验表明该收益不是简单来源于 soft labels，而是来源于不确定组优先分配与 attack/benign 非对称信任的联合作用。新补的 deployment-oriented 检查进一步说明：当阈值从 main 批次冻结到 external-J 时，CDRO-UG 仍保持最低 FPR，但需要接受更低的 F1 和略差的 attack-IP 首报时延；per-family breakdown 还表明 `burst` 仍是所有方法共同的 hardest family。补充的 public HTTP benchmark、budget sweep、XGBoost(weak)、PI-GNN(clean) 与 reproducibility package 则进一步说明：该方法在可复现 public data 上是竞争性的，在低监督预算下仍可用，但并不存在普遍的 label-efficiency 优势，而且与 clean-label ceiling 之间仍有明显差距。因此，本文最合适的定位不是“通用 noisy-label robustness”，而是“在结构化弱监督与条件偏移下，面向 benign false-positive control 的机制型方法”。
