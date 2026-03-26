# 第 5 章 边界、附录导向证据与结论

本章承担全文最后的收束任务。到第 `4` 章结束时，正文已经给出了本文最重要的正向证据链：`external-J` 上更低的 pooled benign `FPR`、frozen-threshold 视角下更低的 alert burden，以及由 non-uniform prioritization 与 class-asymmetric trust 支撑的机制解释。因此，本章不再继续扩展正向 headline，而是集中完成两件事：第一，明确哪些证据只能作为边界、局限或附录支持，而不能被提升为主结论；第二，在这些边界被充分披露之后，对本文可以成立的贡献范围给出一个克制但清晰的最终结论。

## 5.1 边界、局限与附录导向证据

【附录证据放置说明】

本章正文不新增主文图表。考虑 `BlockSys` 主文 `14` 页限制，本章涉及的 supporting evidence 统一导向附录，建议按如下方式排布：

1. `Table A7`：多 external 场景的 direction consistency；
2. `Table A8`：pooled external-4 validation 与 stronger noisy-label baselines；
3. `Table A9`：multiple-testing corrections 与 runtime；
4. `Table A10`：calibration 与 operating-point 补充；
5. `Table A11`：hard/camouflaged protocols 与 stress sweeps；
6. `Table A12`：public benchmark、label-budget 与 non-graph / clean-label references；
7. `Table A13`：full deployment supplement、family breakdown 与 analyst-facing cases。

首先，本文最需要明确的边界，是 `external-J` 的正向结果不能被自动外推成普遍外部泛化结论。第 `4` 章已经说明，当前最强支持证据出现在 `external-J`：相对 `Noisy-CE`，`CDRO-UG` 的 pooled benign `FPR` 从 `0.2695` 降到 `0.2259`，且配对检验 `p = 0.0051`。但当四个 external 场景被合并读取时，pooled `F1` 与 `FPR` 对 `Noisy-CE` 都不再构成显著优势，且 pooled `ECE / Brier` 还更差。附录 `Table A7` 进一步给出的只是“部分一致性”而不是“稳定泛化”：在 tuned-threshold 视角下，`FPR` 方向只在 `J/K/L` 三个场景上与主结论一致，而 `I` 场景出现反向结果。因此，这组证据的正确读法不是“方法对外部分布变化普遍有效”，而是“方法在一个外部条件偏移场景上呈现了清晰正向结果，并在更广外部集合上表现出有限、但不充分的方向支持”。从更一般的 shift-aware learning 视角看，这样的结果更接近 regime-specific external robustness，而不是广义 domain generalization 声明[2]。

其次，附录中的 stronger-baseline、public benchmark 与 reference-baseline 结果进一步收窄了本文结论。附录 `Table A8` 表明，在部分 pooled 指标上，更强的 noisy-label baselines 仍然可以与 `CDRO-UG` 竞争，甚至在个别设置中取得更低的 `FPR`。这意味着本文不能被写成“统一优于现有 noisy-label 方法”的论文，而应被写成“在特定目标和特定风险读法下更有价值”的论文。附录 `Table A12` 则说明，公共数据上的补充实验更适合作为 completeness evidence，而不是新的 headline。以 `Biblio-US17` 为例，`Noisy-CE` 仍有最高的 mean `F1 = 0.842`；`CDRO-UG` 只是在 mean `FPR` 上表现出极小且不显著的方向性下降（`0.023` 对 `0.025`），同时 `ECE / Brier` 也不占优。类似地，label-budget 曲线说明方法在仅保留 `5%` 到 `10%` 弱标签覆盖率时仍然可用，但并不能支持“普遍更强的低标注效率”表述。non-graph 与 clean-label reference 结果也应按边界来读：`XGBoost(weak)` 这类非图参考基线可以提供有价值的比较视角[1]，但它并不能替代图结构建模；与此同时，`PI-GNN(clean)` 仍显著高于所有弱监督方法，说明当前瓶颈主要仍然来自 supervision quality，而不只是模型骨干。

再次，附录 `Table A9` 到 `Table A13` 中的运行代价、部署补充、family breakdown、stress sweeps 和 analyst-facing case studies，主要作用是回答“方法在哪些意义上可用”与“方法在哪些地方会失效”，而不是给主文增加新的亮点。runtime 补充说明 `CDRO-UG` 在当前 CPU-only 设置下仍处于与 `Noisy-CE` 接近的计算量级，这有助于排除“结果来自不可接受的额外计算成本”这一质疑，但并不足以支撑任何“更快”或“更高效”的泛化结论。full deployment supplement 也只能加强 tradeoff 解释，而不能把 tradeoff 本身抹去：frozen-threshold 转移虽然保住了更低的 external-J `FPR` 与更低的 benign alert burden，但同时带来了更低的 `F1`、更低的 attack-IP detect rate 和更慢的 first-alert delay。calibration 与 operating-point 补充同样只能作为 completeness evidence，因为它们没有形成比 `external-J` pooled `FPR` 更强的主结论。hard/camouflaged 协议和 stress sweep 的意义更偏向 operating boundary discovery。经过合并配对修正后，hard/camouflaged pooled delta 接近于零，而 heavy flip-noise stress 则暴露出当前方法在“方向性错误弱标签”下的明显弱点。换言之，现有 `CDRO-UG` 更能容忍 weak-label coverage loss，而不擅长处理大比例 adversarially wrong weak labels。这样的边界并不会削弱论文，反而会使其更符合安全检测论文对失败模式透明披露的要求；经典研究早已指出，在 IDS 中误报负担本身就足以使看似准确的检测器难以部署[3]。

综合这些附录证据，可以得到一个更准确的适用范围判断：`CDRO-UG` 最适合的不是任意 noisy-label 场景，而是 covered-only weak supervision、结构化 uncertainty 异质性、存在 conditional shift、且 benign-side false-positive control 比追求平均 pooled 指标更重要的场景。也正因如此，本文的后续工作不应简单继续扩充模型复杂度，而更应聚焦于两个方向：其一，如何在 weak labels 出现方向性错误时重新设计 trust mechanism；其二，如何在不显著增加主文复杂度的前提下，引入更轻量的 shift-aware adaptation 机制[2]。这两点都比把当前结果改写成更强表述更重要。

## 5.2 结论

本文研究的是一个比“通用 noisy-label 学习”更窄、但对真实检测系统更有意义的问题：在弱监督时空图攻击检测中，当监督可靠性随条件区域变化、并且部署成本主要体现为 benign false-positive escalation 时，训练机制能否更有针对性地控制风险。围绕这一问题，本文提出 `CDRO-UG`，将 uncertainty-guided conditional robustness 与 class-asymmetric trust 结合到统一训练目标中。全文最强的实证支持并不来自主批次 pooled 指标，而来自 `external-J`：相对 `Noisy-CE`，`CDRO-UG` 将 pooled benign `FPR` 从 `0.2695` 降到 `0.2259`，并在 frozen-threshold 视角下把 false alerts/run 从 `63.4` 降到 `36.1`，把每 `10k` benign 节点的 alerts 从 `1676` 降到 `958`。第 `4` 章中的机制分析进一步说明，这一收益并不是任意 soft-label trick 的副产物，而是与 non-uniform group prioritization 和 weak-label class-asymmetric trust 的联合作用直接相关。

同样重要的是，本文也明确给出了这一结论不能被扩大到什么程度。当前结果并不支持 universal pooled-accuracy superiority，也不支持“对所有 external 场景都稳定显著更优”的说法；public benchmark 只能作为 completeness evidence，而不是新的正向 headline；stronger noisy-label baselines、hard/camouflaged 协议和 heavy flip-noise stress 也都清楚地界定了方法边界。因此，本文更准确的定位应当是：`CDRO-UG` 是一种面向 structured weak supervision 与 conditional shift 的 scoped mechanism，其最可靠价值在于 deployment-costly benign false-positive control，而不是作为任意 noisy-label regime 下的通用最优解。这样的结论也与安全检测系统长期强调误报负担的基本认识一致[3]。如果按这一范围理解本文，那么它的贡献、证据和局限就是彼此一致的。

## 本章引用文献

[1] Chen, T., Guestrin, C.: XGBoost: a scalable tree boosting system. In: Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, pp. 785-794 (2016). https://doi.org/10.1145/2939672.2939785

[2] Zhou, K., Liu, Z., Qiao, Y., Xiang, T., Loy, C.C.: Domain generalization: a survey. IEEE Transactions on Pattern Analysis and Machine Intelligence 45(4), 4396-4415 (2023). https://doi.org/10.1109/TPAMI.2022.3195549

[3] Axelsson, S.: The base-rate fallacy and the difficulty of intrusion detection. ACM Transactions on Information and System Security 3(3), 186-205 (2000). https://doi.org/10.1145/357830.357849
