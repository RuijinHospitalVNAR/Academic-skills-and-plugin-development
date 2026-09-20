---
name: seq-struct-analysis
description: 蛋白质序列与结构检索、获取、清洗与分析流水线。Use when 用户要鉴定蛋白家族归属或同源序列（BLAST/Jackhmmer/HHsuite/MMseqs2）、从远端库采集数据（NCBI/UniProt/RCSB/AlphaFold DB + 抗体-抗原库 SAbDab/CoVAbDab/OAS/IMGT/IEDB；序列/结构批量下载、基因组邻接区扫描）、做结构相似性检索与折叠归类（Foldseek afdb50/pdb100、TM-align/DALI）、获取与清洗 PDB/FASTA 数据（残基号修复、链提取、CIF 转换）、做多序列比对与催化基序保守性分析（MAFFT/MUSCLE/MMseqs2 + MEME/FIMO motif 发现与扫描）、或串联"序列层+结构层"双重证据回答"这个蛋白是什么/像谁/催化机器是什么"。关键词：家族鉴定、同源检索、foldseek、mmseqs2、hmmer、jackhmmer、meme、fimo、hhpred、BLAST、序列分析、结构比对、数据下载、efetch、uniprot、rcsb、afdb、sabdab、sabdab2、covabdab、oas、imgt、iedb、igblast、抗体数据库、antibody database、数据采集、TM-score、催化三联体、motif。
---

# 序列-结构分析流水线 (Sequence-Structure Analysis Pipeline)

固化自 A9 尿酸酶项目家族鉴定全流程（290aa 未知蛋白 → 三重证据定案 α/β 水解酶，2026-09）。工具选择经评估精简：**BLAST（近缘）→ MMseqs2（中远缘+大数据集）→ HMMER/HHsuite（远缘 profile）→ Foldseek（结构层）→ TM-align/Kabsch（定量叠合）**，去除冗余环节。

## 0. 何时使用

- 未知蛋白的家族归属 / 功能注释（序列+结构双证据）
- 同源序列收集（建 MSA / 找催化基序 / 收 AF3 templates）
- 结构近邻检索、实验结构锚点挑选（如 3h04 之于 A9）
- 抗体-抗原数据采集（SAbDab2 及其 AI/ML 清洗训练集——本地已有缓存、CoVAbDab/OAS 抗体序列、IMGT germline、IEDB 表位）；通用数据清洗（PDB/CIF/FASTA 坑）

## 1. 标准流水线（三步定案法）

```text
步骤1 序列层                步骤2 结构层                 步骤3 整合定案
BLAST nr (近缘/物种来源)     Foldseek afdb50 (全景)       序列+结构证据交叉
BLAST swissprot (人工注释)   Foldseek pdb100 (实验锚点)   催化残基/基序几何核对
mmseqs2 UniRef90 (中远缘)    TM-align/RMSD 定量叠合       → 家族归属 + 机制图景
      ↑ 步骤1.5 数据采集: 按 ID 拉取原文 (同源 FASTA/结构 CIF/基因组邻接区)
```

命令级操作手册与 A9 全流程实例：[references/pipeline-playbook.md](references/pipeline-playbook.md)
工具对比与选型矩阵（HMM/MMseqs2/MEME 档位）：[references/tool-matrix.md](references/tool-matrix.md)
远端数据采集（通用库 + 抗体库 SAbDab/CoVAbDab/OAS/IMGT/IEDB 拉取命令与限速规范）：[references/data-acquisition.md](references/data-acquisition.md)

## 2. 选型速查（详见 tool-matrix）

| 任务 | 首选 | 备选 | 一句话理由 |
|---|---|---|---|
| 近缘同源+物种来源 | BLAST nr | mmseqs2 easy-search | 物种注释最全 |
| 中远缘/大数据集 | **MMseqs2** | BLAST | 快 100-10000x，灵敏度相当；可直接搜 AF3 的 MSA FASTA 库（实证 uniref90 85G 可直接 easy-search） |
| 远缘/迭代深化 | **Jackhmmer** (HMMER 迭代) / HHsuite (hhblits) | hmmsearch | 迭代 profile HMM，AF2/AF3 原生 MSA 路线；深 MSA/远缘灵敏度高于单轮比对 |
| AF3 MSA 库检索 | **MMseqs2** easy-search（实证 85G 直搜） | jackhmmer（AF3 原生语义，需 hmmpress 索引，慢但高灵敏） | ColabFold 服务端 MSA 亦用 MMseqs2 替代 jackhmmer 提速 |
| 结构近邻 | **Foldseek** | DALI (慢但金标准) | 3Di 编码，结构检索速度≈序列 BLAST |
| 定量叠合 | TM-align / Kabsch | DALI | RMSD+TM-score 报告标准 |
| MSA 构建 | MAFFT / MMseqs2 msa | MUSCLE | 下游 HMM 的输入 |
| motif 发现/扫描 | **MEME Suite** (meme/FIMO/MAST) | 正则扫描 | meme de novo 发现保守基序（无需预设 pattern），FIMO/MAST 用已知矩阵扫 query；结果仍需结构距离二次验证 |
| 抗体库本地缓存 | SAbDab2 训练集 (splits_final, 15.6k 实例) | Zenodo 半年新版 | 路径与守卫见 data-acquisition.md §5.0 |
| 远端采集 | NCBI efetch / UniProt REST / RCSB / AFDB | — | 检索得 ID → 拉原文；命令与限速见 data-acquisition.md |

## 3. 高频坑速查

| 坑 | 规则 |
|---|---|
| CIF 提取链残基号 | 手转 PDB 常把残基号全变 1 → Foldseek 判 "Too short" 弃用；用 Biopython 从 CIF 提取链并保留原残基号（A9 实证） |
| Foldseek 模式 | 在线 API 必须 `-F "mode=3diaa"`（all/tmalign 均报 Mode 验证错）；AFDB50 本地下载被墙时用在线 API（~1 分钟） |
| Foldseek 内部编号 | 命中模板残基号有 offset（3h04 从 3 起，内部号 +2），叠合前先核对 |
| BLAST e-value | 家族归属要报 identity + coverage + bit score 三元组，勿只报 e-value（swissprot 零命中 ≠ 无同源，可能是缺人工注释） |
| 基序判定 | 催化基序（如 GxSxG nucleophile elbow、HGGG oxyanion hole、GxGxxG Rossmann）用正则或 MEME de novo 发现 + 结构距离双重验证；单凭序列 motif 会误判（GGGL 看似 GGGxG 但第 6 位非 G 不构成经典模体，A9 实证） |
| 折叠-功能矛盾 | 序列注释（如 "α/β hydrolase"）与下游功能（如氧化酶）冲突时，用结构检索 Top 命中的家族分布 + 操纵子基因组上下文（邻接基因功能耦合）做第三方仲裁 |

## 4. 产出清单

```text
family_analysis/
├── raw/            采集原文: fetch_manifest.csv + {ncbi,uniprot,rcsb,afdb,antibody}/ 批量产物
├── blast/          nr + swissprot 的 xml/表格 (Top hits 三元组)
├── mmseqs/         uniref90 hits + query fasta
├── foldseek/       afdb50/pdb100 结果 json + top_hits_summary + 叠合产物 (xxx_on_yyy.pdb + 对比图)
└── VERDICT.md      家族归属结论: 序列层证据 + 结构层证据 + 基序/几何核对 + 机制含义
```
