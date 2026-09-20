# 技能吸收/合并/拒绝评估标准

compare.py 阈值（desc_jaccard = description 词集 Jaccard；body_overlap = 正文 bigram 重叠率）：

| top 相似度 | 自动建议 | 人工复核要点 |
|---|---|---|
| < 0.20 且无触发词冲突 | ABSORB | 确认职责确实不同域；避免"数值低但语义同域"（如两个都管"机制分析"） |
| 0.20 – 0.45 | BOUNDARY | 问：用户会同时需要两者吗？合并后 description 是否还能精准触发？ |
| ≥ 0.45 | MERGE | 合并方向：经验并入更成熟的一方（正文更长/实证更多者为主） |

**MERGE 判据补充**（数值之外，任一成立即倾向合并）：
- 同一工作流阶段（workflow.yaml 同 stage）且输入输出契约相同
- 新技能 80% 内容可映射为现有技能的新增章节（如新引擎档位、新工具对比行）
- 两者 description 触发词交集 ≥ 5 个专有词（非停用词）

**REJECT 判据**（任一成立）：
- 一次性问题（环境特定 hack、已修复的 bug 记录）
- 与全局技能目录已有技能重复（~/.claude 或 ~/.trae-cn 下同名/同职责）
- 外部平台深度绑定且无离线价值
- 无法写出可复现触发条件（description 只能写"当用户提到 X"这种过窄触发）

**REMOVE 判据**（任一成立，需用户确认）：
- 平台/工具下线且无替代场景（先例 world-threads-entry 2026-09-20）
- 12 个月零触发 + 零维护提交（台账 trigger_notes 为证）
- 被 3+ 个其他技能的边界声明列为"拦走目标"（信号：职责已被更强技能覆盖）

**审计位说明**：audit-log 每条含 user_confirmed 布尔——AI 代执行日常运维可 false，
但 add（吸收）/remove（下架）/merge 必须为 true（用户已答 AskUserQuestion 或聊天明确同意）。
