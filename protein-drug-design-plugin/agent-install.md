# 让 AI Agent 帮你安装本插件

不想手动敲命令？把下面这段话**整段复制**给你正在使用的 AI 编程助手（Trae / Claude Code / Codex CLI / Cursor / Windsurf 等），它会自动完成安装：

## 中文版提示词（复制以下全部内容）

```text
请帮我安装蛋白质药物设计技能插件（protein-drug-design）。请严格按以下步骤执行，每步完成后向我报告结果再进行下一步：

1. 克隆仓库：
   git clone https://github.com/RuijinHospitalVNAR/Academic-skills-and-plugin-development.git /tmp/pdd-plugin
   （若 /tmp 不可写，改克隆到我的家目录下 ~/.pdd-plugin）

2. 检测你自身是哪个 agent（按我当前使用的工具判断）：
   - Trae CN → 目标 "trae"
   - Claude Code → "claude"
   - Codex CLI → "codex"
   - Cursor → "cursor"
   - Windsurf → "windsurf"
   - OpenCode → "opencode"
   - 其他/不确定 → "generic"
   如果无法确定，先问我再用对应目标。

3. 运行安装器（把 <target> 换成第 2 步的结果）：
   bash /tmp/pdd-plugin/protein-drug-design-plugin/install.sh <target>

4. 验证安装：列出目标技能目录下是否存在这 4 个核心技能目录：
   seq-struct-analysis、structure-prediction-analysis、md-simulation-workflow、protein-design-workflow

5. 报告：安装了多少个技能、装到了哪个目录、我需要重启会话/IDE 才能生效。

注意：
- 如果第 3 步输出提示 Cursor/Windsurf 需要把指向行加入项目 rules，请把那一行原文转告我。
- 不要修改插件内任何文件；不要把 skills 目录装到项目目录。
```

## English prompt (copy everything below)

```text
Please install the protein-drug-design skills plugin for me. Execute these steps strictly, reporting each result to me before proceeding:

1. Clone the repo:
   git clone https://github.com/RuijinHospitalVNAR/Academic-skills-and-plugin-development.git /tmp/pdd-plugin
   (if /tmp is not writable, clone to ~/.pdd-plugin instead)

2. Detect which agent you are running in (based on the tool I am using right now):
   - Trae CN -> target "trae"
   - Claude Code -> "claude"
   - Codex CLI -> "codex"
   - Cursor -> "cursor"
   - Windsurf -> "windsurf"
   - OpenCode -> "opencode"
   - other / unsure -> "generic"
   If you cannot determine it, ask me first.

3. Run the installer (replace <target> with the step-2 result):
   bash /tmp/pdd-plugin/protein-drug-design-plugin/install.sh <target>

4. Verify: check that these 4 core skill directories exist in the target skill directory:
   seq-struct-analysis, structure-prediction-analysis, md-simulation-workflow, protein-design-workflow

5. Report: how many skills were installed, into which directory, and that I need to restart the session/IDE for them to take effect.

Notes:
- If step 3 prints a rules pointer line for Cursor/Windsurf, relay that line to me verbatim.
- Do not modify any plugin files; do not install the skills into a project directory.
```

## 原理说明

Agent Skills 规范（agentskills.io）下，安装本质就是“把 `skills/` 各目录放到对应工具的技能目录”——`install.sh` 已封装 8 类工具的路径差异，提示词只是引导 agent 完成克隆→自检身份→调用→验证的闭环。装完后新会话即可用自然语言触发，例如：“用 md-simulation-workflow 帮我搭一个 100ns 的 AMBER 体系”。
