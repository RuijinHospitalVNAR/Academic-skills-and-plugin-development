# 蛋白质药物设计技能插件 (protein-drug-design)

基于他山科研平台框架搭建的领域技能插件。四个技能覆盖蛋白质药物设计核心链路：
**序列/结构鉴定 → AI 结构预测与批量分析 → 分子动力学验证 → 结合能与机制深化**。

## 目录结构

```text
protein-drug-design-plugin/
├── .trae-plugin/plugin.json          # 插件清单 (入口声明, "skills": "./skills/")
├── workflow.yaml                     # 工作流编排配置 (阶段/数据契约/扩展点/约定)
├── README.md                         # 本文件
├── templates/
│   └── skill-template/SKILL.md.tmpl  # 新技能骨架模板 (扩展入口)
└── skills/
    ├── seq-struct-analysis/          # 序列-结构分析流水线
    │   ├── SKILL.md
    │   └── references/
    │       ├── tool-matrix.md        #   BLAST/Jackhmmer/MMseqs2/Foldseek/MEME 选型矩阵
    │       └── pipeline-playbook.md  #   三步定案法命令手册 (A9 案例)
    ├── structure-prediction-analysis/ # 结构预测批量部署与结果分析 (已集成, 内容未改动)
    │   └── SKILL.md
    ├── md-simulation-workflow/       # 分子动力学全流程 (AMBER 主力)
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── md-engine-comparison.md   # AMBER/GROMACS/NAMD/CHARMM/OpenMM 调研与决策树
    │   │   ├── amber-protocol-playbook.md # S1→S8 协议手册 (参数化/构建/平衡/生产/分析/CpHMD/QM/MM)
    │   │   └── analysis-and-pitfalls.md   # 收敛判据体系 + 伪影排查手册
    │   └── templates/                    # 标准 mdin 模板 (min/heat/equil/prod NPT+NVT)
    └── protein-design-workflow/      # 端到端工作流编排器 (路由层+扩展接口)
        └── SKILL.md
```

## 技能清单

| 技能 | 类型 | 来源 |
|---|---|---|
| `protein-design-workflow` | 新建（编排层） | 本插件设计 |
| `seq-struct-analysis` | 新建 | 固化自 A9 尿酸酶家族鉴定实证（BLAST/Foldseek/MMseqs2 三重证据定案） |
| `structure-prediction-analysis` | **集成**（原样保留） | 用户已有技能（AF3/Protenix/OpenDDE 批量 + 双轴四象限分析） |
| `md-simulation-workflow` | 新建 | 固化自 A9 MD/QM/MM/CpHMD + 48 体系 500-769ns 实证；含五引擎调研 |

他山科研插件（tashan-research-skills）**保留不动**，后续按需逐步修改；两插件并行无冲突。

## 工作流总览

```text
FASTA ──[seq-struct-analysis]──> 家族归属+结构锚点
   └──[structure-prediction-analysis]──> model.cif+置信度 ──> 四象限/口袋分析
          └──[md-simulation-workflow]──> prmtop(守卫) ──> 轨迹+收敛 ──> ΔG±SEM/机制
```

阶段契约、算力排期基线与扩展点注册表见 [workflow.yaml](workflow.yaml)。

## 安装使用

1. **源码态（当前）**：技能内容以绝对路径引用本机资产（<LOCAL_SCRIPTS_DIR>、<AMBER_HOME> 等），在本机已可直接工作；
2. **作为插件安装**：将本目录放入 `~/.trae-cn/plugins/<registry>/protein-drug-design/<version>/`（或由市场打包），重启后技能自动注册——description 进入系统提示，按触发词按需加载；
3. **跨机迁移注意**：SKILL.md 中 ⚠️ 标记的本机路径（Amber22、远端 rcdb 服务器、GPU UUID）需按目标机改写。

## 扩展指南

- **新增执行技能**：复制 `templates/skill-template/` → `skills/<新技能名>/`，写 frontmatter（name + description 只写触发条件）→ 在 workflow.yaml `stages` 注册 → plugin.json keywords 补触发词。
- **接入新 MD 引擎**：在 md-simulation-workflow/references/md-engine-comparison.md 注册档位即可，编排层零改动。
- **修改既有技能**：改 SKILL.md 前先跑基线场景（无该技能时 agent 如何犯错），改后重测是否遵守（TDD for skills）。

## 共享约定（全技能强制）

1. 官方工具优先；手写脚本须先与官方输出语义比对确认无 bug 再运行。
2. 完成判定只认终结标记（.out STOP/Final），不信文件存在性；改算法/续跑必失效全部层级缓存。
3. 所有参数与判据标注实证来源；未实证项标 ⚠️。
4. 每个项目独立 handoff.md，跨任务不混写。

## 版本

- 0.1.0 (2026-09-20)：初版骨架。四技能 + 工作流配置 + 扩展模板。
- 0.1.1 (2026-09-20)：seq-struct-analysis 更新——jackhmmer 选型（AF3 原生 MSA 路线 vs MMseqs2 快筛）、MME 澄清为 MEME（motif 发现）、内网地址脱敏（占位符 <REMOTE_HOST>:<REMOTE_PORT>）。同步 GitHub: RuijinHospitalVNAR/Academic-skills-and-plugin-development。

## 相关仓库

- 上游开发仓库：<https://github.com/RuijinHospitalVNAR/Academic-skills-and-plugin-development>（本插件在此仓库 protein-drug-design-plugin/ 子目录下持续开发）
