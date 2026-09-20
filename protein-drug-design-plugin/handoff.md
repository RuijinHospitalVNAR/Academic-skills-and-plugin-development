# Handoff — protein-drug-design 插件项目

> 本文件为插件项目专属交接记录（2026-09-20 起），不与其他项目混写。
> 素材来源（只读引用，不修改源项目）：
> - A9 尿酸酶项目：<A9_PROJECT_DIR>/handoff.md
> - SH3/HCG MD 趋势：<MD_PROJECT_DIR>/handoff.md
> - GPCR 抗体设计（structure-prediction-analysis 技能出处）：<GLOBAL_HANDOFF>

## 已完成 (2026-09-20)

1. **插件骨架** <PLUGIN_DIR>/（他山框架格式）：
   - .trae-plugin/plugin.json（v0.1.0，name/displayName/description 中英 + i18n + 16 keywords + "skills": "./skills/"）
   - workflow.yaml：五阶段（family-identification → structure-acquisition → structure-analysis → md-validation → binding-energy）阶段契约（inputs/outputs/proven_case）+ 3 个扩展点（new_engine_adapter / new_analysis_tool / alternative_predictor）+ 全技能共享约定
   - README.md：目录结构、技能清单、工作流总览、安装与扩展指南
   - templates/skill-template/SKILL.md.tmpl：新技能骨架模板
2. **技能四件套**（全部通过 frontmatter 校验：name+description 必有，description <1024B，只写触发条件）：
   - structure-prediction-analysis：**集成**（自 <HOME>/.trae-cn/skills/ 原样复制 12565B，含 AF3/Protenix/OpenDDE 批量与双轴四象限全量内容）
   - md-simulation-workflow：**新建**。SKILL.md（引擎选型决策树 + 五阶段流程 + 坑速查）+ 3 references（md-engine-comparison：AMBER/GROMACS/NAMD/CHARMM/OpenMM 五引擎对比与决策树；amber-protocol-playbook：S1→S8 全协议含 BCC/RESP 双路线、三道守卫、CpHMD 三禁、QM/MM SCF 收敛根因律；analysis-and-pitfalls：收敛双判据（核心区 RMSD + 块平均 SEM/10% ΔG 阈值）+ 伪影排查）+ 5 个 mdin 模板（min/heat/equil/prod NPT/prod NVT，参数实证自 A9 C0 系列与 48 体系协议）
   - seq-struct-analysis：**新建**。SKILL.md（三步定案法）+ 2 references（tool-matrix：序列/结构/MSA 三档位矩阵 + 已剔除冗余环节评估 + MME 档位说明；pipeline-playbook：A9 全流程命令手册含 Foldseek mode=3diaa、CIF 残基号坑、基因组上下文仲裁）
   - protein-design-workflow：**新建**（编排层）。任务路由规则、算力排期实证基线表、扩展接入四步法、阶段间检查点
3. **验证**：JSON 语法、四个 SKILL.md frontmatter、workflow.yaml 阶段/扩展点计数——脚本校验全过。

## 关键设计决策

- description 规范：只写"Use when + 触发词"，不总结工作流（防 AI 照 description 捷径跳过正文）。
- 结构预测技能原样集成（用户要求保留）；他山科研插件保留不动，后续逐步修改。
- MD 技能默认 AMBER 主力（本机已验证 + QM/MM/CpHMD 生态），多引擎对比仅作选型与迁移参考，不重复造轮子；OpenMM 细节引用已有 superpowers:molecular-dynamics 技能。
- "MME" 无标准工具定义（检索核实）：在 tool-matrix 中按 MSA 工具与结构对齐两档位双覆盖，标注待用户确认归类。
- 脚本策略遵循用户规则：协议手册以官方工具命令（tleap/cpptraj/MMPBSA.py/cphstats/Foldseek API/mmseqs2）为主，mdin 模板为配置文件级低风险资产；未新增未经验证的可执行脚本。

## 更新 (2026-09-20 第二轮)

1. **MME 澄清（用户确认）**：MME = **MEME**（motif 发现套件）。tool-matrix §3 已收录 MEME(de novo 发现)/FIMO/MAST(扫描) 三行；pipeline-playbook Step4 补 meme/fimo 命令；"待确认 MME"占位行已删除。
2. **Jackhmmer 选型已收录（用户建议采纳，定位为互补而非替换）**：
   - MMseqs2 保留为家族快筛主力（实证 85G 直搜；ColabFold 服务端 MSA 同路线）；
   - jackhmmer 新增为流水线可选步骤 1d——远缘深挖 + AF3 原生 MSA 备料（AF2/AF3 特征管线内置组件，unpairedMsa 语义对齐最稳）；
   - tool-matrix 新增 "Jackhmmer vs MMseqs2 实证选型" 小节（速度/灵敏度/格式兼容三维对比 + 结论）。
3. **IP 脱敏**：同步 GitHub 前将全部内网端点（user@<内网IP>:<端口> 形式）替换为 <REMOTE_HOST>:<REMOTE_PORT> 占位符（structure-prediction-analysis/SKILL.md ×2 处、md-engine-comparison.md ×1 处），grep 验证无字面量残留。真实地址仅存本地项目 handoff，不入库。
4. **GitHub 同步（推送待授权）**：
   - 本地克隆 <GIT_CLONE_DIR>（空仓库, main 分支），插件已复制为 protein-drug-design-plugin/ 子目录；
   - commit 13f6b49 已完成（19 文件, 1225 行, "Add protein-drug-design plugin v0.1.1"）；
   - ⚠️ push 被拒：<OLD_DEPLOY_KEY> 密钥对目标仓库只读（GitHub deploy key 仓库绑定）；
   - 已生成专用密钥对 <DEPLOY_KEY_PATH>（ed25519, 无口令），公钥已交用户添加为该仓库 Deploy key（需勾选 Allow write access）；
   - 用户添加后执行: GIT_SSH_COMMAND="ssh -i <DEPLOY_KEY_PATH> -o IdentitiesOnly=yes" git push -u origin main（在 <GIT_CLONE_DIR> 下）。

## 更新 (2026-09-20 第三轮)

1. **v0.1.1 已推送 GitHub**（main 13f6b49, <DEPLOY_KEY> key 生效）。
2. **数据采集模块补齐（用户指出缺口，采纳）**：新增 references/data-acquisition.md——NCBI E-utilities（efetch 批量 FASTA ≤200/post、esearch→efetch 链、elink→efetch 基因组上下文 A9 操纵子实证链、web BLAST URL API）、UniProt REST（fasta/search/注释字段）、RCSB/AFDB 结构拉取（含网络受限降级方案）、Foldseek 结果落盘、采集规范（manifest/幂等/限速/版本锚定/原文落盘）。SKILL.md 流水线补"步骤1.5 数据采集"、产出清单补 raw/ 目录、触发词补数据下载等；playbook Step1.5/Step3/Step4 接入链接。

## 更新 (2026-09-20 第四轮)

1. **抗体-抗原库采集补齐（用户指出缺口）**：data-acquisition.md 新增 §5"抗体-抗原专用库"——SAbDab(结构+CDR 注释, weekly)/Thera-SAbDab(WHO INN)/CoVAbDab(序列全量 csv)/OAS(天然库 unit 级, TB 级按需)/IMGT germline+IgBLAST(NCBI FTP 稳定端点)/IEDB(REST+全量导出)/AbDb/NanoLAS 备选；OPIG 端点标注 ⚠️ 以站点最新为准（newsabdab 迁移期勿硬编码）；结构本体走 RCSB 避免整包拉取；清洗范式挂接本机 MAGE repo notebook（SAbDab detagging/CoVAbDab curation）；ANARCI 衔接说明。原"采集规范"§5 改 §6，补 raw/antibody/ 分目录规则。SKILL.md 触发词补 sabdab/covabdab/oas/imgt/iedb/igblast 等。
2. 同步 GitHub。

## 更新 (2026-09-20 第五轮)

1. **SAbDab2 本地缓存盘点与文档化（用户指出"zando"清洗库）**：
   - 命名澄清：检索无 "ZANDO" 抗体库；本地数据经文件布局/术语（INSTANCE/TYPE=FAB/SABDABupdate=20260430/pdb_0000xxxx_H_L 命名）比对确认为 **SAbDab2 官方 AI/ML 清洗训练集**（Capel et al. 2026 bioRxiv 10.64898/2026.06.16.732554；Zenodo 20083995，半年更新）。
   - 本地规模：ab/abag_split.csv 各 15,641 行 + _sd 非冗余变体 3,414 行 + 8,846 清洗 cif (1.9GB)；抗原类型 PROTEIN 3698/SUGAR 821/PEPTIDE 734 等。路径 VNAR-antigen-feature-analysis/data/antibody_antigen_complexes/splits/splits_final/。
   - data-acquisition.md：§5.0 新增本地缓存小节（布局+四条守卫：版本锚定防 split 泄漏/链名已标准化/cif 覆盖度过滤/低冗余用 _sd + VNAR 原生 instance type）；选型矩阵 SAbDab→SAbDab2 升级并标训练集为⭐首选；5.1 更新为 sabdab2 新站 + Zenodo 下载（旧 newsabdab 路径删除）。
   - SKILL.md 触发词补 sabdab2，选型表补本地缓存行。
2. 同步 GitHub。

## 更新 (2026-09-20 第七轮)

1. **智能体接入完成（用户指令）**：插件三新技能 (md-simulation-workflow / seq-struct-analysis / protein-design-workflow) 已复制到用户级技能目录 ~/.trae-cn/skills/（frontmatter 校验过），蛋白质药物设计智能体可立即触发；structure-prediction-analysis 原件已在目录，未动。被覆盖的同名 OPIG 英文版 protein-design-workflow 已备份为 protein-design-workflow.bak_opig_20260920。
2. **仓库级双语 README**：撰写 README.md（中文版）+ README_EN.md（English version），含插件简介/技能表/工作流图/安装方式（含智能体接入说明）/数据来源与致谢（OPIG/SAbDab2/Zenodo/ANARCII 等）/许可注记。GitHub 已推送。

## 更新 (2026-09-20 第八轮 · v0.2.0)

1. **全量收编他山科研 20 技能**（用户确认插件定位为蛋白设计+写作全链路，14 项不再视为噪音）：
   - 复制 20 技能入 skills/（总量 24）；备份 <BACKUP_DIR>/tashan-research-skills-backup-20260920.tar.gz (1.7MB)。
   - 4 个触发面冲突技能加边界声明（description 末尾）：experiment-design（MD矩阵排期→protein-design-workflow）、statistical-analysis（MD收敛判据→md-simulation-workflow）、scispark（计算机制深化→md-simulation-workflow）、research-baseline-builder（跨阶段路由→protein-design-workflow）。
   - plugin.json v0.2.0（全链路描述+32关键词）；workflow.yaml 注册 6 个全链路阶段（research-ideation/research-planning/statistical-validation/writing/review/presentation，含 alternatives），stages 总数 11。
2. **卸载他山插件**：官方市场入口无法脚本调用，按兜底路径执行：tar 备份 → rm <HOME>/.trae-cn/plugins/trae-remote-official/tashan-research-skills/ → 清 plugin-config.json 的启用条目 → 清 installed-plugins.json 的市场条目（python json 编辑）。验证：目录不存在+两 json 无 tashan 残留。
3. **智能体目录同步**：20 技能复制到 ~/.trae-cn/skills/（⚠️ statistical-analysis 与全局 K-Dense 英文版同名，K-Dense 版先备份为 statistical-analysis.bak_kdense_20260920 再覆盖；experiment-design(tashan) 与 experimental-design(K-Dense) 不同名不冲突）。
4. 双语 README 更新全链路口径+收编说明；GitHub 推送。

## 下一步计划

1. [ ] 实测触发：插件安装/注册后，用典型请求（"做这个蛋白的 MD"、"A9 是什么家族"）验证技能触发与加载链路。
2. [ ] MME 归类确认（问用户：MSA 工具还是结构对齐？）后修订 tool-matrix。
3. [ ] mdin 模板实测一轮（新小体系跑通 min→prod 链路）后再标"已验证模板"。
4. [ ] 逐步吸收他山科研技能中可复用项（如 research-baseline-builder 的预注册判据模式可挂到 binding-energy 阶段）。
5. [ ] 后续新任务（A9 D2 / MC4R 新一轮设计）的 handoff 继续写各自项目文件；插件本体变更记录到本文件。

## 遇到的问题

- 无阻塞问题。已知事项：(1) 插件内 SKILL.md 引用的本机绝对路径（<AMBER_HOME>、远端 rcdb、GPU UUID）跨机迁移需改写（README 已注明）；(2) <LOCAL_DATA_ROOT> 根目录 LS 工具曾显示为空但实际有子目录（工具枚举上限），素材定位改用 Glob 解决；(3) 本机 IDE Write 桥接对本目录偶发超时，shell heredoc 兜底成功（与 A9 项目历史经验一致）。
