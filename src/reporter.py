import csv
import os
from datetime import datetime


def generate_reports(results, csv_path="reports/results.csv", html_path="reports/report.html"):
    """Generate CSV and HTML reports from scored results."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    _write_csv(results, csv_path)
    _write_html(results, html_path)


def _write_csv(results, csv_path):
    fieldnames = [
        "case_id", "category", "prompt", "answer", "passed",
        "score", "reason", "latency_ms", "success", "error",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow({
                "case_id": r["case_id"],
                "category": r["category"],
                "prompt": r.get("prompt", ""),
                "answer": r.get("answer", ""),
                "passed": r.get("passed", False),
                "score": r.get("score", 0),
                "reason": r.get("reason", ""),
                "latency_ms": r.get("latency_ms", 0),
                "success": r.get("success", False),
                "error": r.get("error", ""),
            })


def _write_html(results, html_path):
    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    pass_rate = (passed_count / total * 100) if total > 0 else 0
    avg_latency = sum(r.get("latency_ms", 0) for r in results) / total if total > 0 else 0

    # Category breakdown
    cat_stats = {}
    for r in results:
        cat = r["category"]
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "passed": 0}
        cat_stats[cat]["total"] += 1
        if r.get("passed"):
            cat_stats[cat]["passed"] += 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentEval - AI Agent 自动化评测报告</title>
<style>
  body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; margin: 40px auto; max-width: 1100px; padding: 0 20px; color: #333; }}
  h1 {{ text-align: center; color: #1a1a2e; }}
  .meta {{ text-align: center; color: #888; margin-bottom: 30px; }}
  .summary {{ display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; margin-bottom: 30px; }}
  .summary-card {{ background: #f5f5f5; border-radius: 10px; padding: 20px 30px; text-align: center; min-width: 140px; }}
  .summary-card .value {{ font-size: 32px; font-weight: bold; color: #1a1a2e; }}
  .summary-card .label {{ font-size: 13px; color: #888; margin-top: 5px; }}
  .pass {{ color: #27ae60; }}
  .fail {{ color: #e74c3c; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 10px 12px; text-align: left; }}
  th {{ background: #f0f0f0; font-weight: 600; }}
  tr:hover {{ background: #fafafa; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
  .badge-pass {{ background: #d4edda; color: #155724; }}
  .badge-fail {{ background: #f8d7da; color: #721c24; }}
  .section-title {{ margin-top: 40px; border-bottom: 2px solid #1a1a2e; padding-bottom: 8px; }}
  .answer-cell {{ max-width: 400px; word-break: break-all; font-size: 12px; }}
</style>
</head>
<body>
<h1>AgentEval - AI Agent 自动化评测报告</h1>
<div class="meta">生成时间：{now}</div>

<div class="summary">
  <div class="summary-card">
    <div class="value">{total}</div>
    <div class="label">总测试用例</div>
  </div>
  <div class="summary-card">
    <div class="value pass">{passed_count}</div>
    <div class="label">通过</div>
  </div>
  <div class="summary-card">
    <div class="value fail">{total - passed_count}</div>
    <div class="label">失败</div>
  </div>
  <div class="summary-card">
    <div class="value">{pass_rate:.1f}%</div>
    <div class="label">通过率</div>
  </div>
  <div class="summary-card">
    <div class="value">{avg_latency:.0f} ms</div>
    <div class="label">平均耗时</div>
  </div>
</div>

<h2 class="section-title">分类统计</h2>
<table>
  <tr><th>测试类别</th><th>总数</th><th>通过数</th><th>通过率</th></tr>
"""
    for cat, stats in sorted(cat_stats.items()):
        cat_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        html += f'  <tr><td>{cat}</td><td>{stats["total"]}</td><td>{stats["passed"]}</td><td>{cat_rate:.1f}%</td></tr>\n'

    html += """</table>

<h2 class="section-title">详细结果</h2>
<table>
  <tr><th>Case ID</th><th>类别</th><th>Prompt</th><th>回答</th><th>通过</th><th>分数</th><th>原因</th><th>耗时</th></tr>
"""
    for r in results:
        passed = r.get("passed", False)
        badge = '<span class="badge badge-pass">通过</span>' if passed else '<span class="badge badge-fail">失败</span>'
        prompt_short = (r.get("prompt", "") or "")[:80]
        answer_short = (r.get("answer", "") or "")[:120]
        html += (
            f'  <tr>'
            f'<td>{r["case_id"]}</td>'
            f'<td>{r["category"]}</td>'
            f'<td>{_escape(prompt_short)}</td>'
            f'<td class="answer-cell">{_escape(answer_short)}</td>'
            f'<td>{badge}</td>'
            f'<td>{r.get("score", 0)}</td>'
            f'<td>{r.get("reason", "")}</td>'
            f'<td>{r.get("latency_ms", 0):.0f} ms</td>'
            f'</tr>\n'
        )

    html += """</table>

<h2 class="section-title">失败用例原因</h2>
<table>
  <tr><th>Case ID</th><th>类别</th><th>原因</th><th>Prompt</th></tr>
"""
    failed = [r for r in results if not r.get("passed")]
    for r in failed:
        prompt_short = (r.get("prompt", "") or "")[:80]
        html += (
            f'  <tr>'
            f'<td>{r["case_id"]}</td>'
            f'<td>{r["category"]}</td>'
            f'<td>{r.get("reason", "")}</td>'
            f'<td>{_escape(prompt_short)}</td>'
            f'</tr>\n'
        )

    html += """</table>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


def _escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
