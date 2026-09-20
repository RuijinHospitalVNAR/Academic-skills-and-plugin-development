# 轨迹分析与伪影排查手册 (Analysis & Pitfalls)

> 48 体系 500-769ns 项目的判据体系与事故复盘浓缩。每条坑都有实证事故编号可溯（见 <MD_PROJECT_DIR>/handoff.md 各节）。

## 1. 分析命令标准链（一次遍历多指标）

```text
parm system.prmtop
trajin md_total.nc 1 last 50         # 采样间隔按体系大小调
strip :WAT,Na+,Cl-,K+                # strip 在 distance 前会使掩码为空 → 先 strip 后算, 或 strip 写出再用 protein_only.prmtop
autoimage                            # 见 §4
rms fit <核心区>@CA out rmsd.dat     # 一次遍历同批输出多指标, 勿多块输入(clear all 会静默清空漏 run 的块)
rms fit <配体>@CA out lig_rmsd.dat
distance COM :<rec> :<lig> out com.dat
nativecontacts ... mindist out nc.dat
atomicfluct out rmsf.dat byres
run
```

## 2. 收敛判据（RMSD 侧，2026-09 定稿口径）

- **掩码=核心区**：排除固有无序尾与纯化 tag。掩码选择错误是最大假阳性源（48 体系 14 个 drafting 中 7 个因掩码含柔性尾被误判；tag RMSF 可达 15Å）。先做 per-residue RMSF 剖面定掩码，再算判据。
- **判据**：末 100ns std < 2.0Å 且 |线性拟合斜率| < 1.0 Å/100ns；末 50ns 作辅助闸（识别"末窗恰好平"的局部平坦陷阱）。
- **半窗一致性**（可选诊断）：末 100ns 两半的 residue-wise RMSF 剖面 Pearson r>0.90。⚠️ 该诊断必须用正式存档脚本（记录 fit 区/残基子集/帧区间），临时脚本结果不可引用（实证：7 种口径无一复现已知 r 值）。
- **边界跳变复核**：轨迹拼接处相邻帧 RMSD 跳变应 <0.5Å；>1Å 先查数据缺陷（时钟误判、段截断、接缝）再谈物理。
- **注意**：全复合物 RMSD 对多链体系不是解离指标（域间铰链翻转可达 30Å 而键合与氢键全稳）；判解离用界面几何量（COM 距 + native contacts + 最小重原子互距 + 界面 SASA 四量互证）。

## 3. 收敛判据（能量侧，2026-09-16 定稿）

- ΔG 报告值：**末 100ns 全窗均值**（100 帧铺满 100ns，比 100 帧挤 20ns 误差 ↓2.2x）。
- ΔG 不确定度：**块平均 SEM**（5×20ns 子块）。理论：真实 SEM = σ√(2τ/T)；实测中位 σ(ΔG)≈18 kcal/mol、τ_int≈4.4ns → 帧间 SEM 低估 4.7x。
- 收敛判据：末两窗（各 100ns）块均值差 < max(10%·|mean|, 1.0) kcal/mol。（5% 阈值会把方法噪声判成未收敛：ΔG~-110 量级时 5%≈5.5 与段间 SD 同量级。）
- **RMSD 收敛 ≠ ΔG 收敛**：实证 34/48 结构收敛中仅 13/48 能量收敛（5% 口径）。双判据必须并列报告。
- 两态振荡体系（ΔG 直方图双峰）：单值不可用，报两态均值±SEM+布居。

## 4. PBC 与成像

- 生产 iwrap=1 时，无 autoimage 的 RMSD 会把跨边界分子算成巨大位移（实证方波 20-60Å 假跳变）。
- 两套 cpptraj 口径（官方流水线 vs 诊断脚本）必须逐行对齐——一条漏 autoimage 就会出现"图对不上"。
- `distance`/`nativecontacts` 默认走最小镜像，与成像无关，适合判解离。
- 改算法必须同时失效**所有层级**缓存（本地/远程/中间 dat/汇总 json）——实证两次事故同源：改了算法，旧缓存"存在即跳过"被复用。

## 5. 批处理与幂等安全（完成判定规则）

**铁律：完成判定只认终结标记（.out 中的 STOP/Final），绝不以文件存在性/大小为准。**

- NetCDF 是边写边增长的：运行中的 md_seg5.nc 会被 glob 误当完整段 → 半成品中间缓存被"存在即跳过"幂等**永久复用**（实证事故：503.15ns 假 unified 数据）。
- .rst 因 ntwr 定期写盘，同样不能当完成信号。
- 幂等跳过加时间戳条件：缓存 mtime ≥ 对应 .out mtime 才可信。
- 时间轴权威口径：读 NetCDF `time` 变量（scipy.io.netcdf_file, mmap=True）。帧数×步长推算在多段续跑体系必错（实证 8 体系被 .out TIME 最大值误判截断 22-29ns）。
- 续跑后必须失效的缓存清单：末段提取 nc、FINAL_RESULTS、per-frame csv、rmsd dat、汇总 json。
- 续跑接缝体检：md_1 末帧 vs md_2 首帧 RMSD/ΔCOM/压力三查；实证接缝不连续特征 = RMSD 跳 6.3Å + ΔCOM +9.4Å + 首步压力 1789bar。**解离事件落在接缝上不可报告物理时刻**。

## 6. 链身份与体系自检

- **链身份必须从序列验证，勿按掩码假设**（实证： receptor/ligand 身份搞反导致整节结论错误——把抗原脯氨酸尾柔性误读成 CDR3 重排）。用 init_dry.pdb 提取序列核对突变位点对位。
- 纯化 tag（His/FLAG/linker）必须从 RMSD/RMSF 与讨论中剔除，并在方法学声明。
- 体系原子数指纹：用配体原子数/残基组成核对体系归属（防跨文件串数据）。

## 7. 统计报告规范

- 排名稳健性：双口径（PB+GB）都靠前才算稳健候选；单口径 Top1 勿当结论（实证：某体系 PB#1 但 GB#12）。
- 相关性报告：先散点看离群点；离群点撑起的 Pearson 假相关要报剔除后 ρ；95%CI 跨 0 时只写"未检测到显著相关"。
- matplotlib 语义坑：errorbar 的 `fmt="o"` + `ls=":"` 时 ls 被静默覆盖 → linestyle 写进 fmt（`"o:"`）。
- 出图全局规范：Arial Bold 8pt、SVG `svg.fonttype=none`（Illustrator 可编辑）已写入用户级 matplotlibrc。
