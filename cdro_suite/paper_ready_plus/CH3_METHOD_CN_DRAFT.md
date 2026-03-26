# 第 3 章 问题定义与方法

本章给出本文问题定义与 `CDRO-UG` 方法。按照导师建议，本章不再把问题定义、方法细节和版本说明拆成更多小节，而是压缩为三个部分：首先定义弱监督时空图攻击检测问题及其关键统计量；然后给出类别非对称信任与条件分组机制；最后定义 `CDRO-UG` 的目标函数、训练流程以及最终锁定版本。

## 3.1 问题定义与弱标签统计

本文考虑一个时空图攻击检测任务。记图为

```latex
\[
\mathcal{G} = (\mathcal{V}, \mathcal{E}, X),
\]
```

其中，`\(\mathcal{V}\)` 表示节点集合，`\(\mathcal{E}\)` 表示边集合，`\(\mathbf{X}\)` 表示节点特征矩阵。每个节点 `\(i \in \mathcal{V}\)` 对应一个流量时间窗或通信单元，其潜在真实标签记为

```latex
\[
y_i \in \{0,1\},
\]
```

其中 `\(y_i = 1\)` 表示攻击，`\(y_i = 0\)` 表示 benign。与传统全监督设定不同，训练阶段并不总能获得所有节点的真实标签，而是只能获得若干 weak-label views。记第 `\(m\)` 个弱监督视角给出的类别后验为

```latex
\[
\mathbf{p}_i^{(m)} \in [0,1]^2, \qquad m = 1,2,\dots,M.
\]
```

这些 weak-label views 可以来自启发式规则、已有检测器、历史标签逻辑或多源弱标注器。本文不要求每个视角都覆盖所有样本，也不要求这些视角之间完全一致。对具有 weak supervision 的节点集合，记为

```latex
\[
\mathcal{I} = \{ i \in \mathcal{V} \mid i \text{ has weak supervision} \}.
\]
```

对于每个 `\(i \in \mathcal{I}\)`，我们首先将多个弱监督视角聚合为一个统一弱后验

```latex
\[
\tilde{\mathbf{p}}_i = \mathrm{Agg}\!\left(\mathbf{p}_i^{(1)}, \mathbf{p}_i^{(2)}, \dots, \mathbf{p}_i^{(M)}\right),
\]
```

并定义对应的弱硬标签为

```latex
\[
\tilde{y}_i = \arg\max_{c \in \{0,1\}} \tilde{\mathbf{p}}_{i,c}.
\tag{1}
\]
```

在此基础上，我们从 weak-label views 中提取三个对后续训练至关重要的统计量。

第一，不确定性 `\(u_i\)`。它用于衡量聚合后弱标签的置信程度。直观上，当多个视角意见分散、或聚合后后验接近决策边界时，`\(
u_i
\)` 应更大。形式上，我们将其记为

```latex
\[
u_i = U\!\left(\tilde{\mathbf{p}}_i, \{\mathbf{p}_i^{(m)}\}_{m=1}^{M}\right), \qquad u_i \in [0,1].
\tag{2}
\]
```

第二，一致性 `\(a_i\)`。它用于描述多视角弱标签之间的一致程度。若不同视角对节点 `\(i\)` 给出相近判断，则 `\(a_i\)` 较大；反之则较小。记为

```latex
\[
a_i = A\!\left(\{\mathbf{p}_i^{(m)}\}_{m=1}^{M}\right), \qquad a_i \in [0,1].
\tag{3}
\]
```

对应的分歧量可写为

```latex
\[
d_i = 1 - a_i.
\tag{4}
\]
```

第三，条件偏移代理量 `\(\rho_i\)`。它用于刻画样本位于更高 shift risk 区域的程度。由于本文关注的是 conditional shift，而不是单纯的总体 label noise，因此仅使用平均损失或平均置信度并不足以区分真正高风险的弱监督区域。我们因此保留一个由 weak-label statistics 派生的 shift-sensitive proxy：

```latex
\[
\rho_i = R\!\left(\tilde{\mathbf{p}}_i, u_i, a_i, \{\mathbf{p}_i^{(m)}\}_{m=1}^{M}\right).
\tag{5}
\]
```

基于上述记号，本文的问题不再是“如何在整体上拟合弱标签”，而是“在弱标签可靠性沿时空图呈现异质性分布时，如何把训练压力更多地放到 uncertainty 更高、shift risk 更大的区域，同时避免 benign-side 的过度预测”。这一定义决定了后续方法设计的两个核心原则：

1. 训练过程需要显式区分条件风险不同的样本区域；
2. weak attack 与 weak benign 信号不应被对称对待。

## 3.2 类别非对称信任与条件分组

【图 1 放置位置】

此处插入 `Figure 1`，对应文件：
`fig_method_overview.svg`

图注占位：

`Figure 1. 方法与部署整体框架。上半部分展示 weak supervision views 如何被聚合为 uncertainty、agreement、shift proxy 和 class-asymmetric trust，并进一步进入 conditional DRO 目标；下半部分展示训练完成后的 detector 如何通过 source-frozen threshold 迁移到 external shifted batch，并以 pooled F1、FPR 和 alert-burden 指标进行部署侧评估。`

放置说明：

该图应放在本节开头靠前位置，先于公式展开。其作用不是提供细节，而是让读者在进入 trust score、conditional groups 和目标函数之前，先建立整套方法的全局视图。

本文方法的第一个关键设计是类别非对称信任。直观上，weak attack signal 和 weak benign signal 在很多安全场景中并不具有相同质量。攻击侧弱标签往往来自更强的规则命中、事件关联或历史攻击模式，而 benign 侧 weak label 则更容易受到覆盖不足、规则空缺和上下文歧义影响。因此，如果训练时对两类 weak signal 赋予完全相同的信任程度，模型就更容易在 benign 区域中产生过预测。

基于这一判断，本文为每个训练样本定义一个 trust score `\(t_i\)`。设 `\(c_i\)` 表示一个由 weak posterior 派生的置信统计量，则 trust score 定义为

```latex
\[
t_i =
\begin{cases}
\alpha_{\mathrm{atk}} \, f_{\mathrm{atk}}(a_i, c_i), & \tilde{y}_i = 1, \\
\alpha_{\mathrm{ben}} \, f_{\mathrm{ben}}(a_i, c_i, u_i), & \tilde{y}_i = 0,
\end{cases}
\tag{6}
\]
```

其中，`\(\alpha_{\mathrm{atk}}\)` 与 `\(\alpha_{\mathrm{ben}}\)` 分别是 attack 类与 benign 类的全局信任系数，且通常满足

```latex
\[
\alpha_{\mathrm{atk}} > \alpha_{\mathrm{ben}}.
\tag{7}
\]
```

这表示在最终锁定版本中，模型对 weak attack evidence 保持相对更高的信任，而对 weak benign evidence 更保守。特别地，benign 分支中的函数 `\(f_{\mathrm{ben}}(\cdot)\)` 显式依赖 `\(u_i\)`，意味着当 weak supervision 本身更不确定时，benign 信号会被进一步折减。

在 trust score 基础上，训练目标不直接使用单一硬标签，而是构造软目标

```latex
\[
\mathbf{q}_i
=
t_i \cdot \mathrm{onehot}(\tilde{y}_i)
\;+\;
(1-t_i)\tilde{\mathbf{p}}_i.
\tag{8}
\]
```

其中，`\(\mathrm{onehot}(\tilde{y}_i)\)` 表示由弱硬标签生成的 one-hot 向量。式 `(8)` 的含义是：当 trust score 较高时，训练目标更接近弱硬标签；当 trust score 较低时，训练目标更多保留弱后验中的不确定信息。这样做的目的，不是简单引入 soft label，而是利用类别非对称信任把 weak attack 与 weak benign 的质量差异编码到训练目标中。

本文方法的第二个关键设计是条件分组。由于我们关注的是 conditional shift，而不是全局平均风险，因此训练过程需要识别“哪些区域更值得被鲁棒性目标重点关注”。在最终实现中，我们使用 `\(u_i\)` 与 `\(\rho_i\)` 的训练集统计量来构造条件组。记

```latex
\[
b_u(i) = \mathbb{I}\!\left[u_i > \mathrm{med}_{j \in \mathcal{I}}(u_j)\right],
\qquad
b_{\rho}(i) = \mathbb{I}\!\left[\rho_i > \mathrm{med}_{j \in \mathcal{I}}(\rho_j)\right],
\tag{9}
\]
```

其中，`\(\mathbb{I}[\cdot]\)` 为指示函数，`\(\mathrm{med}(\cdot)\)` 表示中位数。于是每个样本被映射到一个条件组

```latex
\[
g_i = 2\,b_u(i) + b_{\rho}(i), \qquad g_i \in \{0,1,2,3\}.
\tag{10}
\]
```

这四个组可分别理解为：

1. 低 uncertainty、低 shift risk；
2. 低 uncertainty、高 shift risk；
3. 高 uncertainty、低 shift risk；
4. 高 uncertainty、高 shift risk。

这里的组并不对应某种语义类别，而是为了显式暴露弱监督质量和部署风险的条件异质性。相比直接在全体样本上使用统一损失，条件分组使模型能够在训练时区分“应当被优先照顾的高风险区域”和“相对稳定的低风险区域”。

## 3.3 CDRO-UG 目标函数、伪代码与最终锁定版本

在得到软目标 `\(\mathbf{q}_i\)` 与条件组 `\(g_i\)` 后，本文将训练过程写为一个 uncertainty-guided conditional DRO 目标。记模型 `\(f_{\theta}\)` 对节点 `\(i\)` 输出的预测后验为 `\(\hat{\mathbf{p}}_i = f_{\theta}(i)\)`，则单样本软交叉熵损失定义为

```latex
\[
\ell_i
=
- \sum_{c \in \{0,1\}} q_{i,c}\log \hat{\mathbf{p}}_{i,c}.
\tag{11}
\]
```

基于所有有 weak supervision 的节点，基础损失写为

```latex
\[
\mathcal{L}_{\mathrm{base}}
=
\frac{1}{|\mathcal{I}|}\sum_{i \in \mathcal{I}} \ell_i.
\tag{12}
\]
```

对于每个条件组 `\(g\)`，对应的组损失写为

```latex
\[
\mathcal{L}_g
=
\frac{1}{|\mathcal{I}_g|}\sum_{i \in \mathcal{I}_g}\ell_i,
\qquad
\mathcal{I}_g = \{ i \in \mathcal{I} \mid g_i = g \}.
\tag{13}
\]
```

与固定 worst-group objective 不同，本文不直接把所有权重都压到单一最坏组，而是为每个组构造一个 priority score。该分数同时考虑该组的当前损失、平均 uncertainty 与平均分歧量：

```latex
\[
\pi_g
=
\lambda_{\mathrm{loss}}\mathcal{L}_g
\;+\;
\lambda_u \bar{u}_g
\;+\;
\lambda_d \bar{d}_g,
\tag{14}
\]
```

其中，

```latex
\[
\bar{u}_g = \frac{1}{|\mathcal{I}_g|}\sum_{i \in \mathcal{I}_g} u_i,
\qquad
\bar{d}_g = \frac{1}{|\mathcal{I}_g|}\sum_{i \in \mathcal{I}_g} d_i.
\tag{15}
\]
```

给定 priority score 后，组权重通过温度参数为 `\(\tau\)` 的 softmax 计算：

```latex
\[
w_g
=
\frac{\exp(\pi_g/\tau)}
{\sum_{g'}\exp(\pi_{g'}/\tau)}.
\tag{16}
\]
```

最终，`CDRO-UG` 的训练目标写为

```latex
\[
\mathcal{L}_{\mathrm{CDRO\text{-}UG}}
=
(1-\lambda)\mathcal{L}_{\mathrm{base}}
\;+\;
\lambda \sum_g w_g \mathcal{L}_g.
\tag{17}
\]
```

式 `(17)` 的作用是，把训练压力从“平均拟合所有 weak labels”改成“在保持基础风险的同时，把更多关注分配给高 uncertainty、高 disagreement、且当前更易出错的条件组”。这也是本文将其称为 uncertainty-guided conditional robustness 的原因。

为便于后续排版与实现描述，`CDRO-UG` 的训练流程可写成如下伪代码。

【算法 1 放置位置】

算法标题占位：

`Algorithm 1. Training Procedure of CDRO-UG (sw0).`

放置说明：

该算法应紧跟在式 `(17)` 之后。其作用是把前面的数学定义压缩成一个可执行流程，便于导师和审稿人快速理解“weak-label aggregation -> trust-aware target construction -> conditional group weighting -> parameter update -> source-locked deployment transfer”的整体顺序。

```latex
\begin{algorithm}[t]
\caption{Training Procedure of CDRO-UG (sw0)}
\label{alg:cdro_ug}
\KwIn{Spatiotemporal graph $\mathcal{G}$, weak-label views $\{\mathbf{p}_i^{(m)}\}$, model $f_{\theta}$, trust coefficients $\alpha_{\mathrm{atk}}, \alpha_{\mathrm{ben}}$, objective coefficients $\lambda, \lambda_{\mathrm{loss}}, \lambda_u, \lambda_d$, temperature $\tau$}
\KwOut{Trained model parameters $\theta$}

\For{each training epoch}{
    Aggregate weak-label views to obtain $\tilde{\mathbf{p}}_i$ and $\tilde{y}_i$ for all $i \in \mathcal{I}$\;
    Compute weak-label statistics $u_i$, $a_i$, $d_i$, and shift proxy $\rho_i$\;
    Construct conditional groups $g_i$ by median-thresholding $u_i$ and $\rho_i$\;
    Compute trust score $t_i$ using class-asymmetric trust\;
    Build soft target $\mathbf{q}_i = t_i \cdot \mathrm{onehot}(\tilde{y}_i) + (1-t_i)\tilde{\mathbf{p}}_i$\;
    Run forward pass and obtain prediction $\hat{\mathbf{p}}_i = f_{\theta}(i)$\;
    Compute per-sample loss $\ell_i$, group loss $\mathcal{L}_g$, and group priority $\pi_g$\;
    Compute group weights $w_g$ with temperature-controlled softmax\;
    Form final objective $\mathcal{L}_{\mathrm{CDRO\text{-}UG}}$ and update $\theta$\;
}
Lock the operating threshold on the source validation split and transfer the trained detector to the target batch for deployment-style evaluation\;
\end{algorithm}
```

需要强调的是，本文主文使用的最终版本不是所有探索变体的简单叠加，而是锁定为 `CDRO-UG (sw0)`。该版本具有如下特征：

1. 仅使用 covered-only weak supervision；
2. 保留类别非对称信任；
3. 保留 non-uniform conditional group prioritization；
4. 不使用 pseudo-sample expansion；
5. 不额外引入 sample-weight amplification。

选择这一版本的原因并不是它在所有设置下都最复杂或最强，而是它在当前实验链条中提供了最清晰的机制解释。它能够把本文的核心思想收束为一句话：利用 weak-label uncertainty 和 shift proxy 识别高风险区域，并通过 class-asymmetric trust 与 conditional robustness 抑制 benign false positives 的部署代价。对本研究而言，这种机制清晰性比继续叠加更多训练技巧更重要。

## 本章说明

本章以本文方法定义为主，因此不额外引入必须单列的新外部参考文献。与 weak supervision、noisy-label learning、domain generalization 和图攻击检测相关的文献背景，已经在第 `2` 章中统一交代。后续若在英文正式稿中需要补充与 `DRO` 或 `group robustness` 直接对应的经典引用，可在第 `2` 章相关工作中统一补入，而不建议在本章再次重复展开。
