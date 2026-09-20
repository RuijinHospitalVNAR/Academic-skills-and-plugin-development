# 流水线操作手册 (含 A9 全流程实例)

> 每个 step 给出可直接改用的命令模板 + A9 实证产物示例。A9 = 290aa 未知功能蛋白（Enterocloster 来源），最终定案 α/β 水解酶。

## Step 0. 序列获取与清洗

```bash
# 目标蛋白 FASTA 准备（预测来源项目通常已有 a9.fasta）
head -c 300 query.fasta
```

清洗规则：去 * / 终止符；统一大写；记录序列长度（后续所有 coverage 计算的基线）。

## Step 1. 序列层检索（三连）

```bash
# 1a. BLAST nr —— 物种来源与近缘 (在线 E-utilities 或 blast+ 客户端)
blastp -query query.fasta -db nr -evalue 1e-4 -outfmt 5 -num_alignments 100 -out blast_nr.xml
# 1b. BLAST swissprot —— 人工注释参考（零命中也有信息量: 缺注释≠无同源）
blastp -query query.fasta -db swissprot -evalue 1e-4 -outfmt 5 -out blast_sp.xml
# 1c. MMseqs2 vs UniRef90 —— 中远缘全覆盖 + 可直接复用 AF3 的 MSA 库
mmseqs easy-search query.fasta uniref90_2022_05.fa mmseqs_uniref90.m8 tmp \
  --format-output "target,qlen,tlen,evalue,pident,alnLen"
# 1d. (可选) jackhmmer 迭代检索 —— AF2/AF3 原生 MSA 路线
# 适用: 远缘深挖, 或需与 AF3 特征管线同语义备料 (unpairedMsa 供 AF3 输入 json)
# 代价: 大库需 hmmpress 索引, 数小时级; 快筛场景勿用 (用 1c)
jackhmmer -N 3 --cpu 8 query.fasta uniref90_db > jackhmmer_uniref90.sto
```
选型：家族快筛走 1a/1c（MMseqs2 实证 85G 直搜，ColabFold 同路线）；远缘深挖/AF3 供料走 1d（AF3 原生语义）。

**报告三元组铁律**：每个 Top hit 记 `identity / coverage / bit-score(E-value)`。A9 实证：nr Top1 WP_002592014.1 = α/β hydrolase [Enterocloster], 100% id (290/290), bit 597 → 物种锁定。

**产物族谱收簇**：Top 命中收 FASTA → MAFFT 比对 → 催化基序保守性图（motif 正则/MEME de novo + 比对列位）。

## Step 2. 结构层检索（Foldseek 两库）

```bash
# 2a. 提取链（CIF→PDB, Biopython 保留残基号!）
# ⚠️ 坑: 手写 CIF→PDB 常把残基号全部重编为 1 → Foldseek 报 "Too short" 直接弃用
python extract_chain.py model.cif A > query_fixed.pdb   # Biopython MMCIFParser

# 2b. 在线 API 检索 (afdb50 全景 + pdb100 实验结构)
# ⚠️ 必须 -F "mode=3diaa"; all/tmalign 均报 Mode 验证错
curl -X POST https://search.foldseek.com/api/ticket \
  -F "q=query_fixed.pdb" -F "database=afdb50" -F "mode=3diaa"
# 轮询 ticket → /api/result/<id>/<entry> 下载 json
# pdb100 同法 (database=pdb100) —— Top 命中即"实验结构锚点"候选
```

A9 实证：afdb50 Top1 = A0A6I2GL88 "Alpha/beta hydrolase fold" (29% id, qcov 98%)，Top30 全部 α/β 水解酶/酯酶家族；pdb100 Top1 = **3h04_A** (S. aureus, 27% id, E=5.8e-24)。

## Step 3. 定量叠合与催化机器核对

1. **全局超叠**（Kabsch，官方库实现）：A9 vs 3h04 → 267 CA, RMSD 2.04Å。
   ⚠️ 手写 Kabsch 两坑：矩阵约定（`M=U@D@Vt, t=qc-pc@M`）与重复加质心；实现后必须过"同文件=0"自检，或直接用 gemmi/Biopython 官方 superpose。
2. **催化残基几何对照表**：把候选催化残基映射到模板编号（注意 Foldseek 内部号 offset，3h04 案例为 +2），逐对距离对比。A9 vs 3h04：SerOG–HisNE2 2.73/2.77Å，HisND1–AspOD2 4.74/4.09Å → 三元组几何几乎重合。
3. **口袋残基一一对应**：配体（或模板配体）4.5Å 内残基在两个结构中列出对照。
   ⚠️ 移植配体姿态后 <1Å 接触可能含堆积伪影（侧链无重排），方向性结论仍有效但注明。

## Step 4. 基序与功能仲裁

- motif 扫描：正则匹配已知基序（GxSxG / HGGG / GxGxxG / GD 等）；同源簇足量时用 **MEME** de novo 发现（`meme homologs.fasta -protein -nmotifs 10 -minw 6 -maxw 30 -oc meme_out/`），已知矩阵用 **FIMO** 扫 query（`fimo motif.meme query.fasta`）。**全部结果仍需结构距离二次验证**。
- 反例警示（A9 实证两条）：
  - `GGGL` 看似 `GGGxG` 但第 6 位非 G → 不构成经典 Rossmann/核苷酸结合模体（用于排除 FAD 结合）；
  - Smith-Waterman 局部比对 vs HpxO 仅 36 分（噪声级）+ 最佳局部比对仅 10% 覆盖 → 无全局同源性 → 与"HpxO 型黄素蛋白"假说切割。
- **基因组上下文仲裁**（折叠-功能矛盾时）：NCBI E-utilities 链 elink(protein→nuccore) → efetch(rettype=ft) 取邻接基因。A9 实证：位于保守尿囊素利用操纵子 (allH→allB×2→NCS1×2→**A9**→allE→allD→arcC)，共线性在第二菌株复现 → 功能与尿囊素分解通路强耦合 → 支持线性酰胺底物假说。
- 家族归属须写 **VERDICT.md**：序列层证据（1a/1b/1c）+ 结构层证据（2/3）+ motif/几何核对 + 机制含义 + 残留不确定性。

## Step 5. 与下游技能的衔接

- 结构锚点（3h04 类）→ `md-simulation-workflow` 作 MD 体系参照 / QM/MM 口袋几何对照。
- 家族归属 + MSA → `structure-prediction-analysis` 的 AF3 templates/MSA 语义（受体链 MSA 复用）。
- 收集的同源序列（uniref90 hits）可直接喂 AF3 MSA 库构建。
