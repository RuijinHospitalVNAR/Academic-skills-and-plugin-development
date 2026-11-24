# TNFR1 亲和力成熟全流程实例手册（命令级）

> 唯一真相源：`<TNFR1_PROJECT_DIR>/handoff-TNFR1-SDAbs-design.md`（872 行）。本手册为精华浓缩，参数全部实证。
> 母本：DOM1h-131-206（GSK/Domantis EP2746291B1，KD 0.47nM kon 主导）；模板 = od_P2_1206_seed_87239.cif（ipTM 0.964 全局最高）。

## 阶段 0：FR 胚系溯源

- ANARCII VHH 切分：`Anarcii(seq_type="vhh").number([seq])['Sequence 1']['numbering']` → FR1 1-26 / CDR1 27-38 / FR2 39-55 / CDR2 56-65 / FR3 66-104 / CDR3 105-117 / FR4 118-128（IMGT）
- 胚系候选靠家族级特征（hallmark 残基 + blastn vs imgt.org，注意站点可达性）
- **FR 招募位排查（本阶段最重要发现类型）**：若原 VL/疏水残基已被招募进 paratope（三引擎接触实证），FR 替换 = 摧毁界面 → 全 FR 锁死

## 阶段 A：热点扫描（A0→A1→A0+→A1+）

1. **A0 界面重提**（单模板）：paratope（≥2 原子接触口径）+ epitope；vs 多引擎共识 Jaccard 验证模板代表性
2. **A1 丙氨酸扫描**（PyRosetta r387）：WT 笛卡尔约束 relax（RMSD<1.5 自检）→ 逐位 mutate ΔΔG；**阴性对照 |ΔΔG|≤1.5 + ΔΔG-接触数 Spearman 显著 = 扫描自检标配**
3. **A0+/A1+ 多构象版**：61 构象接触频率（4.5/5.0Å 双阈值）+ 3 构象×31 位×5 重复 = 465 任务；**v2 四类分级**（能量敏感-保留 / 波动 / 低敏感 / 硬锁）——单构象过信位被挤出
4. **三约束文件**（make_constraints.py）：
   - `constraints_B1-B3_fixed_allowed.csv`：序列设计族共用（主文库放开位 + 探索文库位）
   - `constraints_B4_antigen_anchor.csv`：RFD4 condition_hotspot 抗原锚点（primary 7 + secondary 5）
   - `constraints_C1_epitope_gate.csv`：core7 + extended12，Jaccard≥0.5 主判 + core 覆盖≥60% 辅判

## 阶段 B：五引擎文库

| 引擎 | 角色 | 关键参数 | 验收要点 |
|---|---|---|---|
| B1 LigandMPNN | 多样性主力 | T 梯队 0.1/0.2/0.3/0.5；`--omit_AA C`；301aa batch 128 | 唯一序列随 T 升；锁位/FR/新Cys 全合规 |
| B2 AntiBMPNN | 家族先验锚 | T0.1/0.2 | 高收敛（家族恢复率 92-98%），多样性靠其他引擎 |
| B3 IgGM | 单点位频率谱 | 每 batch 1 个 X 枚举×300 | 频率谱病态收敛正常；有效信息集中少数多样性位点；与家族实证分歧留给 B6 调和 |
| B4 RFD4-Proteina | 界面微调+冲突变数 | antibody ckpt（HF `nvidia/RFD4-Proteina`）+ annotated CIF（C_CRD/C_SEQ/hotspot）+ inverse_folding 主跑 + tsr_k 双温层 | 固定链叠加 RMSD<0.1Å；突变全在 CDR |
| B5 AnewOmni | （本战役出局） | AntibodyMultipleCDR | 整段 CDR 重生成 vs 位点级约束不兼容；length_ranges off-by-one |

- **B6 统一池**（b6_merge_pool.py）：统一 IMGT → 去重 → new_cys 剔除 → 位点级共识标记 → 排序键（引擎共识数→家族命中→突变数接近目标带→总数）
- 共识示例：30A→S 四引擎一致（最强）；102R→K 双引擎一致且家族实证恰是 K

## 阶段 C：级联漏斗

```text
C3 liabilities（零GPU前置：NG/NS、DG/DS、M/W氧化、游离Cys、NXS/T糖基化、pI漂移）
  → C0 WT基线（20 seeds 重跑：ipTM/ipSAE mean±σ；协议可复现验证）
  → C0.5 全池 5s×1 双轴 triage（分位定线：双轴≥WT 直升 + bottom20% 弃置）
  → C1 幸存者 25-100s 精筛（姿态收敛 wilson_lb≥0.5 + 表位 Jaccard gate）
  → C2 top1000 OD 25s×1 正交（免MSA免模板；confirm_frac 注记级）
  → C4 能量（Germinal relax 主轴 + MMGBSA top200）
  → C4.5 ANARCII 合规（vs 专利+家族+母本库 identity；标记不剔除）
  → C5 独立口径终检（ESMFold2：VHH 单序列+仅抗原 MSA；≥WT 过线）
  → 融合排名（0.5·能量秩 + 0.25·表位收敛秩 + 0.25·正交秩；DIVERGENT→EXCLUDE）
```

要点：
- WT σ 极窄（<0.001）时 mean-2σ 线近乎"不低于 WT"→ 幸存率<5% 则改**池内分位定线**（跑与定线解耦）
- Mol-1 拿全 PAE：`--need_atom_confidence true`（+39% 耗时）；ipsae.py 键名适配器
- C1 近饱和（PASS 1341/1343）= C0.5 先验池质量验证，**排序判据留给 C2/C4**（gate 与排序分层）
- 远端批量：MSA 同路径挂载根治静默在线检索；watchdog 只杀自家容器名（多项目共存）
- 判完成用**逐 job cif 计数**（docker 自动建空目录会让目录计数虚高）；E1 矩阵对账（SKILL 执行期防线）

## 阶段 D：交付

- 提交池 = 终检过线 ∩ 融合排名，ipSAE 降序；全读数注记（突变/区/融合分/双ΔG/epi_jac/wilson_lb/odcf/germinal/C5）
- **共识突变收敛分析**（多引擎独立收敛位 = 亲和主驱动推断 → SPR 单点/双点建议序）
- 资格裁决用**同进程 CDR 窗序列 join 逐位 diff**（zip≈join 需同骨架；线性位↔IMGT 有 gap 错位）
- 位点升级（差一步达标候选 +1 共识位）：**窗子串直接替换 + ANARCII 窗 diff 自证**，禁线性索引
- **独立终审**：不读中间 csv，从原始 fasta/json/库全量重算 7 维

## 工程执行体系（六机并行战役沉淀）

- 沙箱收割对策：长任务 **setsid** 或阻塞式 run_in_background（nohup 延迟收割实证 4 次）
- keepalive（crontab 每 2min 拉活）+ 远端 watchdog（只杀自家容器名防误杀共存项目）
- 回传：relay 慢则远端 tar + 手动拉；收包必须 stat 字节数 + gzip -t（半截残留曾误判）
- 多项目共存：独立命名空间 + 自家容器名前缀 + watchdog 过滤器；GLP1R 混入教训
- 远端 pkill pattern 不得与当前 ssh 命令行文本重合（会话自杀）
