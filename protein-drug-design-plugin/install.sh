#!/usr/bin/env bash
# ============================================================================
# protein-drug-design 插件 · 多 Agent 安装适配器 (install.sh)
# 用法:  bash install.sh [agent]        # agent 缺省 = list
# 示例:  bash install.sh trae         # Trae / Trae CN
#        bash install.sh claude       # Claude Code
#        bash install.sh codex        # OpenAI Codex CLI
#        bash install.sh cursor       # Cursor
#        bash install.sh windsurf     # Windsurf
#        bash install.sh opencode     # OpenCode
#        bash install.sh openclaw     # OpenClaw / 桌面 agent (agent-skills 规范)
#        bash install.sh generic      # 通用: 只把 skills/ 摆到 ~/.agents/skills
#        bash install.sh list
#
# 原理: Agent Skills 规范 (agentskills.io) 已被主流 IDE/CLI 采纳——所有目标都是
# "把 skills/<name>/SKILL.md 放到该工具扫描的技能目录"。差异只在目录位置:
#   Trae:            ~/.trae-cn/skills/            (CN) | ~/.trae/skills/ (intl)
#   Claude Code:     ~/.claude/skills/
#   Codex CLI:       ~/.codex/skills/  (或 $CODEX_HOME/skills)
#   Cursor/Windsurf: 无原生 skills 目录 → 用 ~/.agents/skills/ (跨工具通用位置,
#                    配合其 rules 机制指向; 或直接放项目根 .agents/skills/)
#   OpenCode:        ~/.config/opencode/skills/
#   OpenClaw 等:     ~/.agents/skills/  (openai agents skills 规范默认)
# ============================================================================
set -euo pipefail
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$PLUGIN_DIR/skills"

list() {
  cat <<'EOF'
支持目标:
  trae       Trae / Trae CN        -> ~/.trae-cn/skills (或 ~/.trae/skills)
  claude     Claude Code           -> ~/.claude/skills
  codex      OpenAI Codex CLI      -> ~/.codex/skills ($CODEX_HOME)
  cursor     Cursor                -> ~/.agents/skills + 项目 rules 提示
  windsurf   Windsurf              -> ~/.agents/skills + 项目 rules 提示
  opencode   OpenCode              -> ~/.config/opencode/skills
  openclaw   OpenClaw/桌面 agent   -> ~/.agents/skills
  generic    通用                  -> ~/.agents/skills
  list       显示本帮助
EOF
}

install_to() {  # $1=目标目录  $2=工具名
  local dest="$1" tool="$2"
  [ "${1:-}" = "list" ] && { list; exit 0; }
  mkdir -p "$dest"
  local n=0
  for d in "$SRC"/*/; do
    [ -f "$d/SKILL.md" ] || continue
    rm -rf "$dest/$(basename "$d")"
    cp -r "$d" "$dest/"
    n=$((n+1))
  done
  echo "[$tool] 已安装 $n 个技能 -> $dest"
  echo "[$tool] 重启/新会话后生效; 用该工具内询问技能列表或直接下触发词任务验证。"
}

case "${1:-list}" in
  trae)
    if [ -d "$HOME/.trae-cn" ]; then install_to "$HOME/.trae-cn/skills" "Trae CN"
    elif [ -d "$HOME/.trae" ]; then install_to "$HOME/.trae/skills" "Trae"
    else install_to "$HOME/.trae-cn/skills" "Trae CN"; fi ;;
  claude)   install_to "$HOME/.claude/skills" "Claude Code" ;;
  codex)    install_to "${CODEX_HOME:-$HOME/.codex}/skills" "Codex CLI" ;;
  cursor)   install_to "$HOME/.agents/skills" "Cursor(via agents-skills)"
            cat <<'EOF'
  [Cursor 追加提示] Cursor 无原生技能加载; 两种用法:
   (1) 已装社区扩展支持 agents-skills 的话直接生效;
   (2) 否则在项目 .cursorrules / Settings>Rules 加一行:
       "任务匹配时先读 ~/.agents/skills/<skill-name>/SKILL.md 再执行 (可用技能: 见该目录)"
EOF
            ;;
  windsurf) install_to "$HOME/.agents/skills" "Windsurf(via agents-skills)"
            echo "  [Windsurf 追加提示] 在 Cascade > Rules 中加入与 Cursor 相同的指向行。"
            ;;
  opencode) install_to "$HOME/.config/opencode/skills" "OpenCode" ;;
  openclaw|generic) install_to "$HOME/.agents/skills" "OpenClaw/generic(agents-skills 规范)" ;;
  *) list ;;
esac
