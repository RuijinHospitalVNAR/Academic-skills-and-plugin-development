---
name: periodic-review
description: 跨项目周期性回顾技能（周/月/季/年）。当用户说「周回顾」「月回顾」「季度回顾」「年度回顾」，或要求聚合各项目 handoff 进展、生成跨项目状态矩阵、盘点跨项目风险与 GPU 资源时使用。扫描全部 handoff-*.md 最新条目，按模板生成周报（reviews/weekly/YYYY-Www.md）；自动聚合区由 agent 填写，决策区由用户批注；最新周报的「本周优先级」是后续对话的默认行动序。与 handoff 全局规则配套：handoff 管项目内跨对话传递，本技能管跨项目推进。
metadata: {"skillKey":"periodic-review","userInvocable":true}
---

# Periodic Review（跨项目周期性回顾）

为多线并行的科研工作区（抗体设计 / 基因组分析 / 文章撰写 / plugin 开发）提供日/周/月/季/年五层回顾。
本技能是**元工作流**技能（与 research-dream、cognitive-profile 同类），不属于蛋白设计主流水线，
不注册进 workflow.yaml stages。

## 三条设计原则（任何执行不得违背）

1. **单一事实源不破坏** — 项目真相在各项目 `handoff-*.md`；本技能只生成聚合视图与决策记录，禁止双写项目状态。
2. **机器聚合，用户决策** — 自动聚合区 agent 填；决策区（本周优先级/冻结栏）用户批注，可口头、agent 代填。
3. **产物必须被消费** — 最新周报的「本周优先级」= agent 后续对话的**默认行动序**，与新指令冲突时先问用户。

## 层级与触发

| 层 | 触发词 | 产物位置 | 状态 |
|----|--------|----------|------|
| 日 | 「日审核」 | `reviews/daily_audit/reports/YYYY-MM-DD/audit.md`（cron 03:00 自动生成） | 已启用（2026-11-11 静态审计层） |
| 周 | 「周回顾」 | `reviews/weekly/YYYY-Www.md`（ISO 周号，周一~周日） | 已启用 |
| 月 | 「月回顾」 | `reviews/monthly/YYYY-MM.md` | 规划中 |
| 季 | 「季度回顾」 | `reviews/quarterly/YYYY-Qn.md` | 规划中 |
| 年 | 「年度回顾」 | `reviews/annual/YYYY.md` | 规划中 |

机制说明与状态登记：`<WORKSPACE_ROOT>/reviews/README.md`。首次启用某层前先建目录+模板（仿 weekly 模式）并回写 README。

## 周回顾执行程序（触发时严格照做）

1. **盘点 handoff**：glob `<WORKSPACE_ROOT>/handoff-*.md` + `<WORKSPACE_ROOT>/*/handoff-*.md` + `<WORKSPACE_ROOT>/*/*/handoff-*.md`
   （覆盖 AF3_prediction/A9_Multimer/A9_UricAcid 等深层）；pdd-plugin 双副本合并为一行。
2. **逐份提取最新状态**：先 `stat` mtime 定活跃度，再按文件条目排序方向读尾段/头段；
   每份提取四项 = 最新日期 / 当前状态一句话 / 下一步 / 阻塞。mtime 只是线索，**内容才是真相**。
3. **资源状态**：`nvidia-smi` 查在位卡与利用率，GPU 台账以 project_memory「GPU FLEET」权威行为准（2026-10-25 8 卡新秩序，勿引用更早的禁用记录；启动前核实+按 UUID 绑定为不变量）；检查 watchdog 与长任务状态；**汇总本周 daily_audit 报告**（`reviews/daily_audit/reports/*/audit.md`）的 findings 计数与新异常，命中≠错误，异常项列风险区。
4. **生成周报**：严格用 `reviews/weekly/_template.md` 栏目；状态矩阵按活跃度降序，停滞 ≥2 周标 ⚠。
5. **风险交叉核对**：上一期周报风险区逐条闭环或滚动；对任何声称"已记录 handoff"的结论做落盘验证
   （grep 关键词到具体文件），发现缺口先补记再进报告。
6. **等用户批注**决策区（Top-1/2/3、冻结项）后归档；用户未批注前周报保持草稿态。

## 月/季/年层启用时的额外动作

- **月**：月初计划兑现率对照；lessons-learned 升格检查（重复出现的教训升格为 project_memory 硬约束）。
- **季**：四条工作线各选一个"发表/交付锚点"评估距离；输出冻结名单（含理由）。
- **年**：学术产出盘点（论文/专利/工具）对照长期目标。

## 已知坑（2026-W42 首期审计实证，勿重蹈）

- **"已记录 handoff"的声称可能未落盘** — 必须验证（cartfish 2026-10-15 案例：两条演化结论声称已记录，实际缺失）。
- **handoff 迁移/改名可能留缺口** — 项目内容出现在错误 handoff 时：先 grep 目标 handoff 确认无副本，
  再原样迁移（一字不改），行数守恒校验，备份留 /tmp（2026-10-16 迁移缺口修复案例：8 条 GPCR 条目残留 cartfish 文件）。
- **描述性"下一步"长期无排期** — 停滞 ≥4 周的项目在周报中显式提示用户决策：纳入排期或显式冻结。

## 完成标准

- 周报已落盘且决策区获得用户批注（或用户明确表示暂不批注）。
- 上期风险逐条有闭环状态（解决/滚动/显式放弃）。
- 本轮修复的任何 handoff 缺口，修复动作本身记入当期周报风险区。
