# 工具选型矩阵 (Tool Matrix)

> 评估原则：保留高效准确环节，去除冗余低效环节。✅ = 本插件实证使用；其余为行业主流备选。

## 1. 序列检索档位（按进化距离）

| 工具 | 档位 | 核心算法 | 优势 | 局限 | 实证记录 |
|---|---|---|---|---|---|
| **BLAST** (blastp) | 近缘 (ident>30%) | 种子-扩展-统计 | 物种/注释最全 (nr)；swissprot 人工注释 | 大库慢；远缘漏检 | ✅ A9: nr Top1 100% id 锁定物种；swissprot 零命中（缺注释，非无同源） |
| **MMseqs2** | 中远缘/超大数据集 | 降维分组+空間索引 | 快 100-10000x，灵敏度≈BLAST；`easy-search` 一条命令；可直接搜 AF3 的 MSA FASTA（纯文本库） | 报告字段与 BLAST 不同需适配 | ✅ A9: UniRef90 (85G, 214M seqs) 396 hits，Top1 98.9% id |
| **HMMER** (jackhmmer/hmmsearch/phmmer) | 远缘/迭代 (profile) | Profile HMM (Plan7) | 家族级灵敏度；Pfam 扫描标配 | 需先建 MSA/拿现成 HMM；大库慢 | 行业标准；**jackhmmer = AF2/AF3 原生 MSA 生成器**（UniRef90/Mgnify 走 jackhmmer，BFD 走 hmmsearch） |
| **HHsuite** (hhblits/hhsearch) | 远缘 (HMM-HMM) | HMM-HMM 比对 | 远缘灵敏度业界最高之一；HHpred 网页版 | 建 DB 成本高 | hhblits 亦为 AF2 MSA 数据源 |
| PSI-BLAST | 远缘 (迭代) | 迭代 profile | 无需装新工具 | 迭代漂移风险 | 备选 |

**决策规则**：ident>30% 用 BLAST；30%>ident 或库>10G 用 MMseqs2；两者都弱（<20% 或无命中）上 HMMER/HHsuite（需家族 HMM 或先收同源建 MSA）。

**Jackhmmer vs MMseqs2（实证选型）**：
- **MMseqs2**：单轮超快（快 100-10000x），ColabFold 服务端 MSA 已用它替代 jackhmmer；✅ 实证可直接 `easy-search` AF3 自带的 85G uniref90 FASTA。适合家族快筛与大库检索。
- **Jackhmmer**：迭代 profile HMM（默认 N=3，逐轮收紧 HMM），深 MSA 与远缘灵敏度更高；是 AF3 官方特征管线的原生组件——若目标是给 AF3 备料（json 内 unpaired/paired MSA 语义），用 jackhmmer 走 AF3 同源路线最不易踩格式坑。代价：大库需 `hmmpress` 索引，耗时段（数小时级）。
- **结论**：家族鉴定快筛 → MMseqs2（流水线 1c）；远缘深挖或为 AF3 供料 → jackhmmer（流水线 1d，可选）。

## 2. 结构检索与对齐档位

| 工具 | 档位 | 核心算法 | 优势 | 局限 | 实证记录 |
|---|---|---|---|---|---|
| **Foldseek** | 结构近邻检索 | 3Di 字母表 (结构→序列化) + 替代矩阵 | 速度≈序列 BLAST，库全 (afdb50/pdb100) | 对齐精度略逊 DALI；在线 API 有模式限制 | ✅ A9: afdb50 Top1 定折叠；pdb100 Top1=3h04 实验锚点 |
| **TM-align** | 定量结构叠合 | 迭代动态规划 + TM-score | RMSD/TM-score 报告标准 | 全局对齐，慢于 Foldseek | ✅ 3h04 并排对比用超叠实现（Kabsch） |
| DALI | 结构对齐金标准 | 距离矩阵二轮规划 | 远缘折叠判定的文献基准 | 慢；在线服务排队 | 备选（Foldseek 命中存疑时仲裁） |
| CE / CE-CP | 结构对齐 | 组合扩展 | 经典 | 慢 | 备选 |
| PyMOL/RDKit superpose | 快速目检 | Kabsch | 一条命令 | 无统计显著性 | 仅目检用 |
| gemmi superpose_positions | 程序化叠合 | Kabsch (官方库) | 结构流水线内嵌 | — | ✅ AF3 姿态聚类实证（手写 Kabsch 有坑时改官方库） |

**决策规则**：全景扫描/找近邻 → Foldseek（在线 API `mode=3diaa`）；定量报告（RMSD/TM-score）→ TM-align 或 Kabsch 超叠；Foldseek 与功能注释矛盾 → DALI 仲裁。

## 3. MSA 与 motif 档位

| 工具 | 用途 | 备注 |
|---|---|---|
| MAFFT | MSA 构建（精度优先 L-INS-i） | 下游 HMM/基序图输入 |
| MUSCLE / Clustal Omega | MSA 快速构建 | 大集合用 super5 |
| MMseqs2 `msa` / `easy-cluster` | 百万级序列聚类+MSA | 大数据集首选 |
| EMBOSS/正则扫描 | 催化基序 motif 扫描 | 必须配结构距离二次验证（见 SKILL.md §3） |
| **MEME** (MEME Suite) | de novo motif 发现 | 蛋白模式 `-protein`，从同源簇无监督发现保守基序（无需预设 GxSxG 式 pattern） |
| **FIMO / MAST** (MEME Suite) | 已知 motif 矩阵扫描/比对 | MEME 输出的 .meme 矩阵（或 PROSITE 下载矩阵）扫 query；结果仍需结构距离二次验证 |
| InterProScan | 结构域/Pfam 注释 | 家族归属的独立第三方证据 |

✅ **MME 已澄清（2026-09-20 用户确认）**：MME = **MEME**（Multiple EM for Motif Elicitation，motif 发现套件），归入 §3 motif 档位（见 MEME/FIMO/MAST 行）。

## 4. 已剔除的冗余环节（评估记录）

| 环节 | 剔除理由 |
|---|---|
| PSI-BLAST 作为主力迭代检索 | MMseqs2 全覆盖且快千倍，迭代漂移难控 |
| 本地建 Foldseek AFDB50 库 | 下载被墙 + 200M+ 结构维护成本；在线 API ~1 分钟够用（离线集群场景除外） |
| MEME 输出 motif 直接当结论 | MEME 是统计发现工具， motif 仍需结构距离/催化几何二次验证（A9 案例：GGGL 看似 GGGxG 但不构成经典模体） |
| 手写 Kabsch 叠合用于结构比较 | 已两次实证踩坑（重复加质心、矩阵约定），一律用官方库（gemmi/Biopython）并在实现后跑"同文件=0"自检 |
| DALI 作为首选结构检索 | 慢一个量级；Foldseek 3Di 已足够灵敏，DALI 降为仲裁 |
| swissprot 零命中即判 "novel" | 必须交叉 nr + 结构层再下结论（A9 案例：swissprot 零命中但 nr 100% 命中） |
