# Academic Skills and Plugin Development

[English](README_EN.md) | 简体中文

面向科研与蛋白质药物设计的 **Agent Skills 插件开发仓库**。核心产出为 [protein-drug-design-plugin/](protein-drug-design-plugin/)——一个 44 技能的全链路科研技能插件。

## 仓库结构

```text
Academic-skills-and-plugin-development/
├── protein-drug-design-plugin/   # ★ 核心插件（44 技能，双语 README，安装即用）
│   ├── README.md / README_EN.md  #    插件完整文档（技能清单/工作流/多 IDE 安装）
│   ├── install.sh                #    一键适配 Trae/Claude Code/Codex/Cursor 等 8 类工具
│   └── skills/                   #    44 项技能
└── scripts/                      # 维护脚本
```

## 核心插件：protein-drug-design（44 技能）

- **计算主线**（4 项自研，实证固化）：序列/结构鉴定 → AF3 结构预测与批量分析 → 分子动力学（AMBER 主力）→ 结合能与机制深化
- **管理**：skill-manager（技能生命周期：添加/合并/下架 + 台账审计）
- **全链路**（39 项收编）：文献调研、研究构思、实验设计、统计分析、学术写作、论文审查、成果展示（PPT/视频/配图/专利/实验日志）

**零命令安装**：不想敲命令？把[这段提示词](protein-drug-design-plugin/agent-install.md)复制给你的 AI 助手，它会自动完成安装。

手动快速安装（详见[插件 README](protein-drug-design-plugin/README.md)）：

```bash
git clone https://github.com/RuijinHospitalVNAR/Academic-skills-and-plugin-development.git
cd Academic-skills-and-plugin-development/protein-drug-design-plugin
bash install.sh trae     # 或 claude / codex / cursor / windsurf / opencode / openclaw
```

## 许可

插件自研部分供科研使用；收编技能沿用各自原始许可（详见[插件 README 致谢表](protein-drug-design-plugin/README.md#数据来源与致谢)）。
