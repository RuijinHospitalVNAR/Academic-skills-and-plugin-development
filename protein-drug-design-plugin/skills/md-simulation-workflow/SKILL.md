---
name: md-simulation-workflow
description: 蛋白质/复合物分子动力学模拟全流程技能（AMBER 主力）。Use when 用户要做蛋白-配体或蛋白-蛋白体系的 MD 模拟：结构准备与质子化、配体力场参数化（antechamber/RESP）、tleap 体系构建、min→heat→equil→production 升温平衡、GPU 生产模拟、cpptraj 轨迹分析、MM/GBSA(PBSA) 结合能计算、收敛性判定，或要选择 MD 引擎（AMBER/GROMACS/NAMD/CHARMM/OpenMM）、诊断 MD 崩溃与伪影（PBC 成像、续跑接缝、缓存 STALE）、规划 500ns+ 延伸与 CpHMD/QM/MM 深化。关键词：MD、分子动力学、AMBER、tleap、prmtop、pmemd.cuda、cpptraj、MMGBSA、MMPBSA、RMSD 收敛、力场 ff19SB/gaff2。
---

# MD 模拟工作流 (Molecular Dynamics Simulation Workflow)

固化自两个实证项目：A9-尿酸酶体系（4 体系 100ns + QM/MM + CpHMD，2026-09）与 SH3/HCG 48 体系 500-769ns 延伸与收敛分析（2026-09）。所有协议参数均有实证记录，标注 ⚠️ 的项使用前需核对本机环境。

## 0. 何时使用 / 不使用

**使用**：蛋白-配体、蛋白-蛋白复合物的动力学稳定性验证；预测结构（AF3 等）的动力学可用性评估；结合自由能定量（MM/GBSA/PBSA）；pKa/质子化（PROPKA/CpHMD）；反应机制（QM/MM）。

**不使用**（转交其他技能）：结构预测本身 → `structure-prediction-analysis`；序列/家族鉴定 → `seq-struct-analysis`；对接初筛（Glide/AutoDock）→ 走对应工具，MD 用于对接后精修。

## 1. 引擎选型（30 秒决策）

本技能默认 **AMBER**（pmemd.cuda GPU 性能最佳、ff19SB/OPC 现代力场、QM/MM+CpHMD 生态完整，本机 <AMBER_HOME> 已验证）。其他场景查 [references/md-engine-comparison.md](references/md-engine-comparison.md)：

- 无 AMBER 许可证 / 免费优先 → GROMACS
- 膜蛋白大体系 + CHARMM-GUI 流程 → NAMD
- Python 定制/ML 力场 → OpenMM（另有 superpowers:molecular-dynamics 技能）

## 2. 标准流程（五阶段）

```text
S1 结构准备 → S2 配体参数化 → S3 tleap 体系构建 → S4 升温平衡 → S5 生产模拟 → S6 分析与收敛判定
   (质子化/缺失处理)   (BCC 或 RESP)      (溶剂化/离子+三道守卫)   (min→heat→NPT)   (NVT/NPT GPU)    (cpptraj + MM/GBSA)
```

每阶段的命令、参数与守卫规则见 [references/amber-protocol-playbook.md](references/amber-protocol-playbook.md)（含 templates/ 下的标准 mdin 模板）。

关键协议基线（实证默认值）：

| 项 | 默认值 | 出处 |
|---|---|---|
| 蛋白力场 | ff19SB（新项目）/ ff14SB（延续旧项目） | A9 C0 系列 / 48 体系 |
| 水模型 | OPC（配 ff19SB）/ TIP3P（配 ff14SB） | 同上 |
| 配体力场 | gaff2 + AM1-BCC 电荷；高精度需求用 RESP（HF/6-31G*） | NSU 参数化全流程 |
| 溶剂化 | solvateOct 10 Å，addIonsRand 中和（0.15M 盐按需） | C0 系列 |
| 平衡链 | min 5000 → heat 400ps（骨架限制 2.0）→ NPT 800ps | 同上 |
| 生产 | dt=2fs（SHAKE），300K，ntwx 适配分析需求 | 同上 |
| 系综选择 | 密度确定后 NVT 生产可避免 barostat 伪影（论文口径须声明） | 48 体系第六节 |

## 3. 分析与收敛判定（实证判据体系）

详见 [references/analysis-and-pitfalls.md](references/analysis-and-pitfalls.md)。速查：

- **RMSD 判据**：核心区掩码（排除固有无序尾/纯化 tag）末 100ns std<2.0Å 且 |slope|<1.0Å/100ns
- **能量判据**：末两段 ΔG 差 < max(10%·|mean|, 1.0) kcal/mol；不确定度报块平均 SEM（帧间 SEM 低估 ~4.7x）
- **ΔG 报告口径**：末 100ns 全窗均值（非 20ns 窗），误差 ↓√5
- **PBC 硬前提**：cpptraj 分析前必须 autoimage（iwrap=1 轨迹不做成像 → RMSD 假方波）
- **时间轴权威口径**：读 NetCDF time 变量，勿用 帧数×步长 推算（续跑体系必错）

## 4. 深化模块（按需进入）

| 模块 | 触发 | 要点（详见 playbook §8） |
|---|---|---|
| PROPKA pKa | 质子化态不确定 | 多帧系综 + 配体剥离；阴离子结合可致 ΔpKa≈+2（A9 实证） |
| CpHMD | 需动态 pKa | 固定 pH 多点 GPU 可行（~200 ns/day）；**pH-REX 勿用 pmemd.cuda**（SPFP 单精度能量噪声淹没 Metropolis 判据，接受率<0.1%）；ntcnstph/ntrelax=50 |
| QM/MM | 反应机制 | GB 隐式 2876 原子级体系可行；结构必须先 MM 充分弛豫（否则 SCF 不收敛）；DFTB3 起步 |
| 小分子热力学 | 产物路线判别 | xtb 快筛 + DFT(Jaguar B3LYP-D3/PBF) 复核；**必须做实验锚定校正**（甲酸氧化 DFT 偏差 -20.8 kcal/mol 实证） |

## 5. 高频坑速查（每条都真踩过）

| 坑 | 规则 |
|---|---|
| tleap 静默丢配体 | PDB 中段出现 TER+END → tleap 读到 mid-file END 停止，无警告。**构建后必须验证配体掩码命中**（三道守卫之一） |
| 离子参数 | 必须用 `frcmod.ionsjc_tip3p`（ions234lm 无 Na+ vdW → tleap Fatal）；用 `bin/tleap` wrapper（裸 teLeap 无搜索路径） |
| mol2 价态 | OpenBabel 芳香键 `ar` + 环内 C=O → antechamber "Weird valence" Fatal；改写显式 Kekulé 键级 |
| pmemd.cuda 环境 | 必须沙箱外运行（CUDA init 被拦）；GPU UUID 需完整 `GPU-` 前缀格式；启动 30s 后 `nvidia-smi --query-compute-apps` 验证真上卡 |
| "产物存在即跳过" | 上游仍在写入或算法已改时会静默污染（半成品 NetCDF 边写边增长）；完成判定只认 .out 的 STOP/Final 终结标记 |
| 续跑接缝 | md_1/md_2 拆分体系接缝处可有不连续（实证 6.3Å 跳变+1789bar）；解离事件落在接缝上不可报告 |
| 配体被排出口袋 | 产物性放置的体系，min/heat/equil 阶段必须对配体加位置约束（ntr=1 + -ref），否则生产第 1 帧即飞出 |
| heat 的 ntr=1 | 必须给 `-ref min.rst`，否则 "Error on OPEN: refc" |

## 6. 产出清单（一个完整 MD 项目的交付物）

```text
<project>/
├── build/          system.prmtop + system.inpcrd + tleap log (Errors=0) + 守卫检查记录
├── md/             min/heat/equil/prod 的 .in/.out/.rst/.nc + GPU 绑定记录
├── analysis/       rmsd/rmsf/contacts/hbond .dat (cpptraj 官方产物) + 收敛判定表
├── energy/         MMGBSA FINAL_RESULTS + 块平均统计
└── handoff.md      独立交接记录（每项目一份，不混写）
```
