# BlockSys 中文目录（导师建议收敛版）

截至 `2026-03-24`，`BlockSys 2026` 官方 `CFP` 仍写明：

`Papers must ... not exceed 14 pages ... in Springer LNCS format.`

官方来源：
- https://blocksys.info/2026/call-for-papers/

因此更安全的执行方式是：

1. 投稿主文版严格控制在 `14` 页内；
2. 另备 `4` 页附录作为导师版 / 补充材料版；
3. 在官方未明确“附录不计页数”之前，不默认把附录并入主投稿 PDF。

## 导师建议后的正文结构

按导师建议，正文压成 `5` 章主结构：

1. 第 `1` 章：零小节
2. 第 `2` 章：`2` 个小节
3. 原第 `3` 章与第 `4` 章合并为新的第 `3` 章，共 `3` 个小节
4. 原第 `5` 章收束为新的第 `4` 章，共 `4` 个小节
5. 原第 `6` 章与第 `7` 章合并为新的第 `5` 章，共 `2` 个小节

## 推荐目录

### 摘要

报告问题、方法、`external-J` 主结果、deployment tradeoff。

### 第 1 章 引言

不拆小节，连续完成：

1. 问题定义；
2. 部署风险；
3. 方法与贡献；
4. strongest supported claim。

### 第 2 章 相关工作与论文定位

#### 2.1 弱监督、noisy-label 学习与 shift-aware robust learning
#### 2.2 图攻击检测与本文定位

### 第 3 章 问题定义与方法

#### 3.1 问题定义与弱标签统计
#### 3.2 类别非对称信任与条件分组
#### 3.3 CDRO-UG 目标函数与最终锁定版本

### 第 4 章 实验与结果

#### 4.1 实验设置
#### 4.2 核心结果：主批次与 external-J
#### 4.3 frozen-threshold 部署迁移结果
#### 4.4 机制分析

### 第 5 章 边界、附录导向证据与结论

#### 5.1 边界、局限与附录导向证据
#### 5.2 结论

## 图表安排

正文只保留：

1. `Figure 1`：方法与部署框架
2. `Table 1`：核心 pooled 结果
3. `Figure 2`：source-vs-shift 总览
4. `Table 2`：frozen-threshold deployment transfer
5. `Figure 3`：机制 probe
6. `Figure 4`：false-positive source decomposition

其中：
1. `Table 3` 不再作为正文单列表，而改写成 `4.4` 中的压缩机制段落，并由附录机制表支撑；
2. 只恢复最能服务 failure-mode 解释的 `Figure 4`，不恢复 `Table 3`。

推荐位置：

1. `Figure 1` 放第 `3` 章
2. `Table 1` 与 `Figure 2` 放 `4.2`
3. `Table 2` 放 `4.3`
4. `Figure 3` 与 `Figure 4` 放 `4.4`

## 主文页数预算

1. 摘要：`0.35` 页
2. 第 `1` 章：`1.50` 页
3. 第 `2` 章：`1.00` 页
4. 第 `3` 章：`2.80` 页
5. 第 `4` 章：`5.00` 页
6. 第 `5` 章：`1.10` 页
7. 参考文献：`1.10` 页

合计建议控制在 `12.85` 页左右。

## 附录 4 页建议

### 附录 A：完整主结果与显著性

1. `table1_main_results.csv`
2. `table2_batch2_results.csv`
3. `table3_significance.csv`

### 附录 B：机制补充

1. `table4_mechanism_probe.csv`
2. `table5_fp_sources.csv`
3. `table6_weak_label_quality.csv`
4. `fig4_weak_label_quality.png`

### 附录 C：边界补充

1. `table20_external_direction_consistency.csv`
2. `table11_strong_baselines.csv`
3. `table15_public_http_benchmark.csv`
4. `table14_stress_sweeps.csv`

### 附录 D：复现与补充部署说明

1. artifact / reproducibility 说明
2. deployment supplement 简述
3. schema / split manifest / wrapper / sanitized sample 说明

## 执行原则

1. 正文严格按 `5` 章收束；
2. 主文只保留 `4` 图 `3` 表；
3. 其余 supporting evidence 转入 `4` 页附录；
4. 若投稿系统不允许附录单独上传，则附录仅保留为导师版或补充材料准备版。
