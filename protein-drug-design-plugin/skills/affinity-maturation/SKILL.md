---
name: affinity-maturation
description: >
  抗体/纳米抗体多位点突变亲和力成熟设计与级联筛选流水线（TNFR1 实证固化）。Use when
  用户要对已有抗体做亲和力成熟/affinity maturation（多位点 CDR 突变设计）、从专利或文献
  实验数据挖谱系建突变体数据集、做热点扫描/丙氨酸扫描定设计位与约束、用多引擎
  （LigandMPNN/AntiBMPNN/IgGM/RFD4-Proteina/AnewOmni）建突变文库并做跨引擎共识、
  或规划级联漏斗（liabilities→triage→精筛→正交→能量→终检）与融合排名交付。
  关键词：亲和力成熟、affinity maturation、热点扫描、丙氨酸扫描、alanine scan、
  设计位、约束文件、突变文库、LigandMPNN、AntiBMPNN、IgGM、RFD4 抗体微调、
  位点共识、级联筛选、融合排名、突变体数据集、CDR 突变。
  边界（蛋白药物设计插件内置版）：结构预测与批量推理走 structure-prediction-analysis
  （本技能的 C 阶段级联复用其双轴四象限管线）；能量计算走其 Germinal relax 协议；
  跨阶段编排走 protein-design-workflow；MD 验证走 md-simulation-workflow。
---

# 亲和力成熟：多位点突变设计与级联筛选 (Affinity Maturation)

固化自 TNFR1-SDAbs 战役（2026-11 全程，872 行 handoff 实证）：从 GSK/Domantis 专利
数据出发，经热点扫描→五引擎文库→六端级联漏斗→三源融合排名，交付 7 条提交候选
（独立终审 ALL PASS）。核心思想：**已有实验数据（谱系/KD/pose）作先验与校准锚，
AI 计算作生成与筛选引擎，两者在每个 gate 上交叉验证**。

## 0. 何时使用

- 对已绑定抗体（有 WT 结构/序列+可选 KD）做多轮突变提升亲和
- 从专利/文献挖抗体谱系并建突变体数据集（计算校准用）
- 规划"设计位→约束→多引擎文库→级联筛选→融合排名"全流程
- 竞赛/交付场景的序列合规（新颖性/队内去重）与独立终审

## 1. 七阶段总流程

```text
阶段0 FR溯源 → A 热点扫描 → B 多引擎文库 → C 级联漏斗 → C4 能量 → C5 终检 → D 交付
   ANARCII      丙氨酸扫描     五引擎+共识      算力经济       双口径秩融合   赛方/验证口径   独立终审
```

| 阶段 | 核心动作 | 关键产出 |
|---|---|---|
| 0 FR 溯源 | ANARCII FR/CDR 切分 + 胚系鉴定 + **FR 招募位排查** | 锁死清单（FR+二硫+招募位） |
| A 热点 | 单模板界面重提 + 丙氨酸扫描（**3 构象×N 重复**） | 四类决策表 + **三约束文件** |
| B 文库 | 五引擎并行 + 验收 + 统一池 | 位点级跨引擎共识 + 排序预表 |
| C 级联 | liabilities→5s triage→30s 精筛→25s 正交 | 各级幸存名单+读数表 |
| C4 能量 | Germinal relax **4 观测均值**主轴（N(0,0.03Å) 扰动 rep ×3 + 原观测；std>2 REU=HIGH_VAR 参与分层）+ MMGBSA 观察 | 双能量秩 + flag + mean4/std4 |
| C5 终检 | 独立口径引擎（赛方/ESMFold2）WT 基线 | ≥WT 过线名单 |
| D 交付 | 融合排名 + 合规 + 独立终审 | 提交池 + SPR 建议序 |

命令级全流程实例与坑：[references/tnfr1-playbook.md](references/tnfr1-playbook.md)
五引擎对比与约束兼容性：[references/engine-matrix.md](references/engine-matrix.md)

## 2. 数据资产层（先于一切设计，"已有数据"侧）

1. **专利/文献挖掘**：谱系（谁是亲本）、KD/kon/koff 数值表、选择压语义（蛋白酶抗性筛选 ≠ 亲和提升——勿混读）
2. **谱系修正纪律**：引入突变 vs 亲本态要靠原始文献图表定案（TNFR1 实例：206 的 H95 是抗胰酶引入突变、Y95 才是亲本——"家族修复"解读曾被反转）
3. **突变体数据集**：谱系+双坐标突变（Kabat↔seq）+实验字段+计算指标+**分辨率边界声明**（本套计算对 <2× KD 差异无分辨率——诚实写入 README）
4. **计算校准**：有实验值的家族做方向一致性校验（如 OD 组装率与 KD 序同向）
5. **pose 一一致性验证**：家族变体逐条叠合（Bio.PDB.Superimposer，勿手写 Kabsch）——同 pose ⇒ 突变差异可归因界面局部化学 ⇒ **位点叠加/组合设计合法**；pose 切换则需分姿态处理

## 3. 十二条方法论铁律（全部实证）

| # | 铁律 | 出处 |
|---|---|---|
| 1 | **浅读数不作设计依据**（triage 级 ipTM/组装率只够排序与排除，突变设计必须等计算深化） | R2 撤回（用户裁决） |
| 2 | **单模板原则**：热点与 pose 基准用单一最高分结构（如 ipTM 全局最优 seed），多构象只用于挤过信度 | 计划 v2（用户裁决） |
| 3 | 丙氨酸扫描**多构象×多重复**（3×5 起），单构象会把波动位误判勿动位 | A1+（v1 14 勿动位 6 位降级实证） |
| 4 | **Pro/Gly 特殊残基双重不确定**（读数不可信+无家族耐受+环几何基石）→ 默认锁死 | 约束 v3 |
| 5 | **三约束文件分引擎消费**：B1-B3 固定+允许 / B4 抗原锚点（annotated CIF hotspot）/ C1 表位 gate（core+extended Jaccard） | A0+/A1+ |
| 6 | 文库引擎**族间共识>族内一致**：固定 pose 序列族（LMPNN/AntiBMPNN/IgGM）+ 骨架微调族（RFD4）+ 生成式族（AnewOmni）互补选型 | B 阶段 |
| 7 | **引擎出局也是产出**：全段生成式引擎与位点级约束不兼容的实证要记录（AnewOmni B5 全灭 = 约束体系按设计工作的证明） | B5 定性 |
| 8 | **位级共识标记**：同位点跨引擎突变一致 = 最高优先实验项（TNFR1：30A→S 四引擎一致；交付期 D107E 48/49+Y108H 46/49=亲和主驱动推断） | B6/D |
| 9 | **级联算力经济**：零 GPU 的（liabilities 序列扫描）最先，其次 5s triage，30s/25s 只给幸存者；**跑与定线解耦**（WT σ 极窄时改池内分位定线） | C0/C0.5 |
| 10 | 双能量口径分歧（PyRosetta vs MMGBSA ρ=-0.177）→ **秩融合，单口径排名不可信**；融合权重显式（0.5 能量+0.25 表位收敛+0.25 正交） | C4/融合 |
| 11 | **跨引擎绝对值不可比铁律**：ipSAE/ipTM 只在同引擎同口径内比（ESMFold2 vs Mol-1 系统差 0.077 实证）；正交引擎读数一律注记级 | C2/C5 |
| 12 | **独立终审不读中间产物**：从原始 fasta/json/库全量重算（fasta↔json 逐字节、CDR 窗 join 逐位 diff、新颖性复核、队内去重） | 阶段 D（ALL PASS） |

## 4. C 阶段级联与现有技能的衔接

- 姿态收敛 + 表位 gate：**复用 structure-prediction-analysis 双轴四象限管线**（site/pose 指纹 Jaccard 聚类 + Wilson lb；轴二与 gate 重合不重复引入）
- ipSAE 双轴：官方 ipsae.py（PAE 10/蒸馏 10），`need_atom_confidence true` 拿全 PAE；键名适配器（Mol/OD `token_pair_pae` vs AF3 `pae`）
- 能量：Germinal relax 协议（见 structure-prediction-analysis references/germinal-relax-protocol.md）；MMGBSA 用 Schrodinger Prime（`-WAIT` 必加）
- 独立终检引擎（C5）：换一个"无 MSA 泄漏"口径的引擎（如 ESMFold2 单序列 VHH + 仅抗原 MSA），WT 基线内比

## 5. 高频坑速查（详见 playbook）

| 坑 | 规则 |
|---|---|
| 家族谱系误读 | 谁是亲本、哪位是引入突变，必须回原始图表（FIG/Table）定案 |
| 手写叠合 | 一律 Bio.PDB.Superimposer；手写 Kabsch 必须与官方工具对拍后才可用 |
| IgGM 语义 | affinity_maturation 任务=**单点位扫描**（每 batch 1 个 X 枚举），非组合突变；频率谱真实信息集中在少数多样性位点 |
| AnewOmni length_ranges | `random.randint(l, r+1)` 闭区间 off-by-one——锁长写 [7,6] 式 |
| RFD4 annotated CIF | gemmi 转 CIF 必须补 `label_seq_id` + `label_asym_id`（选择器走 asym）；固定链 RMSD 要先叠加（模型自身坐标系） |
| Schrodinger prime_mmgbsa | 必须 `-WAIT` 否则提交即返回、断点误判 FAIL |
| 排序字符串陷阱 | csv 读出按字符串排序漏负号会把降序变升序——排序后必须 head 验收 |
| ANARCII 编号映射 | 线性位↔IMGT 编号有 gap 补偿错位；候选定位用**窗子串直接替换+ANARCII 自证**，禁线性索引法 |

## 6. 产出清单

```text
maturation/
├── dataset/              # 突变体数据集（谱系+实验+计算字段+边界README）
├── hotspot_scan/         # A0/A1(+plus) + 三约束文件 constraints/
├── {b1..b6}/             # 各引擎产出 + 验收 csv + b6_unified 统一池
├── c3_liabilities/       # 序列合规预扫（零GPU前置）
├── {mol_c05,c1,c2}/      # 级联各级幸存名单+读数
├── od_c4/ + mmgbsa/      # 能量双口径 + germinal recheck
├── fusion_rank_final.csv # 三源融合终排名
├── c45_compliance.csv    # 新颖性/合规标记
└── deliverables_*/       # 提交池+fasta+SPR建议+独立终审报告
```
