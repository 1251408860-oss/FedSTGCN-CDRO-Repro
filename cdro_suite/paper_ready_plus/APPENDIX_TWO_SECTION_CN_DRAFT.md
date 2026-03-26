# 附录（两节四页压缩版）

本附录服务于两个目的。第一，把正文中为了页数压缩而没有展开的完整实验结果、统计检验与边界证据集中呈现出来，使审稿人能够复核主文结论的证据来源。第二，把正文中已经使用但未完全展开的机制分析与轻量复现说明补齐，从而把本文的正向证据、边界条件与透明性要求连接起来。附录的写作原则与正文保持一致：不新增主线，不引入新的 headline，只补足正文已经明确提出但受篇幅限制无法展开的 supporting evidence。

## 附录 A 补充实验结果、统计检验与边界证据

本节集中补充三类信息：一是主批次与 `external-J` 的完整 per-protocol 结果；二是正文中未展开的 paired significance 与 multiple-testing readout；三是所有会收窄结论、但又必须对审稿人透明披露的边界证据。为了控制附录总篇幅，建议本节只保留两张紧凑表，而不再把每类补充实验都拆成独立小节。

【表 A1 放置位置】

此处插入 `Table A1`，建议由以下源文件汇总生成：
`table1_main_results.csv`
`table2_batch2_results.csv`
`table3_significance.csv`

表注占位：

`Table A1. 主批次与 external-J 的完整 per-protocol 结果及配对统计检验。表中保留四种 weak-supervision protocols 的结果、对应 pooled 行，以及与正文主比较一致的 paired significance；如需给出多重比较校正，可在表注中说明 Holm 与 Benjamini-Hochberg 校正的读取方式。`

放置说明：

该表应放在本节开头，承担“把正文 pooled 结果展开给审稿人看”的任务。

`Table A1` 的正确读法首先是区分主批次与 `external-J` 的角色。主批次完整结果用于说明 `CDRO-UG` 没有在 source 条件下明显失稳，它更像一个 competitiveness control，而不是本文的 headline。即使在 per-protocol 视角下，主批次 pooled `F1` 对 `Noisy-CE` 的优势也较小，且配对检验不显著。因此，主批次结果只能支撑“方法在源域保持可比竞争力”，不能支撑“方法在常规设置下全面优于现有 weak-label baseline”的表述。与此相对，`external-J` 的完整结果才是正文主张真正落脚的地方。把 pooled 行再展开到各 protocol 后可以看到，`CDRO-UG` 的收益主要仍然集中在 benign-side false-positive behavior，而不是普遍的 pooled `F1` 提升。这一结果与正文保持一致：本文最强正向结论是外部条件偏移下的 benign false-positive suppression，而不是 universal pooled-accuracy gain。

`Table A1` 同时还承担统计解释功能。正文中已经报告了最关键的 paired `p` 值，但在审稿视角下，完整的 per-protocol 结果只有在配套统计读法下才有意义。因此，本表建议保留 raw paired significance，并在表注中说明 family-wise 解释遵循 Holm 校正[1]，全局多重比较风险可参考 Benjamini-Hochberg 控制[2]。这里的目的不是制造更多显著结果，而是防止审稿人误以为正文只选择性展示了支持性数字。也正因为附录显式给出完整统计结果，正文才可以更克制地只保留 pooled headline。

【表 A2 放置位置】

此处插入 `Table A2`，建议由以下源文件压缩汇总生成：
`table20_external_direction_consistency.csv`
`table10_external4_validation.csv`
`table11_strong_baselines.csv`
`table15_public_http_benchmark.csv`
`table14_stress_sweeps.csv`
如版面允许，可补一行来自 `table17_non_graph_clean_upper.csv` 的 reference-baseline 摘要。

表注占位：

`Table A2. 边界证据摘要。该表汇总 multi-external direction consistency、pooled external-4 validation、stronger noisy-label baselines、public benchmark、stress sweep 以及可选的 non-graph / clean-label reference，用于说明本文为何不做过强表述。`

放置说明：

该表应放在 `Table A1` 之后，用一张摘要表集中回答“为什么这篇论文的结论是 scoped 而不是 universal”。

`Table A2` 首先应明确，多 external 结果只能支持“部分一致性”，而不能支撑普遍 external generalization。当前最稳妥的表达是：在 tuned-threshold 视角下，`CDRO-UG` 的 `FPR` 方向在 `J/K/L` 三个外部场景上与正文主结论一致，但 `I` 场景反向，且 pooled external 结果对 `Noisy-CE` 不显著。这样的证据并不推翻 `external-J` 的正向结果，但它确实要求本文把结论限定在“特定 external shifted condition 上的更低 benign false positives”，而不能写成“对外部分布变化稳定更优”。换言之，附录在这里的作用不是给正文“加码”，而是把正文为什么保持克制说清楚。

其次，stronger noisy-label baselines 与 pooled external-4 validation 进一步界定了本文的结论边界。附录应明确写出：在部分 pooled 指标上，更强的 noisy-label baselines 仍可与 `CDRO-UG` 竞争，甚至在个别设置中取得更低的 `FPR`。这说明 `CDRO-UG` 不是 uniformly strongest noisy-label learner。相应地，pooled external-4 validation 也不应被解释为新的正向主结果，而应被解释为“主结果没有被完全推翻，但也没有在 broader pooled external view 下继续增强”。这种写法对于系统与安全方向的论文是必要的，因为审稿人更关心作者是否如实界定 operating regime，而不是是否堆砌更多看似正向的 aggregate numbers。

再次，public benchmark 与 stress-sweep 结果的功能应被明确限定为 completeness evidence。以 `Biblio-US17` 为例，`Noisy-CE` 仍具有更高的 mean `F1 = 0.842`，而 `CDRO-UG` 仅在 mean `FPR` 上表现出极小且不显著的方向性下降（`0.023` 对 `0.025`，`p = 1.0`）。因此，公共数据实验不应用来重写正文 headline，它更适合说明：本文在一个可复现公共场景上并未失效，但也并未形成新的正向主张。同样，heavy flip-noise stress 与 hard/camouflaged suite 的作用是界定 operating boundary，而不是增加正向结果。附录应明确说明，当前方法更能容忍 weak-label coverage loss，而在大比例方向性错误 weak labels 下会明显退化；合并配对修正后的 hard/camouflaged pooled delta 也接近于零。这些结果都不应被隐藏，因为它们正是这篇论文之所以能够避免过强表述的关键证据。

如果 `Table A2` 仍有余量，最值得增加的一行是 non-graph / clean-label reference readout，用于把“方法为什么仍然值得图学习社区关注”说清楚：`XGBoost(weak)` 这类非图参考方法可以在个别 `FPR` 读法上看起来更保守，但通常需要接受更低的 pooled `F1`；与此同时，`PI-GNN(clean)` 明显高于所有弱监督方法，说明当前瓶颈主要仍在 supervision quality，而不是图骨干已经无用。加上这一行后，附录 A 的结论就会更完整：它不仅说明本文为什么不能 overclaim，也说明正文为何仍然可以把问题定位在“structured weak supervision 下的 graph-based benign false-positive control”上。

## 附录 B 机制补充与轻量复现说明

本节补充正文中已经出现但未完全展开的机制证据，并在最后给出轻量复现说明。由于正文已经保留了 `Figure 3` 和压缩机制段落，本节的写法不应再重新讲一遍方法，而应直接回答两个问题：第一，为什么正文中的机制解释是可信的；第二，在原始受控捕获不能公开的前提下，审稿人能够复核到什么程度。

【表 B1 放置位置】

此处插入 `Table B1`，建议由以下源文件汇总生成：
`table4_mechanism_probe.csv`
`table_maintext_mechanism_summary.csv`

表注占位：

`Table B1. 完整机制 probe 与压缩机制摘要。该表保留正文中两条 decisive probes 的完整上下文，并展示 non-uniform prioritization 与 benign trust 调节如何影响主批次 pooled F1 和 external-J pooled FPR。`

放置说明：

该表建议放在本节开头，使正文中的压缩机制段落在附录中有一张可核查的完整表。

`Table B1` 的核心作用，是证明正文中那两条机制判断并非从大表中挑选出的孤立数字。其一，当 uncertainty-guided non-uniform weighting 被 uniform weighting 替换后，主批次 pooled `F1` 从 `0.8661` 降到 `0.8620`，对应 `\Delta = -0.0041`，配对检验 `p = 0.0149`。这说明本文方法并不是“只要写成 DRO 形式就足够”，真正起作用的是把更大的训练压力施加到高 uncertainty、high-risk 的条件组上。其二，当 benign trust 被进一步调低时，`external-J` pooled `FPR` 会从 `0.2259` 上升到 `0.2377`，对应 `\Delta = +0.0119`，配对检验 `p = 0.0007`。这说明结果也不是任意 soft-label smoothing 就能得到，而是依赖于对 weak attack 与 weak benign 采用不同但不过度激进的信任机制。附录在这里的意义，是把正文中压缩过的机制叙述重新放回完整 ablation 上下文中，使审稿人能够确认机制解释与具体数字是一一对应的。

由于 `fig3_fp_sources.png` 已恢复为正文中的 `Figure 4`，本节不再重复放置同一张图，而只保留与其对应的表格和解释段落。正文 `Figure 4` 回答的是“收益到底来自哪里”这一更细的问题：在 `external-J` pooled 视角下，`CDRO-UG` 在 `abstain` bucket 中把 benign `FPR` 从 `0.6364` 降到 `0.5753`，减少了 `123` 个 false positives；在 `weak_benign` bucket 中把 benign `FPR` 从 `0.0428` 降到 `0.0140`，减少了 `97` 个 false positives。若进一步看条件组分解，`high-rho / low-u` bucket 的 benign `FPR` 从 `0.0745` 降到 `0.0172`，`high-rho / high-u` bucket 则从 `0.6093` 降到 `0.5519`。这组结果说明，`CDRO-UG` 并不是在所有区域上平均变好，而是更集中地压低了最有部署代价的 benign false positives。附录在这里的任务不再是重复可视化，而是通过 `table5_fp_sources.csv` 保留更完整的 bucket-level 支撑，使正文 `Figure 4` 的解释可以被逐项核查。

如果本节仍有少量余量，最值得增加的是一个极小的 weak-label audit 摘要表，用 `table6_weak_label_quality.csv` 的核心行说明：在当前任务设置下，weak attack labels 的精度整体高于 weak benign labels。这一补充并不是为了新增一个结论，而是为了让 class-asymmetric trust 的设计不显得像纯经验超参数。即使最终不单独排成一张表，也建议在正文 `Figure 4` 之后用两三句话明确写出这一点，从而把“trust design 有数据支持”这个逻辑闭合起来。

本节最后需要用一个简短小段落交代轻量复现说明。建议直接沿用 artifact package 的写法：由于受控捕获图和原始流量不能公开，本文不提供完整原始数据发布，而是提供一个 lightweight reproducibility package，用于暴露数据接口和附录分析的 replay hooks。该包至少应包括 `schema/graph_schema.json`、`schema/weak_label_sidecar_schema.json`、`protocol_split_manifests/main_protocol_splits.json`、`protocol_split_manifests/external_j_protocol_splits.json`、若干 replay wrapper scripts，以及 `sample/sanitized_node_slice.json`。这一定义的正确口径是 transparency and replay support，而不是 full raw-data release。换言之，附录 B 需要清楚告诉审稿人：他们可以检查图结构、weak-label sidecar 与公共/参考分析链路的复现入口，但不能直接获得私有受控捕获的原始流量。这种表述既不会夸大可复现性，也不会在 artifact 透明性上显得过于含糊。

综上，两节附录与正文的关系应当非常明确。附录 A 解释“为什么正文只做 scoped claim”，附录 B 解释“为什么正文的机制解释值得相信，以及审稿人能复核到什么程度”。只要附录坚持这一分工，它就会是正文的支撑，而不会变成第二条叙事主线。

## 本附录引用文献

[1] Holm, S.: A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics 6(2), 65-70 (1979). https://doi.org/10.2307/4615733

[2] Benjamini, Y., Hochberg, Y.: Controlling the false discovery rate: a practical and powerful approach to multiple testing. Journal of the Royal Statistical Society: Series B 57(1), 289-300 (1995). https://doi.org/10.1111/j.2517-6161.1995.tb02031.x

[3] Chen, T., Guestrin, C.: XGBoost: a scalable tree boosting system. In: Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, pp. 785-794 (2016). https://doi.org/10.1145/2939672.2939785
