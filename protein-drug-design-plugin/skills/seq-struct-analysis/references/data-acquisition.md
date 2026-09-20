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

## 5. 采集规范（防数据事故）

| 规则 | 说明 |
|---|---|
| manifest 登记 | `raw/fetch_manifest.csv`：id, source, url, bytes, sha256(可选), date, local_path——后续清洗/复现全以 manifest 为准 |
| 幂等且可补 | 本地文件存在且 >0 字节则跳过；但 manifest 缺行必须补登记（防"有文件无台账"） |
| 重试 | `curl --retry 3 --retry-delay 5 -sS`；连续失败先测链路再重试 |
| 限速合规 | NCBI 3/10 req·s⁻¹；RCSB/UniProt 批量加 sleep；UA 带联系邮箱 |
| 版本锚定 | AFDB 带版本号 (model_v4)；UniProt 记录 accession + 下载日期——结构库会随版本更新变化，复现需锚定 |
| 原文落盘 | 检索结果（blast xml / foldseek json / m8 表）也归 raw/ 存档——分析脚本重跑依赖它们，勿只留汇总 |
