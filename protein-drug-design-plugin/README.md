# 蛋白质药物设计与科研全链路技能插件 (protein-drug-design)

[English](README_EN.md) | 简体中文

蛋白质药物设计**全链路**技能插件（v0.4.0，**44 项技能**）：

- **计算主线**（4 项自研技能，实证固化）：**序列/结构鉴定 → AI 结构预测与批量分析 → 分子动力学验证 → 结合能与机制深化**
- **管理与元技能**：skill-manager（技能生命周期管理）
- **全链路扩展**（39 项收编技能）：文献调研 → 研究构思 → 采集前实验设计与预注册 → 采集后统计分析 → 学术写作 → 论文审查 → 成果展示（PPT/视频/科研配图/专利草稿/实验日志）

## 目录结构

```text
protein-drug-design-plugin/
├── .trae-plugin/plugin.json          # 插件清单（入口声明）
├── workflow.yaml                     # 工作流编排配置（11 阶段/数据契约/扩展点）
├── install.sh                        # 多 IDE / 桌面 agent 安装适配器
├── data/                             # 技能台账 + 只追加审计日志（skill-manager 产物）
├── templates/skill-template/         # 新技能骨架模板（扩展入口）
└── skills/                           # 44 项技能（含 skill-manager 自管理）
    ├── (计算主线 4 项)               # seq-struct-analysis / structure-prediction-analysis /
    │                                 # md-simulation-workflow / protein-design-workflow
    ├── (管理 1 项)                   # skill-manager（添加/合并/下架+台账审计）
    ├── (科研全链路 19 项)              # academic-writing / scispark / experiment-design /
    │                                 # statistical-analysis / papercheck / visual-deck-builder / ...
    └── (nature-skills 20 项)         # nature-writing / nature-reviewer / nature-paper-card /
                                      # nature-figure / nature-paper-to-patent / ...
```

## 技能清单

### 计算主线（自研 4 项）

| 技能 | 内容 | 实证来源 |
|---|---|---|
| **seq-struct-analysis** | 家族鉴定三步定案法（BLAST/Jackhmmer/MMseqs2 + Foldseek/TM-align）；数据采集（NCBI/UniProt/RCSB/AFDB + **SAbDab2 本地缓存**/CoVAbDab/OAS/IMGT/IEDB）；抗体编号（**ANARCII transformer 优先，VNAR 必用 `-t vnar`**）；MEME motif 发现 | 290aa 未知蛋白→α/β水解酶定案全流程 |
| **structure-prediction-analysis** | AF3/Protenix/OpenDDE 批量推理（MSA 先行+多卡 round-robin+传输瘦身）；双轴四象限结果分析（含 targeted epitope 与膜侧判定） | MC2R/MC4R VNAR 项目（151 候选×100 seeds） |
| **md-simulation-workflow** | AMBER 全流程（BCC/RESP 参数化→tleap 三道守卫→平衡生产→cpptraj）；收敛双判据（核心区 RMSD+块平均 SEM）；五引擎对比；CpHMD/QM/MM/MM-GBSA 口径 | A9 尿酸酶 + 48 体系 500-769ns |
| **protein-design-workflow** | 任务路由、11 阶段数据契约、算力排期基线、扩展接入四步法 | 编排层设计 |

### 管理与元技能

**skill-manager** —— 技能生命周期管理：添加/合并/下架的半自动流程（对比分析后三选一决策）、台账与只追加审计日志、单个+批量双模式（详见下文专节）。

### 全链路扩展（收编 39 项）

| 类别 | 技能 |
|---|---|
| 文献与研究构思 | scispark、sci-employee-deep-research、giiisp-paper-search-apis、nature-academic-search、nature-literature-pipeline、nature-citation、nature-paper-card |
| 研究设计与统计 | experiment-design（预注册/DOE/功效）、statistical-analysis、research-baseline-builder、nature-statistics、nature-experiment-log |
| 学术写作与审查 | academic-writing、scientific-humanization、papercheck、thesis-audit-reviewer、nature-writing、nature-polishing、nature-reader、nature-reviewer、nature-response、nature-ref-verifier |
| 成果展示与转化 | visual-deck-builder、practical-course-producer、manim-agent、giiisp-scientific-image-generation、nature-paper2ppt、nature-image2ppt、nature-figure、nature-paper-to-patent |
| 申报与数据合规 | nature-proposal-writer、nature-data、nature-downloader |
| 工具与元技能 | find-science-skills、skill-criticagent、mcp-criticagent、nature-shared |

> 触发面治理：与计算主线重叠的 4 项（experiment-design / statistical-analysis / scispark / research-baseline-builder）已在 description 加注**边界声明**（如"MD 收敛判据走 md-simulation-workflow"），防止双重触发。

## 工作流总览

```text
[0a]scispark 文献构思 ─[0b]experiment-design 预注册
  v
FASTA ──[seq-struct-analysis]──> 家族归属+结构锚点
   └──[structure-prediction-analysis]──> model.cif+置信度 ──> 四象限/口袋分析
          └──[md-simulation-workflow]──> prmtop(守卫) ──> 轨迹+收敛 ──> ΔG±SEM/机制
                └─[statistical-validation]─[writing]─[review]─[presentation]
```

11 个阶段的完整契约见 [workflow.yaml](workflow.yaml)。

## 安装使用（多 IDE / 桌面 agent 适配）

仓库自带 `install.sh`，按目标工具把 `skills/` 复制到其技能目录：

| 目标 | 命令 | 技能目录 |
|---|---|---|
| Trae / Trae CN | `bash install.sh trae` | `~/.trae-cn/skills`（或 `~/.trae/skills`） |
| Claude Code | `bash install.sh claude` | `~/.claude/skills` |
| OpenAI Codex CLI | `bash install.sh codex` | `~/.codex/skills`（`$CODEX_HOME`） |
| Cursor | `bash install.sh cursor` | `~/.agents/skills` + rules 指向行 |
| Windsurf | `bash install.sh windsurf` | `~/.agents/skills` + rules 指向行 |
| OpenCode | `bash install.sh opencode` | `~/.config/opencode/skills` |
| OpenClaw / 桌面 agent | `bash install.sh openclaw` | `~/.agents/skills`（agents-skills 规范） |
| 帮助 | `bash install.sh list` | — |

适配原理：Agent Skills 规范（agentskills.io）已是跨工具通用标准，各工具差异只在技能目录位置。Cursor/Windsurf 无原生加载器，脚本会打印需加入项目 rules 的指向提示。社区 CLI 替代：`npx skills add RuijinHospitalVNAR/Academic-skills-and-plugin-development --skill '*' --yes --copy`。

### 技能可见性与英文化策略

技能分两层：**description**（常驻系统提示、决定触发，受众最先看到）——已全部双语化（中文技能补 `EN:` 摘要行，英文技能补中文触发词行）；**正文与 references**（触发后才加载）——保持中文为主：实证记录为中文原文，机械翻译易失真，重参考资料按需逐步英文化。

## 技能生命周期管理（skill-manager）

内置 `skill-manager` 技能管理本插件全部技能的**添加/合并/下架**：

- **ADD 半自动流程**：信号采集（踩坑≥2次/排错>1h/用户点名）→ 草案生成（关键点询问用户）→ `compare.py` 与现有技能算相似度（description Jaccard + 正文 bigram + 触发词冲突）→ 按阈值三选一（**吸收/合并/拒绝**）→ `ledger.py` 登记
- **REMOVE 流程**：识别信号（平台下线/长期零触发/职责被覆盖）→ 用户确认 → 自动 tar 备份 + 三处删除（插件/用户级目录）+ workflow.yaml 引用清理
- **可追溯可审计**：`data/skills-ledger.json` 台账（每技能全决策历史）+ `data/audit-log.jsonl`（**只追加永不改写**，含 user_confirmed 位）
- **单个 + 批量双模式**：单命令或 `ledger.py batch <file>`；批量前支持 `--dry-run`

## 数据来源与致谢

| 资源 | 用途 | 出处 |
|---|---|---|
| NCBI E-utilities / BLAST / IgBLAST | 序列检索与采集 | ncbi.nlm.nih.gov |
| UniProt REST | 蛋白注释 | uniprot.org |
| RCSB PDB / AlphaFold DB | 结构获取 | rcsb.org / alphafold.ebi.ac.uk |
| SAbDab2 及其 AI/ML 训练集 | 抗体-抗原结构与 split | Capel et al. 2026, bioRxiv doi:10.64898/2026.06.16.732554；数据 Zenodo 20083995 (CC-BY 4.0) |
| CoVAbDab / OAS | 抗体序列库 | OPIG (opig.stats.ox.ac.uk) |
| ANARCII | 抗体编号（transformer，原生 VNAR 模型） | github.com/oxpig/ANARCII (BSD-3) |
| MMseqs2 / HMMER / Foldseek / MEME Suite | 序列/结构检索与 motif | 各官方发行渠道 |
| nature-skills | 收编 20 项 | github.com/Yuan1z0825/nature-skills (Apache-2.0) |

## 扩展指南

- **新增执行技能**：走 skill-manager 流程，或手动复制 `templates/skill-template/` → frontmatter 写触发条件 → workflow.yaml `stages` 注册 → plugin.json keywords 补触发词 → `ledger.py add` 登记。
- **接入新 MD 引擎**：在 md-simulation-workflow/references/md-engine-comparison.md 注册档位即可，编排层零改动。
- **共享约定**：官方工具优先（手写脚本先与官方输出比对）；完成判定认终结标记不信文件存在性；所有参数标实证来源；每项目独立 handoff。

## 版本

- **0.4.0** (2026-09-20)：新增 skill-manager 技能生命周期管理模块（半自动生成→对比三选一→台账+审计，单个/批量双模式，44 项技能全部入账）。
- **0.3.0** (2026-09-20)：收编 nature-skills 全部 20 项（description 双语化）；新增多 IDE/桌面 agent 适配器 `install.sh`；移除平台绑定的 world-threads-entry。
- **0.2.0** (2026-09-20)：收编科研全链路 20 项技能（4 项加边界声明），workflow.yaml 注册 6 个全链路阶段。
- **0.1.1** (2026-09-20)：数据采集板块（通用库+抗体-抗原库+SAbDab2 本地缓存）；ANARCII 编号规范；内网地址脱敏。
- **0.1.0** (2026-09-20)：初版骨架，4 技能+工作流配置+扩展模板。

## 许可

插件自研部分仅供科研使用。收编部分沿用其原始许可（nature-skills 为 Apache-2.0，其余按各自发布条款；上游署名保留于各技能目录内）。引用本插件协议时请同时引用对应上游工具与数据库（见致谢表）。
