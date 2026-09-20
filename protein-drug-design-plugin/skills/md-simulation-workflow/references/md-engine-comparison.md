# MD 引擎对比与选型 (MD Engine Comparison)

> 调研日期 2026-09。结论优先服务于本插件工作流：**默认 AMBER，按场景替换**。
> 版本敏感项（性能数字、许可证细节）使用前以官方文档为准。

## 1. 五引擎速查表

| 引擎 | 许可证 | GPU 支持 | Python API | 最适场景 | 不适场景 |
|---|---|---|---|---|---|
| **AMBER** (pmemd) | AmberTools 免费 (GPL)，pmemd 引擎付费 (~$500/学术) | **最强** (pmemd.cuda, 单卡多卡均可) | PyAMBER/parmed 生态 | 蛋白-配体、QM/MM、CpHMD、长时程 GPU 生产 | 零预算团队（引擎收费） |
| **GROMACS** | 免费 (LGPL 2.1)，商用亦免费 | 很好 (CUDA/OpenCL/SYCL/HIP) | gmxapi | 蛋白/蛋白-配体通用、自由能计算、教学与脚本化 | 需 QM/MM 深度生态、CpHMD 高级用法 |
| **NAMD** | 学术免费（非开源许可） | 好，**超大体系多机扩展性强** (100M 原子级) | 无原生 (Tcl 脚本) | 膜蛋白 + CHARMM-GUI 流程、超大体系多节点 | Python 工作流、小体系快速迭代 |
| **CHARMM** (程序) | 学术付费/部分免费 | 好 | 无 | CHARMM 力场发源地的原生功能（过于小众时用 NAMD 替代） | 通用学术用户 |
| **OpenMM** | 免费开源 (MIT/LGPL) | 好 (CUDA/OpenCL) | **Python 即主接口** | 定制力场、ML 力场 (ANI/MACE via openmm-ml)、增强采样方法开发 | 开箱即用的命令行流水线 |

补充：LAMMPS（材料/粗粒化向）、ACEMD/folding@home 系（NVT+Langevin 生产协议的发源地之一，本插件 48 体系协议参考）。

## 2. 力场兼容性

| 力场族 | AMBER | GROMACS | NAMD | 备注 |
|---|---|---|---|---|
| ff14SB/ff19SB (AMBER 族) | 原生 | 经转换 (acpype/amb2gmx) 或内置 ambersb | 经转换 | ff19SB 配 OPC 水；ff14SB 配 TIP3P |
| CHARMM36/36m | 有限 | 原生支持 | **原生** | C36m 是膜蛋白主流；CHARMM-GUI 产出直接喂 NAMD/GROMACS |
| CGenFF (配体) | 经转换 | 原生 (cgenff_charmm2gmx) | 原生 | 与 GAFF/AM1-BCC 二选一，勿混用 |
| GAFF/GAFF2 (配体) | **原生** (antechamber) | 经转换 (acpype) | 经转换 | AMBER 配体参数化的黄金标准链 |
| OPLS-AA / GROMOS | 有限 | 原生 | 有限 | — |

**规则**：同一模拟中蛋白与配体力场必须同族配套（ff19SB+gaff2+OPC，或 CHARMM36m+CGenFF+TIP3P），混用需在论文中声明误差。

## 3. 性能要点（2026 官方口径）

- **AMBER pmemd.cuda**：单卡 GPU 性能业界标杆；NVIDIA 官方 HPC 榜单 AMBER 24 GB200 多卡扩展比 ~30-80x/2卡（JAC 体系）；CpHMD GB 体系单卡实测 200-400 ns/day（A9 项目，3090 级）。
- **GROMACS**：CPU 端最快的免费引擎；GPU 需源码编译 `-DGMX_GPU=CUDA`；性能清单（官方 mdrun-performance）：菱形十二面体盒子、constraints=h-bonds、4fs 氢质量重分配、`gmx tune_pme` 调 PME rank。
- **NAMD**：多节点扩展性历史最强（100M 原子级）；NVIDIA NGC 提供 hpc 容器。
- **选型经验法则**：单/双卡跑 100-1000ns 蛋白体系 → AMBER 与 GROMACS 都够用，差距 <2x；**跨卡/跨节点** 或 **百 ns×几十体系的批量** → pmemd.cuda 单卡吞吐优先；**QM/MM / CpHMD** → AMBER 生态最完整（本插件实证路线）。

## 4. 决策树

```text
需要 QM/MM / CpHMD / RESP / 高级自由能?
├─ 是 → AMBER (本插件默认; AmberTools 免费部分+引擎许可)
└─ 否 →
   已有 AMBER 许可证或实验室传统?
   ├─ 是 → AMBER (延续项目一致性)
   └─ 否 →
      膜蛋白 / CHARMM-GUI 流程 / 超大体系?
      ├─ 是 → NAMD (配 VMD 可视化)
      ├─ 需 Python 定制 / ML 力场 / 增强采样开发? → OpenMM
      └─ 其余 (通用蛋白 MD、零预算、社区支持优先) → GROMACS
```

## 5. 跨引擎迁移注意事项

1. **力场不可直接对拷**：ff19SB↔CHARMM36m 数值不同（CMAP、电荷衍生方式），跨引擎结果比较必须同力场同转换工具，并验证能量分解项量级一致。
2. **水模型/离子参数配套**：OPC ↔ TIP3P/OPC 与各自离子参数（ionsjc_tip3p vs SPC/E ion）绑定，转换脚本 (acpype/parmed) 只转拓扑不换物理。
3. **收敛判据引擎无关**：本插件 analysis-and-pitfalls.md 的收敛判据（核心区 RMSD 双条件 + 块平均 SEM + 10% ΔG 阈值）基于统计学，跨引擎通用；但阈值内的绝对 ΔG 数值**不可跨引擎/跨力场混排**。
4. **PBC/成像伪影跨引擎同源**：GROMACS 的 `-pbc whole/mol`、cpptraj `autoimage`、NAMD 的 wrapAll 都是同族问题——分析前统一成像。

## 6. 本机实证资产索引

| 资产 | 路径 | 状态 |
|---|---|---|
| Amber22 (sander/pmemd.cuda/cpptraj/MMPBSA.py) | <AMBER_HOME> | ✅ 已验证 |
| AmberTools23 env (远程 rcdb) | <REMOTE_HOME>/anaconda3/envs/AmberTools23/bin/python | ✅ 已验证 |
| 远端 8×3090 (GPU0 被占, GPU5 MD 专用勿占) | user@<REMOTE_HOST>:<REMOTE_PORT> (内网地址脱敏, 见本地 handoff) | ⚠️ 共享资源，先巡检 |
| gmx 任务参照（他人项目, GLP1R） | /data/hst/GLP1R-* | 只读参考 |
| OpenMM 技能 | superpowers:molecular-dynamics | 备选引擎文档 |
