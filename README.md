# Academic Skills and Plugin Development

[English](README_EN.md) | 简体中文

面向科研与蛋白质药物设计的 **Agent Skills 插件开发仓库**。核心产出为 [protein-drug-design-plugin/](protein-drug-design-plugin/)——一个 44 技能的全链路科研技能插件；同时沉淀本仓库的安全开发基建（敏感信息三层防线）。

## 仓库结构

```text
Academic-skills-and-plugin-development/
├── protein-drug-design-plugin/   # ★ 核心插件（44 技能，双语 README，安装即用）
│   ├── README.md / README_EN.md  #    插件完整文档（技能清单/工作流/多 IDE 安装）
│   ├── install.sh                #    一键适配 Trae/Claude Code/Codex/Cursor 等 8 类工具
│   └── skills/                   #    44 项技能
├── scripts/
│   ├── secret-scan.py            # 本地 pre-commit 敏感信息扫描器
│   └── secret-scan-ci.py         # CI 服务端强制扫描（含全历史 blob 扫描）
└── .github/workflows/secret-scan.yml
```

## 核心插件：protein-drug-design（44 技能）

- **计算主线**（4 项自研，实证固化）：序列/结构鉴定 → AF3 结构预测与批量分析 → 分子动力学（AMBER 主力）→ 结合能与机制深化
- **管理**：skill-manager（技能生命周期：添加/合并/下架 + 台账审计）
- **全链路**（39 项收编）：文献调研、研究构思、实验设计、统计分析、学术写作、论文审查、成果展示（PPT/视频/配图/专利/实验日志）

快速安装（详见[插件 README](protein-drug-design-plugin/README.md)）：

```bash
git clone https://github.com/RuijinHospitalVNAR/Academic-skills-and-plugin-development.git
cd Academic-skills-and-plugin-development/protein-drug-design-plugin
bash install.sh trae     # 或 claude / codex / cursor / windsurf / opencode / openclaw
```

## 安全开发基建（本仓库实践）

本仓库经历过一次完整的泄漏整改（历史重写 + 密钥轮换），并据此建立了可复用的三层防线：

| 防线 | 工具 | 挡住什么 |
|---|---|---|
| 文件级 | `.gitignore` | 密钥/凭证类文件被 add |
| 本地内容级 | `scripts/secret-scan.py`（pre-commit 钩子） | commit 时的 token/私钥/IP/本机路径泄漏 |
| 服务端强制 | `scripts/secret-scan-ci.py`（GitHub Actions） | `--no-verify` 绕过 + **全历史 blob 夹带** |

扫描规则：私钥块、GitHub/OpenAI/AWS/Slack/HuggingFace/Google token、硬编码凭证、公网 IP（本地段与版本号豁免）、本机用户/数据路径。两份扫描器同规则库，修改须同步。

## 许可

插件自研部分供科研使用；收编技能沿用各自原始许可（详见[插件 README 致谢表](protein-drug-design-plugin/README.md#数据来源与致谢)）。
