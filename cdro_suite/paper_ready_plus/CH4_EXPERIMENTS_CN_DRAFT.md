# 第 4 章 实验与结果

本章是全文的实证核心。按照当前正文结构，本章不再把实验、主结果、部署读法和机制分析拆成过多章节，而是压缩为四个部分：首先交代主文需要的实验设置；然后给出主批次与 `external-J` 的核心结果；接着用 frozen-threshold 视角把结果翻译成部署侧指标；最后用机制分析解释为什么该收益会出现。整章的写作原则是证据先于判断，且所有主张都以主文 `4` 图 `2` 表加一个压缩机制段落为中心展开。

## 4.1 实验设置

本文在基于受控网络捕获构建的时空图上评估 `CDRO-UG`。主批次用于四种弱监督协议下的核心比较，`external-J` 用于检验同一训练机制在外部条件偏移场景下的迁移表现。除此之外，我们还保留了其他 external 场景、公共 HTTP benchmark、stress sweep、runtime、calibration、label budget 和非图参考基线等补充实验，但这些内容的作用主要是界定方法边界或回答审稿人可能提出的扩展问题，因此统一放入附录，而不占用主文主线。

主文采用四种 weak-supervision evaluation protocols：weak temporal OOD、weak topology OOD、weak attack-strategy OOD 和 label-prior shift OOD。这样的设置并不是为了制造更多结果表，而是为了覆盖几类最常见的训练-测试不匹配来源，并观察弱标签机制在不同失配条件下是否保持稳定。对于正文读法而言，这四个协议在主文中不再逐协议展开，而是统一汇总为 pooled 结果；更细的 per-protocol 结果保留在附录中，用于支撑审稿阶段的核查。

主文中的核心对比方法收束为三类：`Noisy-CE` 作为最直接的 hard-label weak-supervision 基线，`CDRO-Fixed` 作为“有 group robustness 但没有 uncertainty-guided prioritization”的结构对照，以及最终锁定版本 `CDRO-UG (sw0)`。附录中进一步加入 `Posterior-CE`、`CDRO-UG + PriorCorr` 以及更强的噪声鲁棒损失族，用于测试结果是否仅由 soft label、prior correction 或其他通用噪声稳健损失解释。与此同时，我们还在补充实验中提供了一个简单的非图参考基线 `XGBoost(weak)`，以区分“图结构建模增益”和“训练目标增益”各自的作用[1]。

主文报告的指标以 `F1` 和 `FPR` 为主，但两者在论文中的地位并不相同。`F1` 仍然用于说明总体检测质量是否保持在可接受范围内，而 `FPR` 则是本文的第一主指标，因为本文要解决的核心问题正是 benign false positives 在条件偏移下的部署代价。对于 `external-J`，主文进一步报告 frozen-threshold 视角下的 benign false alerts per run、alerts per `10k` benign nodes、attack-IP detect rate 和 mean first-alert delay，使结果从常见分类指标转化为更接近实际安全运营的系统读法。

统计检验方面，主文采用配对的 sign-flip 风格比较，对 matched protocol-seed runs 给出 raw paired significance。由于主文重点是建立清晰的结果层级，而不是在正文中展开统计学细节，因此正文只保留最关键比较的原始显著性；Holm 与 Benjamini-Hochberg 多重比较修正统一放入附录[2,3]。这一安排的目的，是在不稀释主文叙事的前提下，给审稿人提供足够的统计透明性。考虑到受控捕获数据无法完整公开，我们还准备了轻量级复现包，公开 graph / weak-label schema、split manifests、wrapper scripts 以及 sanitized node slice，以便外部读者复核公共 benchmark、reference baseline 和附录分析的执行接口。

## 4.2 核心结果：主批次与 external-J

【表 1 放置位置】

此处插入 `Table 1`，对应文件：
`table_maintext_core_results.csv`

表注占位：

`Table 1. 主批次与 external-J 的核心 pooled 结果。主批次用于说明方法在 source setting 下保持竞争性；external-J 用于报告 strongest supported result，即相对 Noisy-CE 的 pooled FPR 显著下降。`

放置说明：

该表应放在本节开头，在第一次解释主批次与 `external-J` 角色差异之前出现。读者应先看表，再读文字解释“主批次是 competitiveness control，external-J 是 strongest supported result”。

【图 2 放置位置】

此处插入 `Figure 2`，对应文件：
`fig1_pooled_results.png`

图注占位：

`Figure 2. 主批次与 external-J 的 pooled 结果总览。该图强调本文最稳定、最可辩护的正向证据不是 universal pooled-F1 gain，而是 external shift 下更低的 benign false-positive rate，同时 source batch 上 pooled 表现保持竞争性。`

放置说明：

该图建议紧跟 `Table 1` 之后，用于帮助读者在视觉上快速理解 source-vs-shift 的证据层级。

主文 `Table 1` 和 `Figure 2` 共同承担这一节的主要证据。对于 BlockSys 风格的论文，首先必须明确主批次和 `external-J` 在叙事上的角色不同。主批次的作用是证明方法在 source setting 下没有失稳，能够保持与已有 weak-label graph baseline 同一量级的性能；而 `external-J` 才是 strongest supported result 所在的位置，因为它最直接回答了“当运行环境发生变化时，模型是否能降低 benign-side false-positive burden”这一问题。

从主批次 pooled 结果看，`CDRO-UG (sw0)` 的 `F1` 为 `0.8694`，略高于 `Noisy-CE` 的 `0.8670` 和 `CDRO-Fixed` 的 `0.8622`；对应的 pooled `FPR` 分别为 `0.1626`、`0.1906` 和 `0.1887`。如果只看数值，`CDRO-UG` 在主批次上已经呈现出更好的 pooled `FPR` 和略高的 pooled `F1`。但本文不将这一结果写成 headline，原因很明确：与 `Noisy-CE` 的配对比较在 pooled `F1` 和 pooled `FPR` 上都未达到显著性。因此，主批次在正文中的正确读法只能是 competitiveness control，而不是“模型在 source batch 上已经取得决定性领先”。这种克制写法对于 BlockSys 审稿尤其重要，因为它避免把最弱的一段证据误写成最强的一段结论。

真正的 strongest supported result 出现在 `external-J`。在这一外部条件偏移批次上，`Noisy-CE` 的 pooled `F1` 与 pooled `FPR` 分别为 `0.8876` 和 `0.2695`，`CDRO-Fixed` 为 `0.8880` 和 `0.2368`，而 `CDRO-UG (sw0)` 为 `0.8852` 和 `0.2259`。从 `F1` 角度看，`CDRO-UG` 并没有构成显著优势，其相对 `Noisy-CE` 的 pooled `F1` 变化为 `-0.0023`，配对检验 `p = 0.5924`。但从 `FPR` 角度看，`CDRO-UG` 把 pooled `FPR` 从 `0.2695` 降到 `0.2259`，对应 `\Delta = -0.0436`，且配对检验 `p = 0.0051`。这正是本文最重要的结果，因为它并不是一个模糊的“整体更好”判断，而是一个对部署成本直接有意义、且具有配对显著性的 benign false-positive reduction。

`Figure 2` 的作用不是重复 `Table 1`，而是帮助读者快速看清这篇论文的证据层级。该图应被读成一个 source-vs-shift 对照图：在 source batch 上，`CDRO-UG` 体现的是“没有变差，且 pooled 表现具有竞争性”；在 shifted batch 上，`CDRO-UG` 体现的是“最稳定、最可辩护的优势来自 benign false positives 的下降”。换言之，`Figure 2` 要服务于一个克制但清楚的判断：本文的亮点不是 universal pooled-F1 gain，而是 external shift 下更可靠的 benign-side risk control。

这一节还需要明确一条边界：`external-J` 虽然是 strongest supported result，但它并不自动推出“所有 external 场景都一致改善”。更广泛的 multi-external 读法和 stronger baseline family 比较仍然保留在附录中。正文只需要把最重要的一点讲清楚即可：在当前所有可用结果中，`external-J` 上显著降低 `FPR` 的证据最强、最稳定，也最契合本文的系统目标。

## 4.3 frozen-threshold 部署迁移结果

【表 2 放置位置】

此处插入 `Table 2`，对应文件：
`table_maintext_deployment_transfer.csv`

表注占位：

`Table 2. external-J 上的 frozen-threshold deployment transfer。该表报告 source-locked threshold 下的 frozen F1、frozen FPR、attack-IP detect rate、mean first-alert delay，以及 analyst-facing benign false alerts per run 和 per 10k benign nodes。`

放置说明：

该表应放在本节开头。它是将 `external-J` pooled FPR 优势翻译成系统部署读法的关键证据，因此重要性高于额外机制图。

如果说 `Table 1` 回答的是“在 shifted batch 上 pooled `FPR` 是否下降”，那么 `Table 2` 回答的则是更接近实际部署的问题：当阈值不能在目标批次上重新调优时，这种收益是否仍然存在，以及它是否能被翻译为更低的告警负担。对 BlockSys 审稿人而言，这一节的重要性甚至不低于 `external-J` 的主结果，因为它把分类指标读法真正转化成了 operator-facing 的系统读法。

在 `external-J` 上，若使用从 matched main-batch run 锁定下来的 source threshold，`Noisy-CE` 的 frozen `F1 / FPR` 为 `0.874 / 0.168`，`CDRO-Fixed` 为 `0.827 / 0.239`，而 `CDRO-UG (sw0)` 为 `0.860 / 0.096`。这一结果首先说明，`CDRO-UG` 并没有因为阈值冻结而失去其 benign-side 优势；相反，它在 frozen-threshold 视角下仍然给出了三者中最低的 `FPR`。与 `Noisy-CE` 相比，`CDRO-UG` 的 frozen `FPR` 变化为 `-0.0718`，配对检验 `p = 0.0022`。也就是说，主文的 strongest result 在更严格的 source-locked deployment readout 下仍然成立。

更关键的是，这一优势可以被翻译成明显更低的 benign alert burden。`Noisy-CE` 在 frozen-threshold 下的平均 benign false alerts 为 `63.4` 次/run，每 `10k` benign 节点为 `1676` 次；`CDRO-UG` 分别降至 `36.1` 次/run 和 `958` 次/`10k` benign。对应地，`CDRO-UG` 相对 `Noisy-CE` 的平均 benign false alerts 变化为 `-27.3` 次/run，配对检验 `p = 0.0017`；每 `10k` benign 节点告警数变化为 `-717.7`，配对检验 `p = 0.0022`。对于一篇强调 trustworthy deployment 的论文，这组数字比单纯报告 tuned-threshold `FPR` 更有说服力，因为它直接说明在相同 source threshold 下，分析人员面对的 benign 告警负担会显著下降。

当然，这一部署收益并不是免费的。冻结阈值后，`CDRO-UG` 的 pooled `F1` 从 `Noisy-CE` 的 `0.874` 下降到 `0.860`；attack-IP detect rate 从 `0.990` 下降到 `0.978`；mean first-alert delay 从 `0.58` windows 增加到 `0.88` windows。换言之，`CDRO-UG` 的 deployment gain 并不是“更低误报且没有任何代价”，而是“以一定的覆盖与时延代价换取更低的 benign-side burden”。这种 tradeoff 恰恰是系统论文应该如实报告的内容。它表明本文不是在回避代价，而是在给出一个更接近真实部署的 operating-point choice：如果分析员负担和 benign 误报代价更重要，那么 `CDRO-UG` 提供了一个更保守但更可控的方案。

因此，这一节的最终结论应写得非常明确：`CDRO-UG` 的价值不只是 tuned-threshold 下的统计率改善，而是 source-locked threshold 下仍能保持更低的 benign false-positive burden，并把这一点翻译成 analyst-facing false alerts reduction。这正是本文最接近 BlockSys 风格系统贡献的证据链。

## 4.4 机制分析

【图 3 放置位置】

此处插入 `Figure 3`，对应文件：
`fig2_mechanism_probe.png`

图注占位：

`Figure 3. non-uniform prioritization 与 asymmetric trust 的机制 probe。该图用于在压缩版正文中承载最关键的机制证据，说明本文收益不是来自任意 soft-label trick，而是来自 uncertainty-guided group prioritization 与适度的 class-asymmetric trust 共同作用。`

放置说明：

该图建议放在本节开头，用于同时承担原 `Table 3` 的压缩机制摘要功能；两条 decisive probe 的具体数字直接写入正文，完整 ablation 表放入附录。

如果前两节回答的是“结果是什么”，这一节回答的就是“为什么会出现这样的结果”。在压缩到 `14` 页主文后，本节由 `Figure 3` 和 `Figure 4` 共同承担正文中的核心机制展示，附录中的 `table4_mechanism_probe.csv` 与 `table5_fp_sources.csv` 提供完整支撑。与许多只给出大量 ablation 结果的论文不同，本文的机制分析必须保持高度收束，只服务于一个问题：为什么 `CDRO-UG` 会在 `external-J` 上降低 benign false positives。

首先，`Figure 3` 对应的两条 decisive mechanism probes 给出了最关键的解释。其一是 non-uniform group prioritization。将 uncertainty-guided non-uniform weighting 替换为 uniform weighting 后，主批次 pooled `F1` 从 `0.8661` 降到 `0.8620`，对应 `\Delta = -0.0041`，配对检验 `p = 0.0149`。这说明本文方法并不是“只要用了 group-wise objective 就可以”，而是需要真的把更多训练压力放到高 uncertainty、high-risk 的条件组上。其二是 class-asymmetric trust。若把 benign trust 调得过低，`external-J` pooled `FPR` 会从 `0.2259` 升到 `0.2377`，对应 `\Delta = +0.0119`，配对检验 `p = 0.0007`。这说明本文结果也不是由任意 soft-label trick 带来的，而是依赖于对 weak attack 与 weak benign 赋予不同的、但又不过度激进的信任程度。

其次，弱标签审计为这一 trust mechanism 提供了数据层面的支持。附录中的 weak-label audit 显示，在当前任务设置下，weak attack labels 的精度整体高于 weak benign labels。这意味着 asymmetric trust 并不是一种拍脑袋式超参数偏好，而是对弱监督质量本身的一种建模响应。正文中不需要把 audit 的所有细节重新展开，但必须明确给出这一逻辑：之所以要对 benign 分支更保守，并不是因为 benign 更不重要，而是因为其 weak supervision 更不可靠，更容易把模型推向 benign-side overprediction。

【图 4 放置位置】

此处插入 `Figure 4`，对应文件：
`fig3_fp_sources.png`

图注占位：

`Figure 4. benign false-positive source decomposition。负向 delta 表示相对 Noisy-CE 减少 benign false alarms。该图用于说明 pooled FPR 的下降主要集中在 benign abstain、weak_benign 以及高 shift-risk 区域，而不是所有 bucket 上的平均改善。`

放置说明：

该图建议放在本节后半段，即开始解释“收益来自哪里”之前。这样正文中关于 `abstain`、`weak_benign`、`high-rho / low-u` 和 `high-rho / high-u` 的数字就能直接和图对应起来。

最后，`Figure 4` 进一步说明了收益究竟来自哪里。在 `external-J` pooled 视角下，`CDRO-UG` 在 `abstain` bucket 中把 benign `FPR` 从 `0.6364` 降到 `0.5753`，减少了 `123` 个 false positives；在 `weak_benign` bucket 中把 benign `FPR` 从 `0.0428` 降到 `0.0140`，减少了 `97` 个 false positives。若进一步看条件组分解，`high-rho / low-u` bucket 的 benign `FPR` 从 `0.0745` 降到 `0.0172`，`high-rho / high-u` bucket 则从 `0.6093` 降到 `0.5519`。这些数字的意义在于，它们把 pooled `FPR` 的下降具体落实到了本文原本就最关心的区域：不确定、易偏移、且 benign-side 更容易被错误推高的区域。也就是说，`CDRO-UG` 并不是在所有 bucket 上都平均变好，而是更集中地压低了最有部署代价的 benign false positives。

综合来看，这一节给出的机制解释仍然是闭合的。non-uniform group prioritization 说明模型知道“该把训练压力放在哪里”；class-asymmetric trust 说明模型知道“不同 weak signal 该信到什么程度”；`Figure 4` 则说明模型最终确实在目标失败模式上发挥了作用。正因为这三条证据能相互支撑，本文才可以把 `external-J` 的结果读成一个机制上可解释、部署上可翻译的 benign false-positive control result，而不仅仅是一组偶然更优的数字。

## 本章引用文献

[1] Chen, T., Guestrin, C.: XGBoost: a scalable tree boosting system. In: Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, pp. 785-794 (2016). https://doi.org/10.1145/2939672.2939785

[2] Holm, S.: A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics 6(2), 65-70 (1979). https://doi.org/10.2307/4615733

[3] Benjamini, Y., Hochberg, Y.: Controlling the false discovery rate: a practical and powerful approach to multiple testing. Journal of the Royal Statistical Society: Series B 57(1), 289-300 (1995). https://doi.org/10.1111/j.2517-6161.1995.tb02031.x
