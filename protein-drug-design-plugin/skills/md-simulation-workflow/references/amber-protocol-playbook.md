# AMBER 协议手册 (S1→S8 全流程)

> 实证来源：A9-尿酸酶项目（C0 系列 4 体系、NSU 参数化、QM/MM、CpHMD，2026-09）+ SH3/HCG 48 体系 500-769ns（2026-09）。所有命令均在本机/远端跑通过；`⚠️` 标记项需按项目再核对。
> mdin 模板：本目录 `templates/`（01_min.in … 04_prod_nvt.in / 04_prod_npt.in）。

## S1. 结构准备

1. **来源**：实验结构 (PDB) 优先；AI 预测结构（AF3 等）可直接用作 MD 起点（本项目 48 体系全部从 AF3 结构起步，500ns 后体系稳定）。
2. **清理**：删全部氢 + OXT（tleap 重建）；`⚠️` 检查 PDB 中段是否有多余 `TER`/`END`（tleap 会静默截断，见 S3 守卫）。
3. **质子化态**：先 PROPKA 多帧系综估计关键残基 pKa（配体剥离、只测构象贡献）；显式指定 HID/HIE/HIP（tleap 默认 HIE）。A9 实证：阴离子配体结合使 H256 pKa 上移 ~2 单位，结合态起点应用 HIP。
4. **缺失环**：短缺口由 tleap 封端补全；长缺口回结构预测技能补模。

## S2. 配体参数化

### 路线 A：AM1-BCC（默认，快）
```bash
antechamber -i lig.mol2 -fi mol2 -o lig_gaff2.mol2 -fo mol2 \
  -c bcc -nc 0 -at gaff2 -rn LIG
parmchk2 -i lig_gaff2.mol2 -f mol2 -o lig.frcmod   # 必须检查 ATTN=0
```
- **mol2 价态坑**：OpenBabel 生成的芳香环键 `ar` + 环内 C=O 会触发 "Weird atomic valence" Fatal——问题在键级表示；改写显式 Kekulé 键级（环键 1/2，原子类型 C.2/N.am/N.2/O.2）。验证：antechamber 前用 OpenBabel 输出 SMILES 与参考比对。
- 产物：mol2 + frcmod + （用于 tleap 的）.lib 或直接 loadmol2。

### 路线 B：RESP（高精度，发表级）
官方分步链（⚠️ Amber22 `antechamber -c rc` 直连不可用——"Cannot open file ()" 死锁 3 次复现，必须分步）：
```text
g16 (HF/6-31G* SCF=tight Pop=MK iop(6/33=2) opt) → espgen (gout→esp)
→ antechamber -at gaff2 (先分配类型, 不带电荷) → respgen (resp1/resp2)
→ resp 两阶段拟合 → 电荷注入 .ac (正则定位 ATOM 行电荷 token 替换)
→ parmchk2 (0 ATTN) → tleap
```
实证锚点：ESP 相对 RMS ≤0.11、偶极合理、电荷和=净电荷 ±0.001。`-a qout -ao crg` 合并会静默失败（电荷全 0），必须手动验证。

### 配体放置（产物性几何）
- 与既有位姿叠合放置：Kabsch 全旋转枚举映射（NSU 案例 12 映射枚举 → RMSD 0.064 Å）。
- **放置后冲突预检**：蛋白重原子最近接触 ≥2.7Å（正常 vdW）；<2.0Å 需 min 解决或重新放置。
- ⚠️ **催化/攻击几何需构造而非照搬 MD 帧**：平衡帧配体常不在攻击几何（A9 实证 OG-C2 4.15Å vs 特选起点 3.39Å）；理想几何参数扫描（d × Bürgi-Dunitz 角 × 二面角）后取最优 pose，并核对催化三要素（攻击几何 / 氧阴离子洞 / 广义酸碱）。

## S3. tleap 体系构建 + 三道守卫

```bash
# 用 bin/tleap wrapper（裸 teLeap 无 -I 搜索路径）
$AMBERHOME/bin/tleap -f leap.in
```
leap.in 关键行（模板见 templates/）：
```text
source leaprc.protein.ff19SB
source leaprc.water.opc
source leaprc.gaff2
loadamberparams lig.frcmod
LIG = loadmol2 lig_gaff2.mol2
sys = loadpdb system.pdb
solvateoct sys OPCBOX 10.0
addIonsRand sys Na+ 0        # 中和; 0.15M 盐: addIonsRand sys Na+ n Cl- n
saveamberparm sys system.prmtop system.inpcrd
```

**坑与守卫（构建后三道检查，全过才允许开 MD）**：
1. **Errors=0**：tleap log 无 Fatal/Error（"charge -10" 类提示是蛋白净电荷，非错误）。
2. **配体/关键残基掩码命中**：`cpptraj -p system.prmtop` 或 parmed 验证 `:LIG`、`:256@NE2` 等掩码命中数正确（防 mid-file END 静默丢配体）。
3. **原子数/残基组成核对**：prmtop 原子数与预期一致（配体原子数可作体系指纹：中性 UA 16 原子 vs 尿酸阴离子 15 原子的实证先例）。

离子参数：**必须 `loadamberparams frcmod.ionsjc_tip3p`**（ions234lm_126_tip3p 无 "Na+" 类型 vdW → tleap Fatal），且与所选水模型配套。

## S4. 升温与平衡（链式）

| 步骤 | 模板 | 要点 |
|---|---|---|
| min 1 (全原子) | 01_min.in | maxcyc 5000; CPU sander（⚠️ pmemd.cuda 对部分体系最小化病态：BOND 项爆涨+冻结+REPEATED LINMIN FAILURE，最小化用 CPU） |
| heat 400ps | 02_heat.in | 0→300K, ntr=1 骨架限制 2.0, **必须 `-ref min.rst7`**（否则 Error on OPEN: refc）；产物性放置体系对配体同加限制 |
| equil NPT 800ps | 03_equil_npt.in | ntp=1 taup=2.0 定密度；盒子膨胀失败（体积 +5000%）= 重建失败信号，弃用该段改重建 |

## S5. 生产模拟

- **系综**：NPT（通用）或 NVT（重建盒不稳定时；1ns NPT 定密度后 NVT+Langevin γ=2.0 生产是成熟实践，对结构/动力学量无影响，论文须声明）。
- **性能基线**（3090 级单卡）：~3 万原子体系 100-200 ns/day。
- **环境规则**：pmemd.cuda 必须沙箱外运行（沙箱后台执行会静默回退 CPU：3700% CPU + nvidia-smi 无进程 + 数小时无产出）；用 `nohup ... & echo $!` 前台快返回拉起，**30s 后 `nvidia-smi --query-compute-apps=pid,used_memory` 验证真上卡**。
- **GPU 绑定**：`CUDA_VISIBLE_DEVICES=GPU-<完整UUID>`（短前缀报 no CUDA device）；用卡前 `nvidia-smi -L` 自检 UUID 存在。
- **长时程/批量**：100ns/段 × N 段链式 restart（`irest=1, ntx=5`）；跨机迁移续跑以 NetCDF 时间戳取证无重复计算；段间时钟首尾衔接（如 101.20→101.21）。

## S6. 轨迹分析（cpptraj 官方工具优先）

```text
parm system.prmtop
trajin md_prod.nc 1 last 10          # ⚠️ 时间轴以 NetCDF time 变量为准
strip :WAT,Na+,Cl-,K+
autoimage                            # PBC 硬前提: iwrap=1 轨迹不做成像→RMSD 假方波(20-60Å)
rms fit :1-183@CA out rmsd.dat       # 掩码=核心区(排除IDR/tag), 参考=延伸起点
atomicfluct out rmsf.dat byres       # RMSF: rf(受体叠合,看全局) + lf(配体自叠合,看内部柔性)
distance d1 :110@OG :291@C out dist.dat
nativecontacts :1-105&!@H= :106-211&!@H= distance 4.5 mindist contact
hbond :LIG out hbond.dat avgout hb_avg.dat
run
```
官方工具优先原则实例：RC 汇总曾试 `process_minout.perl`——对本 QM/MM 输出不可用（正则失配+hash 冲突+不读 rst），才退回手写 summarize（并与官方语义逐项比对）。手写解析 bug 高发区：RESTRAINT 取锚定块（FINAL RESULTS）非文件首个匹配；EAMBER 缺失时用组分和回退（7 位有效数字，勿用 4 位 ENERGY）。

## S7. 结合能 MM/GBSA(PBSA)

```bash
MMPBSA.py -O -i mmpbsa.in -o FINAL.dat -sp system.prmtop \
  -cp complex.prmtop -rp receptor.prmtop -lp ligand.prmtop \
  -y md_last20ns_nowat.nc        # 去水复合物轨迹(4529原子) 配 complex.prmtop, 勿配 system.prmtop
```
- 口径：GB 用 `igb=5, saltcon=0.154`；PB 用 `ipb=2, inp=2,indi=1,exdi=80, radiopt=1, cavity_surften=0.0378, cavity_offset=-0.5692`（Amber22 sander 不认 gmx_MMPBSA 专属参数 smoothopt/iprob）。
- 采样：末 20ns×100 帧（快速判据）或**末 100ns 全窗**（报告口径，误差 ↓√5）。
- 统计：**块平均 SEM**（5×20ns 子块）。帧间 SEM 低估 ~4.7x（τ_int≈4.4ns 实证）；ΔG 逐帧 σ≈18 kcal/mol 时 20ns 窗真实 SEM≈12。
- 残基分解：`idecomp=1` + `print_res`（⚠️ 不能带冒号前缀；ff19SB 下 Amber22 decomp 组装层有 "Mismatch" bug，sander 逐帧 mdout 数据完整，自解析 TDC 块即可；**decomp 的 sas 列是 SASA(Å²) 不是能量，须乘 surften=0.0072**）。
- PB vs GB：绝对值差 50-120 kcal/mol 属正常口径差（PB 空腔惩罚更强），**只有排名对比有效**；两者都靠前的候选才是稳健结论。

## S8. 深化模块

### 8.1 PROPKA pKa（静态）
多帧系综（apo/bound 各 ≥5 帧）+ 配体剥离；输出 pKa ± SD。锚定对照：中性配体不升反降、阴离子 +2.2 是盐桥姿态特有（A9 实证：apo 5.53 / 阴离子结合 7.72）。CLI 装在 anaconda3/bin；不接受 `*.pdb.1` 扩展名。

### 8.2 CpHMD（动态 pKa）
- 固定 pH 多点（可行，GPU）：pH 5.0-8.5 × 5ns/点，apo/bound 各一卡串行；ntcnstph=50, ntrelax=50（Amber 默认 200 的 GB relax 开销巨大）。
- **pH-REX 三禁**：① pmemd.cuda 不能做（SPFP 单精度 GB 能量噪声淹没 Metropolis，接受率<0.1%；CPU 对照正常）；② `-rem 3` 交换的是 pH 标签非坐标，mdout REPNUM 恒定是正常现象，看 EXCHANGE# 计数；③ 副本数必须偶数，`mpirun -np 12 pmemd.cuda.MPI -ng 12`。
- 分析：**官方 cphstats 优先**（--population --cumulative）。手写解析两大实证 bug：state 语义反（state0=HIP 带质子数 2）、帧数漏计（cpout 'Time:' 行远少于真实帧数）。
- 局限：非标准可滴定配体（UA 等）需自定义 titratable，另立项目。

### 8.3 QM/MM（反应机制）
- 体系规模：GB 隐式 ~3000 原子可行（显式 3 万原子体系 sander QM/MM 串行 5-10s/步不可行）。
- **SCF 收敛根因律**：未松弛结构必病态（1000 迭代不收敛）。排除 DIIS/vshift/chg_lambda（chg_lambda 有效但改变物理——同坐标能量差 36 kcal/mol，弃用）后，**根因=结构未弛豫**；MM min 5000 步后 chg_lambda=1.0 + scfconv=1e-5 + dftb_maxiter=500 → 0 失败。
- QM 区电荷核算：各区片段电荷和 ≈ qmcharge（A9 实证 -1.043 → qmcharge=-1）。
- RC 弛豫扫描：maxcyc=4000（1500 不充分会高估势垒）、链式 rst 传递、窗口靶心达标用 RESTRAINT 列诊断（rk=50 推不动短程区，需 rk=200-500）；DISANG 正确格式= mdin 末尾独立行（非任何 namelist 内、非环境变量），验证法 strace 见打开文件 + RESTRAINT=rk×(d-d0)² 精确吻合。
- 判据：ΔG‡<15 kcal/mol 可行 / 15-25 吃力 / >25 否定；**酶只降 ΔG‡ 不改 ΔG_r**——热力学否定用小分子 DFT/xtb 即可，勿浪费 QM/MM。
- 小分子热力学链：GFN2-xTB/ALPB 快筛（注意硝基/亚硝基弱项，偏差可达 +45 kcal/mol）→ Jaguar B3LYP-D3/6-311G**+PBF 复核（全部 opt+freq 0 虚频）；**必须实验锚定校正**（H2/HCOO 氧化 E0' 标定；实测 DFT 在甲酸氧化上系统偏差 -20.8 kcal/mol）；方法学自验证：已知可行途径应给出近零/放能结果（A9 案例羟化步 +3.9 ✓）。

### 8.4 长时程收敛与批量管理（48 体系经验）
- 延伸协议：从原轨迹末帧抽 dry 复合物 → tleap 重建溶剂化（padding 10Å）→ 1ns NPT 平衡 → NVT 段续跑；重建后起点与原末帧 RMSD 差 0.3Å 内=物理连续。
- 收敛双判据 + 块平均：见 analysis-and-pitfalls.md §2-3。
- 幂等批处理的安全闸：见 analysis-and-pitfalls.md §5。
