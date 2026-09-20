# 远端数据采集手册 (Data Acquisition)

> 定位：检索（发现 ID）→ **采集（按 ID 拉取原文）** → 清洗（本地规范化）。本手册补齐中间段。
> 原则：官方 REST 端点优先；采集产物缓存到 `family_analysis/raw/` 并登记 manifest。
> 实证来源：A9 项目（E-utilities 操纵子数据链、web BLAST、Foldseek 在线 API，2026-09）。

## 1. NCBI E-utilities（序列 + 基因组上下文）

```bash
EUTIL="https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# 限速: 无 API key 3 req/s; 带 key 10 req/s (url 加 &api_key=...)
# 批量取 FASTA: id 逗号分隔 ≤200/次(GET); 更大批量用 POST (id file)
curl -s "${EUTIL}/efetch.fcgi?db=protein&id=WP_002592014.1&rettype=fasta&retmode=text" -o hits/WP_002592014.1.fasta

# 检索→采集链: esearch 拿 ID 列表 → efetch 批量拉取
curl -s "${EUTIL}/esearch.fcgi?db=protein&term=alpha/beta+hydrolase+Enterocloster&retmax=100"  # XML 内 <Id> 列表
```

**基因组上下文采集（A9 操纵子实证链）**：
```bash
# 1) 蛋白 → 核酸 contig (elink)
curl -s "${EUTIL}/elink.fcgi?dbfrom=protein&db=nuccore&id=< protein_gid >&linkname=protein_nuccore"
# 2) 取 feature table / GenBank 全注释 (efetch)
curl -s "${EUTIL}/efetch.fcgi?db=nuccore&id=NZ_JADNLR010000011&rettype=ft&retmode=text"     # 特征表
curl -s "${EUTIL}/efetch.fcgi?db=nuccore&id=NZ_JADNLR010000011&rettype=gb&retmode=text"     # 全注释(解析 CDS, 扫描定位基因上下游 ±8kb 邻接基因)
```
A9 实证：WP_002592014.1 → contig NZ_JADNLR010000011, locus I2H27_RS19675 → ±8kb 扫出 allH/allB×2/NCS1×2/allE/allD/arcC 操纵子；第二 contig 共线性复现 = 强功能耦合证据。

**Web BLAST（无本地 blast+ 时）**：NCBI BLAST URL API（`https://blast.ncbi.nlm.nih.gov/Blast.cgi?CMD=Put&PROGRAM=blastp&DATABASE=nr&QUERY=...` → RID 轮询 `CMD=Get`）。A9 实证产物 blast_nr.xml / qblast.xml 即此路。大库首次结果可能排队数十分钟，Rid 轮询间隔 ≥60s。

## 2. UniProt REST

```bash
# 单条 FASTA
curl -s "https://rest.uniprot.org/uniprotkb/P32245.fasta"
# 检索式批量下载 (size≤500, cursor 分页; 大集合加 &stream=true)
curl -s "https://rest.uniprot.org/uniprotkb/search?query=gene:MC4R+AND+organism_id:9606&format=fasta&size=500"
# 带注释字段 (拓扑域/活性位点——build_region_cache 的上游)
curl -s "https://rest.uniprot.org/uniprotkb/P32245.json?fields=ft_topo_dom,ft_act_site,ft_binding,cc_cofactor"
```
⚠️ ID 核对守卫：下载后核对 entry 名称与物种（实证教训：MC4R=P32245，P33032 是 MC5R，拓扑域注释会全错）。

## 3. 结构库拉取（RCSB / AFDB）

```bash
# RCSB 实验结构 (ID 必须大写 4 字符; mmCIF 优先)
curl -s "https://files.rcsb.org/download/3H04.cif" -o raw/rcsb/3h04.cif
# 批量: 列表循环 + sleep 1 (礼貌限速); .pdb 路径仅旧格式需要

# AlphaFold DB 预测结构 (按 UniProt accession)
curl -s "https://alphafold.ebi.ac.uk/files/AF-P32245-F1-model_v4.cif" -o raw/afdb/AF-P32245-F1.cif
```
⚠️ 网络受限环境（本机实证）：AFDB 下载曾超时被墙 → 降级方案 = Foldseek 在线 API 直接检索（结果含叠合信息，~1 分钟）；大文件下载前先 `curl --max-time 30` 试探链路，慢链路改镜像（HF 系走 hf-mirror 的先例）。

## 4. Foldseek 在线 API 结果落盘

ticket 提交与轮询见 [pipeline-playbook.md](pipeline-playbook.md) Step 2b；结果文件 = `/api/result/<ticket>/<entry>`（json，含 alnScores/seqId/qcov/tmScore），逐 entry 拉取后本地汇总为 top_hits_summary。并行 ticket 别开太多（API 公共服务）。

## 5. 抗体-抗原专用库（治疗性抗体/纳米抗体设计必用）

选型矩阵：

| 库 | 内容 | 典型用途 | 更新 | 获取方式 |
|---|---|---|---|---|
| **SAbDab2** | 抗体-抗原结构总库 (SAbDab 重建版, 稳定 SAbDab2 ID, IMGT 编号, VNAR/SD-H 等 6 类 instance) | 结构模板、表位统计、序列检索 | weekly | sabdab2.opig.stats.ox.ac.uk (网页检索/批量导出) |
| **SAbDab2 AI/ML 训练集** ⭐首选 | 清洗后结构+序列+split (半年度版) | ML 训练、CDR/表位统计、模板库 | 每 6 个月 | Zenodo record 20083995; **本地已有缓存 (见 5.0)** |
| **Thera-SAbDab** | 治疗性抗体 (WHO INN) × 结构/序列映射 | 临床抗体基准、专利对照 | weekly | OPIG 网页 csv |
| **CoVAbDab** | 冠状病毒抗体序列 (VH/VL 全序列) + 结构映射 | 冠状病毒抗体工程、逃逸分析 | ~weekly | OPIG 网页 date-stamped csv |
| **OAS** | 天然抗体序列库 (paired/unpaired 库) | 人源化参照、CDR 统计、语言模型训练语料 | 库级版本 | OPIG 网页 unit 级下载 (TB 级, 按需取) |
| **IMGT** | 免疫球蛋白种系基因 / 参考目录 | germline 对照、V-D-J 划分基准 | 库级版本 | Gene-DB 查询 + IgBLAST 参考目录随包 |
| **IEDB** | 表位 (B/T 细胞) + 抗原 + 测定数据 | 抗原表位注释、免疫原性先验 | 库级版本 | REST API / 网页导出 csv |
| **AbDb / NanoLAS** (备选) | 编号化抗体结构 / 纳米抗体 | 特定场景 | — | 站点导出 |

### 5.0 本地缓存（首选起点）：SAbDab2 AI/ML 训练集

> 命名澄清：该数据常被口述为"zando"，检索确认官方名称为 **SAbDab2 clean training data**（Capel et al. 2026, bioRxiv doi 10.64898/2026.06.16.732554；数据 Zenodo record 20083995，每 6 个月更新）。

本地缓存（实证 2026-09-20 盘点）：

```text
<SABDAB2_PROJECT_DIR>/data/antibody_antigen_complexes/splits/splits_final/
├── ab_split.csv        15,641 行  抗体实例级: INSTANCE/PDB_ID/SABDAB_ID/H/L 链 ID/方法/分辨率/
│                                 Hseq/Lseq(实测+expected)/IMGT numbering 列表/CDRH1-3+CDRL1-3/
│                                 聚类去冗列(cdrh3_cluster 等)/ab_split(train|val|test)
├── abag_split.csv      15,641 行  抗原-抗体配对级: 抗原链 ID/类型(PROTEIN/SUGAR/PEPTIDE/ION)/
│                                 抗原序列与解析区间/ag_split 划分
├── ab_split_sd.csv     3,414 行   非冗余变体 split (基准/低冗余场景用)
├── abag_split_sd.csv   3,414 行   同上, 配对级
└── pdb_0000XXXX_X_Y.cif  8,846 个 (1.9GB)  清洗后复合物结构, 文件名=重构PDB ID_抗体链_抗原链
```

使用守卫：
- **版本锚定**：CSV 内 `SABDABupdate` 列记数据版本（本地版=20260430）；半年新版发布后勿混用两个版本的 split（防 train/test 泄漏）。
- **链名已标准化**：cif 内链命名与 CSV 的 H/L/ag 列对应，无需再做 SAbDab 老式的链映射清洗。
- **cif 覆盖度**：8,846 cif < 15,641 行——CSV 行含未解析/未下载实例，用前先按 INSTANCE 过滤本地实际存在文件。
- **低冗余分析用 `_sd`**：跨抗体统计（CDR 构象、表位富集）用 `_sd` 变体防同源膨胀；全量 split 用于 ML 训练。
- **单域抗体**：VNAR/SD-H/SD-L 类型在该库有原生 instance type 标注（SAbDab2 新特性），比老 SAbDab 的 VHH 标记更可靠。

### 5.1 SAbDab2 / Thera-SAbDab / CoVAbDab（OPIG 系）

```bash
# SAbDab2 新站 (sabdab2.opig.stats.ox.ac.uk): 网页检索/按序列查/按 CDR 查, 支持自定义批量导出
# ⚠️ 旧 opig webapps/newsabdab 端点迁移期已过, 一律以 sabdab2 新站为准; URL 勿硬编码旧路径
# AI/ML 训练集 (与本地缓存同源, 每 6 个月更新):
curl -sL --max-time 30 "https://zenodo.org/records/20083995" -o raw/antibody/sabdab2_zenodo_page.html  # 页面内取最新版文件链接
# 按 PDB 号取结构本体 (summary/训练集索引驱动):
curl -s "https://files.rcsb.org/download/7PIU.cif" -o raw/antibody/7piu.cif
```
- **CoVAbDab**：date-stamped 全量 csv（含 VH/VL FASTA 序列、CDR、中和状态），一条 curl 即可入库，注意按下载日期归档。
- **清洗范式本机参照**：`<HOME>/.trae-cn/skills/antibody-design-agent/MAGE/repo/Data cleaning/`（SAbDab detagging、CoVAbDab curation、antigen alignment 实战 notebook）——编号/去冗余逻辑可直接复用。
- **编号工具衔接**：序列拿到后用 ANARCI 按 IMGT/Chothia/Kabat 编号再比对（工具侧, 非采集）。

### 5.2 OAS（天然抗体序列库）

- paired（轻重链配对，约 1TB+）/unpaired 分开组织，**unit 级**下载（单 unit 约 10-20 万序列）。
- 原则：按用途取最小集（如人源化参照取 human paired 若干 unit），勿整库镜像。
- ⚠️ unit 编号与 URL 结构随 OPIG 版本变化，从 OAS 页面现取文件清单。

### 5.3 IMGT / IgBLAST germline

```bash
# IgBLAST 本体 (NCBI FTP, 稳定) — 含 human germline 参考目录 (imgt)
curl -sL --remote-name "https://ftp.ncbi.nih.gov/blast/executables/igblast/release/LATEST/ncbi-igblast-<ver>-x64-linux.tar.gz"
# 其他物种/自定义 germline: IMGT Gene-DB 查询导出 fasta, 或 IMGT/V-QUEST 参考目录下载
#   https://www.imgt.org/genedb/  (query: species=Homo sapiens, group=IG)
```

### 5.4 IEDB（表位与测定数据）

```bash
# REST API v1 (查询式, 结构化 json)
curl -s "https://www.iedb.org/api_v1/epitope_search?organism=SARS-CoV-2&limit=10"
# 全量导出 (网页 Downloader, csv 按表分文件: epitope/assay/receptor)
#   https://www.iedb.org/downloader.php  -> 单文件可达百 MB 级
```
用途：抗原侧表位注释（与 structure-prediction-analysis 的 --epitope gate 衔接）、免疫原性先验。

## 6. 采集规范（防数据事故）

| 规则 | 说明 |
|---|---|
| manifest 登记 | `raw/fetch_manifest.csv`：id, source, url, bytes, sha256(可选), date, local_path——后续清洗/复现全以 manifest 为准 |
| 幂等且可补 | 本地文件存在且 >0 字节则跳过；但 manifest 缺行必须补登记（防"有文件无台账"） |
| 重试 | `curl --retry 3 --retry-delay 5 -sS`；连续失败先测链路再重试 |
| 限速合规 | NCBI 3/10 req·s⁻¹；RCSB/UniProt 批量加 sleep；UA 带联系邮箱 |
| 来源分目录 | raw/antibody/（SAbDab/CoVAbDab/OAS/IMGT/IEDB）与 raw/{ncbi,uniprot,rcsb,afdb}/ 分开落盘, manifest 同列 |
| 版本锚定 | AFDB 带版本号 (model_v4)；UniProt 记录 accession + 下载日期——结构库会随版本更新变化，复现需锚定 |
| 原文落盘 | 检索结果（blast xml / foldseek json / m8 表）也归 raw/ 存档——分析脚本重跑依赖它们，勿只留汇总 |
