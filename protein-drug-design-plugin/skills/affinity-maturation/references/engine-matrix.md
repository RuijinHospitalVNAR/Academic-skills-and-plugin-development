# 突变文库引擎矩阵（约束兼容性 + 选型）

TNFR1 战役五引擎实证 + 历史项目（2D4D2/HCGa1/HER2 冒烟）交叉。选型按**约束可控性**分三族。

## 三族分类

| 族 | 引擎 | 约束形态 | 位点级可控 | 适用 |
|---|---|---|---|---|
| **固定 pose 序列设计族** | LigandMPNN / AntiBMPNN / IgGM | 固定骨架+上下文重设计 | ✅ 完全（固定/允许位集） | 主文库主力 |
| **界面骨架微调族** | RFD4-Proteina（antibody ckpt） | annotated CIF（C_CRD 坐标钉/C_SEQ 身份锁/hotspot 锚） | ✅（注解级） | 界面重塑+新接触，突变数冲目标带 |
| **全段生成族** | AnewOmni | Chothia 整段 CDR mask | ❌ 段级（段内位点排除不支持） | 无锁位需求的 de novo；**约束体系下出局** |

## 逐引擎要点

### LigandMPNN（B1）
- 固定 TNFR1+FR 上下文重设计 CDR；T 梯队 0.1→0.5 控多样性（唯一序列 49→1865）
- 旗标：`--chains_to_design A --omit_AA C --batch_size 128`（301aa 体系 1500 会 OOM）
- 需 6 个权重全家（run.py 统一加载）；零违例合规可达成
- 家族恢复率 20-49%（低）→ 家族先验弱、多样化强

### AntiBMPNN（B2）
- env mlfold；从 example/<自建目录>/ 跑，模型脚本相对路径 ../../Running_AntiBMPNN_run.py，权重符号链接到 example/antibmpnn_model_weights
- 预处理三步：parse → assign_fixed → fixed_positions（HCGa1 先例）
- 高收敛（75 唯一/3000）+ 家族恢复率 92-98% → **共识锚+家族先验校准价值高**，不作多样性来源

### IgGM（B3）
- `design.py --run_task affinity_maturation` 语义 = **单点位扫描**：每 batch 在 fasta_origin WT 上只放 1 个 X 逐位枚举 → 产出是位点×氨基酸频率谱，非组合突变（2D4D2 "640k 样本 158 独特" 真相）
- mask_pos = fasta 中所有 X 位（枚举制）；输入 fasta 双链（抗原置末）
- 高冗余：5k-10k 样本即饱和；分析走 dedup_diff_freq.csv（merge_outputs.py 有 logomaker 空 df bug）
- 频率谱病态收敛（多数位 WT 100% 或单 aa 垄断）→ 有效信息集中 4-6 个多样性位点；与家族实证分歧留给 B6 调和

### RFD4-Proteina（B4）
- 权重：HF `nvidia/RFD4-Proteina` 的 `antibody/rfd4-proteina-antibody-2026-10-30-ema.ckpt`（preview 级未入 release-checkpoints.json；release AE 可配）
- 调用：`rfd4-generate inputs=X.cif hf_ckpt_path=null ckpt_path=<dir> ckpt_name=<ckpt> autoencoder_ckpt_path=<ae> num_replicates=N out_dir=Y`
- 模式：**inverse_folding 主跑**（骨架全固定→长度天然不变，规避 indel 风险）+ 双温层 tsr_k=4 保守 / 2 冲线；partial diffusion 辅跑（界面重塑通道）
- annotated CIF 注解：`condition_CoordinateGroup`（0=固定重原子单刚体组，-1=氢+自由位）/ `condition_sequence`（氨基酸名=锁）/ `condition_hotspot`（标在**抗原**表位原子上）
- gemmi PDB→CIF 两坑：`label_seq_id` 必须手动写（默认 '.' 报 polymer missing）；`label_asym_id` 必须设链名（选择器走 asym，默认 'Axp' 会全落空）
- 输出在模型自身坐标系——固定链 RMSD 必须先叠加再算（直接算 ~130Å 假象）
- 旗标：`'~metrics' compile_lengths=null +generation.dataset.sampling_transforms=null`（保锚点不被重采样）

### AnewOmni（B5，出局案例）
- 机制实证：`antibody.py:42 _extract_antibody_masks` 按 **lig_chains**（抗体侧）整段 Chothia CDR 重采样，fr 侧翼固定——**支持段级 mask 不支持段内位点排除**
- `length_ranges` off-by-one：`gen_utils.py:390 random.randint(l, r+1)` 闭区间——锁 HCDR1=7 要写 [7,6]
- generate.py 权重参数 bug：`--ckpt` 位置错（Confidence object 无 autoencoder）→ 正确 `--confidence_ckpt`
- ANARCI 要 hmmscan：启动带 `PATH=<env>/bin:$PATH`
- Chothia 段↔构体位映射先查清（H1 段是否与主文库位完全重合、段内有无锁位）再决定可救性
- PDBDataset 特征化 ~26min 静默期属正常；产出在 `candidates/{cplx_id}/`（glob 注意排除 pocket.pdb）

## 选型决策树

```text
有位点级锁死约束体系（热点扫描产出）？
├─ 是 → 序列设计族(B1多样性+B2家族锚) + RFD4(冲突变数/界面微调)
│        生成式族(段级) 除非其段边界与放开位完全重合且段内零锁位
└─ 否（整段 CDR 自由重设计）→ 三族全开
```

## 跨引擎共识判读

- 序列级共识极稀（引擎间序列空间几乎不重叠，B1∩B2 同序 1/7647）→ **共识在位点级**
- 位点共识强度分级：四引擎一致 > 三引擎 > 双引擎；与家族实证一致再加一档（102R→K 双引擎+家族实证 K）
- 分歧位（如保守 D107 vs 换 E）不在 B6 裁决——留给 C 阶段 ipSAE/能量证据裁决
