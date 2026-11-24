# Germinal relax 能量协议（能量主口径）

> 溯源定案（2026-11-23 用户确认"这是我们原本要用的"）：protein_filter_lib part2 → VSIG4 → MC4R energy_supp_5 → TNFR1 C4 全量 1001 复刻。
> **能量主轴 = Germinal FastRelax 后的 interface dG**；pack-only dG **已废弃**（不符合 Rosetta 正确使用方法）。

## 1. 为什么 pack-only 废弃（实证 + 方法论）

- pack vs relax 排名 **Spearman ρ=0.007**（n=1000, p=0.84），top20 交集 **0/20**
- relax 增益倒挂：pack 头部候选 -10.9 vs 尾部 -25.8 → pack 排名被**预测侧链随机性**主导
- 方法论：Rosetta 能量评估**必须在弛豫后的结构上做**——未弛豫结构的侧链/堆积冲突未被消除，其 dG 无物理意义；pack-only 读数仅可作 relax 前基线中间量（dG_pre，供 delta_dG 与 flag 判读），**禁止作为独立能量口径输出、报告或排名**

## 2. 运行时（勿混用）

- conda env `amber22_py310` + PyRosetta **r387**（PYTHONPATH 指向 `<PYROSETTA_R387_SETUP>`）
- ❌ 旧 PyRosetta env（py3.6）无 numpy、非 Germinal 历史运行时
- 本地长任务必须 **setsid** 拉起（nohup 后台会被会话清理——TNFR1 曾 24/51 干净截断无报错）

## 3. 协议参数（照抄勿改）

```text
init flags  = -mute all -use_input_sc -ignore_unrecognized_res -ignore_zero_occupancy false
              -load_PDB_components false -relax:default_repeats 2 -no_fconfig -ex1 -ex1aro
FastRelax   = max_iter 200 + constrain_relax_to_start_coords(True)
              + min_type lbfgs_armijo_nonmonotone
              + MoveMap(bb=True, chi=True, jump=False)   # jump=False 锁链间刚性
              + scorefxn ref2015（默认 get_score_function）
IAM         = InterfaceAnalyzerMover('A_B') + pack_input(True) + pack_separated(True)
              + set_calc_dSASA(True)   # part2 原版有，必须显式
              → relax 前后各测一次（dG_pre / dG_post 同口径可对账）
```

对照输出列（recheck csv）：`dG_pre/dG_post/delta_dG、dSASA_pre/post、接触原子对(跨链重原子≤4.5Å)、B 链接触残基数、epi_jac(前后表位 Jaccard)、rmsd_relax(全 CA)`

## 4. 判读 flag（注记级，非 gate）

| flag | 条件 | 含义 |
|---|---|---|
| INTERFACE_LOST | 接触原子掉 >70% 或 dSASA 掉 >70% | VSIG4 LAG3/SPN 式**假界面**（relax 后界面消失） |
| DESTABILIZED | delta_dG > +10 REU | relax 显著劣化 |
| STABLE | 其余 | 通过 |

- **WT 锚对照**必带（真界面 relax 后应稳定）；候选 dG_post 优于 WT 锚 = 亲和改善信号（TNFR1: 352/1000 优于 WT -47.99）
- rmsd_relax 偏大（4-14Å）可为 ECD 柔性区全局位移，接触/表位稳定即可判 STABLE

## 5. 重复性检验与能量主读数（⚠️ 2026-11-24 终版口径）

- **能量主读数 = 4 观测均值**（mean4）：原 recheck dG_post（默认起点）+ 3 个扰动起点 rep；无 reps 段的候选用单次值并标 `NO_REP`
- **独立起点实现 = PDB 文本层坐标扰动**：numpy 对 ATOM 记录 x/y/z 列加 N(0, 0.03Å) 噪声写临时 pdb（每 rep 一个扰动 seed）
  ⚠️ **勿用 `-run:seed`/`-run:jseed`**——r387 均为非法 option（worker 连环崩 + 69 万行 traceback）；numeric.random 无全局 RG 绑定、Atom 无 set_xyz 也全排除——文本层扰动是唯一零 API 依赖可控方案
- **方差判读（std4，4 观测）**：std > 2 REU = HIGH_VAR **降置信且参与分层**（tierA 条件 = germ < WT 锚 ∧ var-OK(std≤2) ∧ od_jac≥0.5）
- 实证依据（TNFR1 top300）：std p50 1.63 / p90 3.11 / max 5.26 REU；**HIGH_VAR 105/300（35%）**——单次 relax 排名 1/3 候选不可靠，均值+方差是必须项
- 工程注记：扰动起点 relax 收敛快 ~3×（短路径，max_iter 不跑满）；WT 锚双 seed 冒烟验证锚低方差再放量

## 6. 与 MM/GBSA 的关系

- MM/GBSA（Schrodinger prime_mmgbsa，relaxed 帧口径）= **观察位/同向性检查，非硬 gate**
- 三口径互异不可直比（TNFR1 WT：pack -33.13 / Germinal -47.99 / A1 cart -53.05）

## 7. 坑全录（7 条，全部实踩）

1. 运行时必须 r387+py3.10（见 §2）
2. r387 C++ 包装对象**不可动态加属性**——`ia.xx=` 赋值即 AttributeError，报错串误导到"方法名缺失"→ 用返回元组
3. `set_calc_dSASA(True)` 必须显式
4. 链身份走 `pose.pdb_info().chain(i)`（`residue.chain()` 返回 pose 内部 int ID 非字母）
5. 氢原子判定用 `residue.atom_is_hydrogen()`（Atom 无 `element()`）
6. setsid（见 §2）
7. 冒烟纪律：目标运行时 + 同并行模式 + 单任务全流程通过才放量；**增量落盘 + 断点跳过**（每结果即时 flush + csv 去重）防死跑白跑

## 8. 参考实现

- 权威：`<GERMINAL_LIB_DIR>/scripts/part2/part2_run_pyrosetta_static_relax_interface.py`
- 复刻（recheck + reps）：`<TNFR1_PROJECT_DIR>/scripts/c4_germinal_recheck.py`、`c4_germinal_reps.py`（增量追加模式 + 3 seed 方差）
