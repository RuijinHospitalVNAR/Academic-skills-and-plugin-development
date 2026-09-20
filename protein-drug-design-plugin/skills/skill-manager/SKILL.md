---
name: skill-manager
description: 本插件技能生命周期管理器：添加/合并/下架 skills 的半自动流程与审计台账。Use when 用户要往插件加新技能（从踩坑/重复操作/新方法中沉淀）、要把新技能与现有技能对比决定吸收/合并/拒绝、要下架效果不佳或过时的技能、要查看技能台账/审计日志/批量管理技能，或用户说"把这个经验做成技能""哪些技能没用了""清理插件技能"时。EN: Lifecycle manager for plugin skills — semi-automatic add/merge/remove with auditable ledger, batch & single modes. Keywords: 技能管理、添加技能、删除技能、合并技能、技能台账、skill lifecycle、skill manager、ledger。
---

# Skill Manager（插件技能生命周期管理）

管理本插件 43+ 技能的**添加 / 合并 / 下架**，全流程可追溯可审计。
构建基础：superpowers:writing-skills（TDD for skills）+ skill-criticagent（评估口径）+ 插件模板 templates/skill-template。

## 0. 三种模式

| 模式 | 入口 | 用户交互 |
|---|---|---|
| **ADD**（半自动生成→吸收/合并/拒绝） | 用户提出 / 工作中发现重要问题 / 周期审计 | 关键决策点必问用户 |
| **REMOVE**（识别并下架） | 用户指令 / 效果审计 / 过时判定 | 下架前确认 |
| **AUDIT**（台账与一致性） | 任意时刻 | 无 |

## 1. ADD 流程（五步）

```text
S1 信号采集 → S2 草案生成 → S3 对比分析 → S4 三选一决策(用户确认) → S5 登记+装机
```

**S1 信号采集**（什么值得做成技能——满足任一）：
- 同一问题被解决 ≥2 次（踩坑手册化价值）
- 一次解决但代价大（排错 >1h / 涉及多轮验证）
- 用户明确说"记住这个/以后都这么做/做成技能"
- 新工具/新库的完整使用协议（含坑）

**S2 草案生成**（半自动）：复制 `templates/skill-template/SKILL.md.tmpl` → 填 frontmatter（description 只写触发条件+双语）→ 正文写流程/坑/产出清单。
**主动向用户提问**（AskUserQuestion，缺一不可跳过）：
1. 触发场景边界（什么任务该触发/不该触发——决定 description 措辞）
2. 语言（默认中文正文+EN: 摘要）
3. 是否有实证出处可标注（provenance）

**S3 对比分析**：`python3 scripts/compare.py <候选目录>` → 得 desc_jaccard / body_overlap / 共享触发词 + 自动建议。

**S4 三选一决策**（阈值详见 [references/decision-criteria.md](references/decision-criteria.md)）：

| compare 结果 | 决策 | 动作 |
|---|---|---|
| top 相似度 < 0.20 | **ABSORB 吸收** | 新建目录 → S5 |
| 0.20-0.45 或职责同域 | **MERGE 合并** | 把新内容并入现有技能对应章节（加 changelog 行），**不新建目录** → `ledger.py merge` |
| ≥0.45 或域外/一次性问题 | **REJECT 拒绝** | 记录拒绝理由到 audit log，不加入 |

MERGE/REJECT 边界判断 AI 可给建议，**最终由用户确认**（半自动原则）。

**S5 登记+装机**：
```bash
python3 scripts/ledger.py add <name> --source "<来源>" --reason "<决策理由>" \
  --compare-report data/compare-last.json --user-confirmed
# 手动补: plugin.json keywords; workflow.yaml stages 注册; bash install.sh trae 装机
```

## 2. REMOVE 流程（四步）

**识别信号**（任一）：
- 台账 trigger_notes 长期记录"低触发/被边界声明拦走"
- 依赖的平台/工具已下线（先例：world-threads-entry）
- 用户明确指令
- 内容过时（协议与当前工具版本严重不符且无人维护更新）

**流程**：列证据 → 用户确认 → `python3 scripts/ledger.py remove <name> --reason "<理由>" --user-confirmed`（自动：tar 备份→删插件目录→删用户级目录→清 workflow.yaml 引用→台账标记 removed→审计日志）。试探先加 `--dry-run`。

## 3. AUDIT 与批量

```bash
python3 scripts/ledger.py status -v     # 台账总览 + 磁盘一致性检查
python3 scripts/ledger.py audit -n 30   # 审计日志尾部（每次操作: 时间/操作/对象/理由/用户确认位）
# 批量（文件每行一条）:
cat > batch.txt <<'E'
remove some-old-skill --reason 平台下线
add new-skill --source 手动 --reason 零重叠吸收
E
python3 scripts/ledger.py batch batch.txt
```

## 4. 铁律

- 审计日志 data/audit-log.jsonl **只追加不改写**；台账 remove 是状态标记非物理删除记录。
- 每次批量操作前 `--dry-run` 或先 `status` 核对；批量文件保留在 data/ 归档。
- 新技能若未过 S4 用户确认，禁止 add（--user-confirmed 是自证位，AI 不得在用户未答时虚标）。
- 技能目录移动物理文件仅限 ledger.py 执行（防手滑绕过台账）。

## 5. 产物

```text
data/skills-ledger.json     台账（每技能: status/source/provenance/decisions[]/merges）
data/audit-log.jsonl        审计日志（只追加）
data/compare-last.json      最近一次对比报告
data/removed-backup/        下架技能 tar 备份
merged-away/                被合并技能的归档目录
```
