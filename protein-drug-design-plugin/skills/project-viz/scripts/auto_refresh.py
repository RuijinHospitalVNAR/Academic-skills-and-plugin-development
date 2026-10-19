#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_refresh.py — handoff 进度图自动核对与刷新（供 git hook 调用）

解决的问题: handoff 更新后忘记跑 handoff_gantt.py --inplace, 导致 PROGRESS-VIZ 图与文字脱节。

逻辑（确定性核对，不依赖 mtime）:
  1. 扫描 repo 下全部 handoff*.md（.git 内除外；handoff 是本地文件, git 不追踪, 故用 rglob）
  2. 对每个文件: 解析轮次标题数 vs PROGRESS-VIZ 区内事件行数
  3. 缺块或计数不一致 → 重跑 handoff_gantt.py --inplace 刷新
  4. 可选 --pipeline: 若 workflow.yaml 有 git 暂存变更 → 重新生成 docs/pipeline-viz.md
     并 git add（供 pre-commit 调用, 让入库的管线图永不落后于 workflow.yaml）

用法:
  auto_refresh.py --repo <path>                    # handoff 核对刷新 (post-commit 用)
  auto_refresh.py --repo <path> --pipeline         # 追加管线图刷新 (pre-commit 用)

退出码恒 0: 图表同步是增强功能, 失败只告警, 绝不阻塞提交。
输出: 无需动作时静默; 有刷新时逐行打印（供 hook 转示用户）。
"""
import re
import subprocess
import sys
from pathlib import Path

# 与 handoff_gantt.py 同目录
sys.path.insert(0, str(Path(__file__).resolve().parent))
from handoff_gantt import parse, VIZ_BEGIN, VIZ_END, build_timeline  # noqa: E402

EVENT_LINE = re.compile(r"^\s{4}\d{4}-\d{2}-\d{2}\s*:")


def chart_event_count(text):
    """PROGRESS-VIZ 区内的 timeline 事件行数（无块返回 -1）"""
    m = re.search(re.escape(VIZ_BEGIN) + r"(.*?)" + re.escape(VIZ_END), text, flags=re.S)
    if not m:
        return -1
    return sum(1 for ln in m.group(1).splitlines() if EVENT_LINE.match(ln))


def refresh_handoffs(repo, actions):
    script = Path(__file__).resolve().parent / "handoff_gantt.py"
    for hf in sorted(Path(repo).rglob("handoff*.md")):
        if ".git" in hf.parts:
            continue
        try:
            text = hf.read_text(encoding="utf-8")
        except OSError as e:
            actions.append(f"warn: 读取失败 {hf.name}: {e}")
            continue
        n_rounds, n_chart = len(parse(str(hf))), chart_event_count(text)
        if n_rounds == 0 or n_rounds == n_chart:
            continue
        r = subprocess.run([sys.executable, str(script), str(hf), "--inplace"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            actions.append(f"进度图已刷新: {hf.name} ({n_rounds} 轮, 原图 {n_chart})")
        else:
            actions.append(f"warn: 刷新失败 {hf.name}: {r.stderr.strip()[:120]}")


def refresh_pipeline(repo, actions):
    """workflow.yaml 有暂存变更时, 重新生成 docs/pipeline-viz.md 并 git add"""
    staged = subprocess.run(["git", "-C", str(repo), "diff", "--cached", "--name-only"],
                            capture_output=True, text=True).stdout.split()
    wy = "protein-drug-design-plugin/workflow.yaml"
    if wy not in staged:
        return
    flow = Path(__file__).resolve().parent / "workflow_flow.py"
    out = Path(repo) / "protein-drug-design-plugin" / "docs" / "pipeline-viz.md"
    if not out.exists():
        return
    r = subprocess.run([sys.executable, str(flow), str(Path(repo) / wy), "--inplace", str(out)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        subprocess.run(["git", "-C", str(repo), "add", str(out)], check=False)
        actions.append(f"管线图已随 workflow.yaml 刷新并暂存: docs/pipeline-viz.md")
    else:
        actions.append(f"warn: 管线图刷新失败: {r.stderr.strip()[:120]}")


def main():
    repo = Path(sys.argv[sys.argv.index("--repo") + 1]) if "--repo" in sys.argv else Path.cwd()
    actions = []
    try:
        refresh_handoffs(repo, actions)
        if "--pipeline" in sys.argv:
            refresh_pipeline(repo, actions)
    except Exception as e:  # 增强功能绝不阻塞
        actions.append(f"warn: auto_refresh 异常: {e}")
    if actions:
        print("\n".join(actions))
    sys.exit(0)


if __name__ == "__main__":
    main()
